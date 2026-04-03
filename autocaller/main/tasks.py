from celery import shared_task
from celery.result import AsyncResult
import asyncio
from main.panoramisk import CallManager
from main.models import Call, CallList, Report, CustomUser, Abonent
from asgiref.sync import sync_to_async
import time, datetime, configparser


class AMImanager:
    def __init__(self, number,type, sound, code, report, abonent, password, is_password):
        config = configparser.ConfigParser()
        config.read('./django-files/config.ini')

        # Настройка loop
        try:
            self.loop = asyncio.get_running_loop()
        except RuntimeError:
            self.loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self.loop)

        # if asyncio.get_event_loop().is_closed():
        #     self.loop = asyncio.new_event_loop()
        # else:
        #     self.loop = asyncio.get_event_loop()

        # self.queue = asyncio.Queue()

        self.manager = CallManager(
            loop=self.loop, 
            host=config['asterisk']['host'],
            port=config['asterisk']['port'],
            username=config['asterisk']['username'],
            secret=config['asterisk']['secret'],)

        self.manager.register_event("*", self.handle_events)

        self.abonent = Abonent.objects.get(id=abonent)
        self.report_id = report

        if len(str(number)) > 5:
            self.number = '98' + number[2::]
        else: 
            self.number = number
        # self.number = number
        self.type = type
        self.sound = sound
        self.code = code
        self.password = password
        self.is_password = '1' if is_password else '0'
        # self.status = True
        self.prefix = config['asterisk']['prefix']
        # self.report = Report.objects.get(id=report)
        self.call_object = None
        self.action_id = None # Определим после создания записи в БД
        self.linkedid = None # Определим после получения Newchannel
        # self.channel = ''
        self.stop_event = asyncio.Event()
        

            
    async def handle_call(self):
        # 1. Создаем объект Call в БД
        call_object = await sync_to_async(Call.objects.create)(
            abonent_number=self.number, 
            phone_type=self.type, 
            report=self.report, 
            abonent=self.abonent, 
            start_time=datetime.datetime.now()
        )

        # 2. Формируем ActionID на базе Django ID
        self.action_id = f"django_call_{self.call_object.id}"
        
        # await sync_to_async(call_object.save)()
        # self.call_object = call_object

        await self.manager.connect()


        # await asyncio.sleep(1)

        # 3. Отправка Originate
        call = await self.manager.send_originate({
        'Action': 'Originate',
        'Timeout': '30000',
        'ActionID': self.action_id,,
        'Channel': f'PJSIP/{self.number}{self.prefix}',
        'Context': 'autocaller',
        'Exten': 'call',
        'Priority': '1',
        'CallerID': 'Autocaller',
        'Variable': f'data={self.sound},code={self.code},pass={self.password},is_pass={self.is_password}',
        })

        # counter = 0

        # 4. Ожидание завершения или таймаута (180 секунд)
        try:
            await asyncio.wait_for(self.stop_event.wait(), timeout=180.0)
        except asyncio.TimeoutError:
            print(f'Таймаут для звонка {self.call_object.id}')
            self.call_object.call_timeout = True
            self.call_object.call_not_answered = True
            self.call_object.end_time = datetime.datetime.now()



        # while self.status == True:
        #     await asyncio.sleep(1)
        #     counter += 1
        #     if counter < 180:
        #         pass
        #     else:
        #         print('Таймаут!')
        #         self.call_object.call_not_answered = True
        #         self.call_object.call_timeout = True
        #         self.call_object.end_time = datetime.datetime.now()
        #         self.status = False
               
        # 5. Финальное сохранение состояния
        await sync_to_async(self.call_object.save)()

        # self.manager.clean_originate(call)
        self.manager.close()
     

    async def handle_events(self, manager, message):
        event = ''
        #print(message)

        #нет ответа от удаленный атс
        if message.event == 'Registry' and message.status == 'Rejected':
            self.call_object.ats_no_answer = True
            self.status = False


        # #определение канала
        # if message.event == 'DialBegin' and message.DialString == f'{self.number}{self.prefix}' and self.channel == '':
        #     self.channel = message.DestChannel

        
        # if self.channel in message.Channel or self.channel in message.DestChannel:
        #     event = message.event
        #     #print(f'{self.channel} канал')
        #     #print(event)
        #     await self.queue.put(event)

        # А) Идентификация канала: ActionID -> Linkedid
        msg_action_id = message.get('ActionID')
        if message.event == 'Newchannel' and msg_action_id == self.action_id:
            self.linkedid = message.Linkedid
            # print(f"Связь: {self.action_id} <-> {self.linkedid}")

        # Б) Фильтрация событий по Linkedid
        msg_linkedid = getattr(message, 'Linkedid', None)
        if self.linkedid and msg_linkedid == self.linkedid:
            event_name = message.event.lower()

            # Ввод кода уведомления
            if event_name == 'varset' and message.Variable == 'user_input':
                self.call_object.user_input = message.Value
                if message.Value == str(self.code): 
                    self.call_object.confirmed = True
                else:
                    self.call_object.incorrect_input_count += 1
                await sync_to_async(self.call_object.save)(update_fields=['user_input', 'confirmed', 'incorrect_input_count'])

            # Ввод пароля
            elif event_name == 'varset' and message.Variable == 'pass_input':
                self.call_object.user_pass_input = message.Value
                if message.Value == str(self.password): 
                    self.call_object.pass_confirmed = True
                else:
                    self.call_object.incorrect_pass_input_count += 1
                await sync_to_async(self.call_object.save)(update_fields=['user_pass_input', 'pass_confirmed', 'incorrect_pass_input_count'])

            # Ответ абонента
            elif event_name == 'dialend' and getattr(message, 'DialStatus', None) == 'ANSWER':
                self.call_object.call_answered = True
                await sync_to_async(self.call_object.save)(update_fields=['call_answered'])

            # Завершение (Hangup)
            elif event_name == 'hangup':
                self.call_object.end_time = datetime.datetime.now()
                self.call_object.end_code = message.cause
                
                # Коды завершения
                if message.cause in ('17', '21'): self.call_object.call_rejected = True
                elif message.cause == '0': self.call_object.call_not_answered = True
                elif message.cause not in ('16', '17', '21', '0'): self.call_object.call_no_response = True
                
                self.stop_event.set() # Пробуждаем handle_call

        # В) Ошибки регистрации или системы
        if msg_action_id == self.action_id:
            if message.event == 'Registry' and message.status == 'Rejected':
                self.call_object.ats_no_answer = True
                self.stop_event.set()
            elif event_name == 'originateresponse' and message.Response == 'Failure':
                self.call_object.call_error = True
                self.call_object.end_time = datetime.datetime.now()
                self.stop_event.set()

    def run(self):
        self.loop.run_until_complete(self.handle_call())

        # cause_codes = ('1', '2', '3', '4', '5', '6', '7', '8', '9', '10', '11', '18', '19', '22', '23', '24', '25', '26', '27',
        #                '28', '29', '30', '31', '33', '34', '35', '36', '37', '38', '39', '40', '41', '42', '43', '44', '45', '46',
        #                '47', '48', '49', '50', '51', '52', '53', '54', '55', '56', '57', '58', '63', '65', '66', '67', '68', '69',
        #                '70', '79', '81', '82', '83', '84', '85', '86', '87', '88', '89', '90', '91', '92', '93', '95', '96', '97',
        #                '98', '99', '100', '101', '102', '103', '111', '127')

        # #нет ответа от абонента
        # if event.lower() == 'hangup' and message.cause == '0':
        #     print(f'{self.number} Не взял трубку!!!!')
        #     self.call_object.call_not_answered = True
        #     self.call_object.end_time = datetime.datetime.now()
        #     self.status = False
            
        # #сброс вызова
        # elif event.lower() == 'hangup' and message.cause in ('17', '21'):   
        #     print(f'{self.number} Вызов отклонен!!!! ')
        #     self.call_object.call_rejected = True
        #     self.call_object.end_code = message.cause
        #     self.call_object.end_time = datetime.datetime.now()
        #     self.status = False

        # #абонент положил трубку
        # elif event.lower() == 'hangup' and message.cause == '16':
        #     self.call_object.end_time = datetime.datetime.now()   
        #     print(f'{self.number} Вызов завершен нормально!!!!')
        #     self.call_object.end_code = message.cause
        #     self.status = False
        
        # #обработка кодов завершения
        # elif event.lower() == 'hangup' and message.cause in cause_codes:   
        #     print(f'Вызов {self.number} завершен с кодом {message.cause}')
        #     self.call_object.call_no_response = True
        #     self.call_object.end_time = datetime.datetime.now()
        #     self.call_object.end_code = message.cause
        #     self.status = False

        # #обработка неизвестных кодов завершения
        # elif event.lower() == 'hangup' and message.cause not in cause_codes and message.cause != '0' and message.cause != '17':
        #     print(f'Вызов {self.number} завершен с неизвестным кодом {message.cause}')
        #     self.call_object.end_code = message.cause
        #     self.call_object.end_time = datetime.datetime.now()
        #     self.status = False

        # #регистрация ответа абонента
        # elif event.lower() == 'dialend' and message.DialStatus == 'ANSWER':
        #     self.call_object.call_answered = True
        #     await sync_to_async(self.call_object.save)()
        #     print(f'Номер {self.number} взял трубку!!!!')

        # #регистрация ввода кода уведомления
        # elif event.lower() == 'varset' and message.Variable == 'user_input':
        #     self.call_object.user_input = message.Value
        #     if message.Value == str(self.code): 
        #         self.call_object.confirmed = True
        #         await sync_to_async(self.call_object.save)()
        #     else:
        #         self.call_object.incorrect_input_count += 1
        #         await sync_to_async(self.call_object.save)()
        #     print(f'Номер {self.number} ввел {message.Value}! Количество неверных попыток {self.call_object.incorrect_input_count}')


        #регистрация ввода пароля
        elif event.lower() == 'varset' and message.Variable == 'pass_input':
            self.call_object.user_pass_input = message.Value
            if message.Value == str(self.password): 
                self.call_object.pass_confirmed = True
                await sync_to_async(self.call_object.save)()
                print(f'Номер {self.number} ввел верный пароль {message.Value}! Количество неверных попыток ввода пароля {self.call_object.incorrect_pass_input_count}')
            else:
                self.call_object.incorrect_pass_input_count += 1
                await sync_to_async(self.call_object.save)()
                print(f'Номер {self.number} ввел неверный пароль {message.Value}! Количество неверных попыток ввода пароля {self.call_object.incorrect_pass_input_count}')
        
        #отработка ошибки атс
        elif event.lower() == 'originateresponse' and message.Response == 'Failure':
            self.call_object.call_error = True
            print(f'Вызов на номер {self.number} невозможен!!!!Ошибка станции!!!')
            print(message)
            self.call_object.end_time = datetime.datetime.now()
            self.status = False
        


    def run(self):
        self.loop.run_until_complete(self.handle_call())
        self.loop.close()
            


