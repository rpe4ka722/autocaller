from celery import shared_task
from celery.result import AsyncResult
import asyncio
from main.panoramisk import CallManager
from main.models import Call, CallList, Report, CustomUser, Abonent
from asgiref.sync import sync_to_async
import time, datetime, configparser
from django.db import transaction


class AMImanager:
    def __init__(self, number,phone_type, sound, code, report_id, abonent_id, password, is_password):
        # Загрузка настроек подключения к Asterisk из ini-файла
        config = configparser.ConfigParser()
        config.read('./django-files/config.ini')

        # 1. Сначала получаем текущий цикл событий
        try:
            self.loop = asyncio.get_running_loop()
        except RuntimeError:
            # Если цикл еще не запущен (редко в Celery, но бывает), берем новый
            self.loop = asyncio.get_event_loop()

        # Инициализация менеджера звонков (библиотека panoramisk)
        self.manager = CallManager(
            loop=self.loop, 
            host=config['asterisk']['host'],
            port=config['asterisk']['port'],
            username=config['asterisk']['username'],
            secret=config['asterisk']['secret'],
        )

        # Регистрация обработчика для ВСЕХ событий Asterisk
        self.manager.register_event("*", self.handle_events)

        # Привязка данных из БД Django
        self.abonent = Abonent.objects.get(id=abonent_id)
        self.report_id = report_id

        # Логика преобразования номера (добавление префикса выхода на линию)
        if len(str(number)) > 5:
            self.number = '98' + number[2::]
        else: 
            self.number = number
        
        # Параметры звонка: звук, код подтверждения, пароль
        self.phone_type = phone_type
        self.sound = sound
        self.code = code
        self.password = password
        self.is_password = '1' if is_password else '0'
        self.prefix = config['asterisk']['prefix']

        self.call_object = None # Ссылка на запись Call в БД
        self.action_id = None # # ID для отслеживания конкретной команды Originate
        self.linkedid = None # Уникальный ID канала в самом Asterisk
        self.stop_event = None # Событие для остановки ожидания, когда звонок завершен

        
        

            
    async def handle_call(self):
        """Основной метод запуска звонка"""

        # Событие для остановки ожидания, когда звонок завершен
        self.stop_event = asyncio.Event()
        
        # 1. Создаем запись о попытке звонка в БД (используем sync_to_async для работы с ORM)
        self.call_object = await sync_to_async(Call.objects.create)(
            abonent_number=self.number, 
            phone_type=self.phone_type, 
            report_id=self.report_id, 
            abonent=self.abonent, 
            start_time=datetime.datetime.now()
        )

        # 2. Формируем уникальный ActionID, чтобы найти этот звонок в потоке событий
        self.action_id = f'django_call_{self.call_object.id}'
        print(f'Полученный ActionID {self.action_id}')
        
        
        try:
            # Подключаемся к Asterisk
            await self.manager.connect()
            await asyncio.sleep(1)

            # 3. Отправка команды Originate (инициировать вызов)
            # Asterisk позвонит на Channel и при ответе отправит его в Context 'autocaller'

            print(f'Отправляем Originate action_id = {self.action_id}')

            call = await self.manager.send_originate({
                'Action': 'Originate',
                'Timeout': '30000',
                'ActionID': self.action_id,
                'Channel': f'PJSIP/{self.number}{self.prefix}',
                'Context': 'autocaller',
                'Exten': 'call',
                'Priority': '1',
                'CallerID': 'Autocaller',
                # Передаем переменные в Dialplan Asterisk (путь к звуку, коды и т.д.)
                'Variable': f'data={self.sound},code={self.code},pass={self.password},is_pass={self.is_password}',
            })

            # 4. Ожидание завершения или таймаута (180 секунд)
            await asyncio.wait_for(self.stop_event.wait(), timeout=180.0)

        except asyncio.TimeoutError:
            print(f'Таймаут для звонка {self.call_object.id}')
            self.call_object.call_timeout = True
            self.call_object.end_time = datetime.datetime.now()
        except Exception as e:
            print(f"Ошибка в handle_call: {e}")
            self.call_object.call_error = True
        finally:
            # 5. Финализация
            self.call_object.end_time = datetime.datetime.now()
            # 5. Сохраняем финальные результаты в БД и закрываем соединение
            await sync_to_async(self.call_object.save)(update_fields=['end_time', 'call_error', 'call_timeout'])
            if self.manager:
                self.manager.close()

     

    async def handle_events(self, manager, message):
        """Обработчик всех входящих событий от Asterisk"""

        print(f'MESSAGE: {message}')
    
        
        # Обработка события Registry от Asterisk
        # Это происходит, когда транк (канал связи) не может авторизоваться
        if message.event == 'Registry' and message.status == 'Rejected':
            self.call_object.ats_no_answer = True
            self.stop_event.set()

        # # Финализация при ошибке Originate (если абонент сразу недоступен)
        # if message.event.lower() == 'originateresponse' and message.Response == 'Failure':
        #     self.call_object.call_error = True
        #     self.stop_event.set()

        # А) Идентификация канала: ActionID -> Linkedid
        msg_action_id = message.get('ActionID')
        if message.event.lower() == 'originateresponse' and msg_action_id == self.action_id:
            if getattr(message, 'Responce', None)=='Succes':
                self.linkedid = getattr(message, 'Uniqueid', None) or getattr(message, 'Linkedid', None)
                print(f"Связь: {self.action_id} <-> {self.linkedid}")
            elif getattr(message, 'Responce', None)=='Failure':
                print('OrogonateResponce = Failure')
                self.call_object.call_error = True
                self.stop_event.set()
            else:
                print('OriginateResponce unnkown responce')
                self.call_object.call_error = True
                self.stop_event.set()

        if not self.linkedid and message.event == 'DialBegin'and message.DialString == f'{self.number}{self.prefix}':
            self.linkedid = getattr(message, 'DestUniqueid', None) or getattr(message, 'DestLinkedid', None)
            print(f"Связь: {self.action_id} <-> {self.linkedid}")


        # Б) Фильтрация событий по Linkedid
        msg_linkedid = getattr(message, 'Linkedid', None)
        if self.linkedid and msg_linkedid == self.linkedid:
            event_name = message.event.lower()

            # Обработка ввода цифр абонентом (через VarSet в Dialplan)
            if event_name == 'varset' and message.Variable == 'user_input':
                self.call_object.user_input = message.Value
                print(f'Пользователь ввел { message.Value}')
                if message.Value == str(self.code): 
                    self.call_object.confirmed = True
                else:
                    self.call_object.incorrect_input_count += 1
                await sync_to_async(self.call_object.save)(update_fields=['user_input', 'confirmed', 'incorrect_input_count'])

            # Ввод пароля
            elif event_name == 'varset' and message.Variable == 'pass_input':
                self.call_object.user_pass_input = message.Value
                print(f'Пользователь ввел пароль { message.Value}')
                if message.Value == str(self.password): 
                    self.call_object.pass_confirmed = True
                else:
                    self.call_object.incorrect_pass_input_count += 1
                await sync_to_async(self.call_object.save)(update_fields=['user_pass_input', 'pass_confirmed', 'incorrect_pass_input_count'])

            # Факт поднятия трубки
            elif event_name == 'dialend' and getattr(message, 'DialStatus', None) == 'ANSWER':
                self.call_object.call_answered = True
                print('Пользователь взял трубку')
                await sync_to_async(self.call_object.save)(update_fields=['call_answered'])

            # Завершение (Hangup)
            elif event_name == 'hangup':
                self.call_object.end_time = datetime.datetime.now()
                self.call_object.end_code = message.cause
                print('Пользователь положил трубку')

                # Безопасное получение cause, даже если его нет в сообщении
                cause = str(getattr(message, 'cause', '0')) 
                self.call_object.end_code = int(cause) if cause.isdigit() else 0
                
                # 1. Абонент сбросил (Занято)
                if cause in ('17', '21'):
                    self.call_object.call_rejected = True
        
                # 2. Абонент не поднял трубку (Таймаут звонка)
                elif cause in ('18', '19'): 
                    # 18 - No user responding, 19 - No answer from user
                    self.call_object.call_not_answered = True
        
                # 3. Успешный звонок (Нормальное завершение)
                elif cause == '16':
                    # Если код 16, значит поговорили. 
                    # Но подтверждение (confirmed) ты уже ставишь в VarSet, так что тут просто финализируем.
                    pass
        
                # 4. Технические ошибки (Недоступен, ошибка сети)
                elif cause == '0':
                    self.call_object.call_no_response = True
        
                # 5. Все остальное (Неправильный номер, перегрузка и т.д.)
                else:
                    self.call_object.call_error = True
                
                await sync_to_async(self.call_object.save)(update_fields=['end_code', 'call_not_answered', 'call_error', 'call_rejected', 'call_no_response'])
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
        """Запуск асинхронного процесса из синхронного кода (Celery)"""
        self.loop.run_until_complete(self.handle_call())
        # self.loop.close()



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
        time.sleep(0.5)
    
    # 4. Возвращаем итоговый результат (True/False)
    return confirmed