# @shared_task() 
# def abonent_call(sound, code, report_id, abonent_id, call_list_id, password, is_password):
#     print(f'abon_id {abonent_id}')
#     print(f'report_id {report_id}')
#     call_list = CallList.objects.get(id=call_list_id)
#     #report = Report.objects.get(id=report_id)
#     abonent = Abonent.objects.get(id=abonent_id)
#     call_object = None
#     current_try = 1
#     while current_try <= call_list.tries_number and not call_object:
#         if call_list.work_phone and not call_object and abonent.work_phone_number:
#             print(f'Оповещение по номеру {abonent.work_phone_number} начато')
#             manager = AMImanager(
#                 number=abonent.work_phone_number,
#                 type='рабочий',
#                 sound=sound,
#                 code=code,
#                 report=report_id,
#                 abonent=abonent_id,
#                 password=password,
#                 is_password=is_password
#                 )
#             try:
#                 manager.run()
#             except:
#                 manager.call_object.asterisk_no_answer = True
#                 manager.call_object.end_time = datetime.datetime.now()
#             call_object = manager.call_object.confirmed
#             manager.call_object.save()
#             del manager
#             print(f'Оповещение по номеру {abonent.work_phone_number} завершено')
#         if call_list.main_phone and abonent.mobile_phone_number and not call_object:
#             print(f'Оповещение по номеру {abonent.mobile_phone_number} начато')
#             manager = AMImanager(
#                 number=abonent.mobile_phone_number,
#                 type='мобильный',
#                 sound=sound,
#                 code=code,
#                 report=report_id,
#                 abonent=abonent_id,
#                 password=password,
#                 is_password=is_password
#                 )
#             try:
#                 manager.run() 
#             except:
#                 manager.call_object.asterisk_no_answer = True
#                 manager.call_object.end_time = datetime.datetime.now()
#             call_object = manager.call_object.confirmed
#             manager.call_object.save()
#             del manager
#             print(f'Оповещение по номеру {abonent.mobile_phone_number} завершено')
#         if call_list.second_phone and not call_object and abonent.secondary_mobile_phone_number:
#             print(f'Оповещение по номеру {abonent.secondary_mobile_phone_number} начато')
#             manager = AMImanager(
#                 number=abonent.secondary_mobile_phone_number,
#                 type='дополнительный',
#                 sound=sound,
#                 code=code,
#                 report=report_id,
#                 abonent=abonent_id,
#                 password=password,
#                 is_password=is_password
#                 )
#             try:
#                 manager.run()
#             except:
#                 manager.call_object.asterisk_no_answer = True
#                 manager.call_object.end_time = datetime.datetime.now()
#             call_object = manager.call_object.confirmed
#             manager.call_object.save()
#             del manager
#             print(f'Оповещение по номеру {abonent.secondary_mobile_phone_number} завершено')
#         current_try += 1
#     #report.save() 
#     return call_object    

@shared_task() 
def abonent_call(sound, code, report_id, abonent_id, call_list_id, password, is_password):
    # 1. Загружаем необходимые объекты
    call_list = CallList.objects.get(id=call_list_id)
    abonent = Abonent.objects.get(id=abonent_id)
    
    confirmed = False  # Флаг успешного подтверждения
    current_try = 1
    
    # 2. Формируем список доступных номеров
    phones = []
    if call_list.work_phone and abonent.work_phone_number:
        phones.append((abonent.work_phone_number, 'рабочий'))
    if call_list.main_phone and abonent.mobile_phone_number:
        phones.append((abonent.mobile_phone_number, 'мобильный'))
    if call_list.second_phone and abonent.secondary_mobile_phone_number:
        phones.append((abonent.secondary_mobile_phone_number, 'дополнительный'))

    # 3. Основной цикл обзвона
    # Работает пока не закончатся попытки ИЛИ пока не получим confirmed = True
    while current_try <= call_list.tries_number and not confirmed:
        for phone_num, phone_type in phones:
            if confirmed: 
                break # Если подтвердили на одном номере, другие не набираем
            
            # Создаем экземпляр менеджера для конкретного звонка
            manager = AMImanager(
                number=phone_num,
                phone_type=phone_type,
                sound=sound,
                code=code,
                report_id=report_id,
                abonent_id=abonent_id,
                password=password,
                is_password=is_password
            )
            
            try:
                # Запускаем асинхронный цикл звонка
                manager.run()
                
                # После завершения run() проверяем, было ли подтверждение
                if manager.call_object:
                    confirmed = manager.call_object.confirmed
            except Exception as e:
                print(f"Ошибка AMI при звонке на {phone_num}: {e}")
                # Если менеджер успел создать объект, помечаем системную ошибку
                if manager.call_object:
                    manager.call_object.asterisk_no_answer = True
                    manager.call_object.save()
            
        current_try += 1 # Переходим к следующей попытке обхода всех номеров
    
    # 4. Возвращаем итоговый результат (True/False)
    return confirmed