@shared_task() 
def list_call(call_list_id, report_id):
    """Проходит по всем абонентам в списке и запускает подзадачи"""
    print(f'Обзвон листа {report_id}')

    try:
        # Шаг 1: Инициализация данных
        call_list = CallList.objects.get(id=call_list_id)
        report = Report.objects.get(id=report_id)

        # Подготовка пути к звуковому файлу (обрезаем расширение, если нужно для телефонии)
        sound = call_list.sound.get_full_path()[:-4]

        # Извлекаем параметры обзвона
        code = call_list.accept_combination
        password = call_list.password
        is_password = call_list.is_password

        results = [] # Список для хранения ID запущенных задач (Task IDs)

        print(f'Лист {call_list.list_name} начат')

        # Шаг 2: Фильтрация абонентов
        # Исключаем тех, кто находится в списке exclude_abonents
        excluded_ids = call_list.exclude_abonents.values_list('id', flat=True)
        abonent_ids = call_list.abonents.all().exclude(id__in=excluded_ids).values_list('id', flat=True)

        # Основной цикл запуска звонков
        for abonent_id in abonent_ids:
            time.sleep(1)
            res = abonent_call.apply_async(args=[sound, code, report.id, abonent_id, call_list_id, password, is_password], queue='celery')

            # Сохраняем ID задачи в список, чтобы потом проверить результат
            results.append(str(res))

        # Обновляем количество задач в очереди отчета    
        report.call_queue = len(results)
        report.save()

        # Шаг 3: Мониторинг выполнения (Ожидание результатов)
        while results:

            for result_id in results[:]:
                res_obj = AsyncResult(id=result_id)
                if res_obj.ready():
                # Здесь .result будет содержать именно то, что вернул abonent_call (True/False)

                    if res_obj.successful():
                        is_confirmed = res_obj.result
                        results.remove(result_id)
                    else: 
                        is_confirmed = False
        
                    if is_confirmed:
                        report.checked_abonents += 1
                    else:
                        report.unchecked_abonents += 1

                    report.save()
                    report.call_queue = len(results)

            time.sleep(0.5)

        report.in_progress = False
        report.end_time = datetime.datetime.now()
        call_list = report.list
        report.save()
        print(f'Оповещение по листу {call_list.list_name} завершено')
        return report.id
    except CallList.DoesNotExist:
        return 'Неизвестная ошибка'
    

@shared_task(bind=True, max_retries=3)
def start_caller(self, list_id, user_id):
    try:
        # Используем атомарную транзакцию для чистоты данных
        with transaction.atomic():
            call_list = CallList.objects.select_related('sound').get(id=list_id)
            user = CustomUser.objects.get(id=user_id)
            
            # Создаем отчет
            report = Report.objects.create(
                list=call_list, 
                in_progress=True, 
                create_by_user=user
            )
            report_id = report.id

        print(f'Инициализация обзвона для списка: {call_list.list_name}')

        # Запускаем следующую задачу ТОЛЬКО после того, как отчет точно сохранился в БД
        transaction.on_commit(
            lambda: list_call.apply_async(
                args=[list_id, report_id], 
                queue='hipri'
            )
        )
        
        return report_id

    except (CallList.DoesNotExist, CustomUser.DoesNotExist) as e:
        return None



    