@shared_task() 
def list_call(call_list_id, report_id):
    print('Обзвон листа')
    print(report_id)
    try:
        call_list = CallList.objects.get(id=call_list_id)
        report = Report.objects.get(id=report_id)
        sound = call_list.sound.get_full_path()[:-4]
        print(sound)
        code = call_list.accept_combination
        password = call_list.password
        is_password = call_list.is_password
        results = []
        print(f'Лист {call_list.list_name} начат')
        excluded_ids = call_list.exclude_abonents.values_list('id', flat=True)

        for abonent in call_list.abonents.all().exclude(id__in=excluded_ids):
            time.sleep(1)
            abonent_id = abonent.id
            res = abonent_call.apply_async(args=[sound, code, report.id, abonent_id, call_list_id, password, is_password], queue='celery')
            print(f'Запущено оповещение абонента {abonent.full_name()}')
            results.append(str(res))
        report.call_queue = len(results)
        report.save()
        while results:
            # for result in results:
            #     if AsyncResult(id=result).ready():
            #         print('Прошло завершение')
            #         results.remove(result)
            #         report.call_queue = len(results)
            #         if  AsyncResult(id=result).result == True:
            #             report.checked_abonents += 1
            #         else:
            #             report.unchecked_abonents += 1
            #         report.save()
            for result in results[:]:
                res_obj = AsyncResult(id=result)
                if res_obj.ready():
                # Здесь .result будет содержать именно то, что вернул abonent_call (True/False)
                    is_confirmed = res_obj.result 
                    results.remove(result)
        
                if is_confirmed:
                     report.checked_abonents += 1
                else:
                    report.unchecked_abonents += 1
        
                report.call_queue = len(results)
                report.save()

            time.sleep(0.5)
        report.in_progress = False
        report.end_time = datetime.datetime.now()
        call_list = report.list
        report.save()
        print(f'Оповещение по листу {call_list.list_name} завершено')
        return report.id
    except CallList.DoesNotExist:
        return 'Неизвестная ошибка'
    

@shared_task() 
def start_caller(call_list_id, user_id):
    call_list = CallList.objects.get(id=call_list_id)
    user = CustomUser.objects.get(id=user_id)
    report = Report.objects.create(list=call_list, in_progress=True, create_by_user = user)
    report.save()
    report_id = report.id
    print(f'Запуск листа {call_list.list_name}')
    list_call.apply_async(args=[call_list_id, report_id], queue='hipri')
    return report_id




    


