from celery import shared_task
from celery.result import AsyncResult
import asyncio
from main.panoramisk import CallManager
from main.models import Call, CallList, Report, CustomUser, Abonent
from asgiref.sync import sync_to_async
import time, datetime, configparser


class AMImanager:
    def __init__(self, number, sound, code, report, abonent):
        config = configparser.ConfigParser()
        config.read('./django-files/config.ini')
        if asyncio.get_event_loop().is_closed():
            self.loop = asyncio.new_event_loop()
        else:
            self.loop = asyncio.get_event_loop()
        self.queue = asyncio.Queue()
        self.manager = CallManager(
            loop=self.loop, 
            host=config['asterisk']['host'],
            port=config['asterisk']['port'],
            username=config['asterisk']['username'],
            secret=config['asterisk']['secret'],)
        self.manager.register_event("*", self.handle_events)
        self.abonent = Abonent.objects.get(id=abonent)
        self.number = number
        self.sound = sound
        self.code = code
        self.status = True
        self.report = Report.objects.get(id=report)
        self.call_object = None
        self.channel = ''
        self.prefix = config['asterisk']['prefix']

            
    async def handle_call(self):
        call_object = await sync_to_async(Call.objects.create, thread_sensitive=True)(abonent_number=self.number, report=self.report, abonent=self.abonent, start_time=datetime.datetime.now())
        await sync_to_async(call_object.save)()
        self.call_object = call_object
        await self.manager.connect()
        await asyncio.sleep(1)
        call = await self.manager.send_originate({
        'Action': 'Originate',
        'Timeout': '30000',
        'ActionID': f'{id}',
        'Channel': f'PJSIP/{self.number}{self.prefix}',
        'Context': 'autocaller',
        'Exten': 'call',
        'Priority': '1',
        'CallerID': 'Autocaller',
        'Variable': f'data={self.sound},code={self.code}',
        })

        counter = 0

        while self.status == True:
            await asyncio.sleep(1)
            counter += 1
            if counter < 180:
                pass
            else:
                print('Таймаут!')
                self.call_object.call_not_answered = True
                self.call_object.call_timeout = True
                self.call_object.end_time = datetime.datetime.now()
                self.status = False
               
        await sync_to_async(self.call_object.save)()

        self.manager.clean_originate(call)
        self.manager.close()
     

    async def handle_events(self, manager, message):
        event = ''
        #print(message)

        #нет ответа от удаленный атс
        if message.event == 'Registry' and message.status == 'Rejected':
            self.call_object.ats_no_answer = True
            self.status = False


        #определение канала
        if message.event == 'DialBegin' and message.DialString == f'{self.number}{self.prefix}' and self.channel == '':
            self.channel = message.DestChannel

        
        if self.channel in message.Channel or self.channel in message.DestChannel:
            event = message.event
            #print(f'{self.channel} канал')
            #print(event)
            await self.queue.put(event)

        cause_codes = ('1', '2', '3', '4', '5', '6', '7', '8', '9', '10', '11', '18', '19', '22', '23', '24', '25', '26', '27',
                       '28', '29', '30', '31', '33', '34', '35', '36', '37', '38', '39', '40', '41', '42', '43', '44', '45', '46',
                       '47', '48', '49', '50', '51', '52', '53', '54', '55', '56', '57', '58', '63', '65', '66', '67', '68', '69',
                       '70', '79', '81', '82', '83', '84', '85', '86', '87', '88', '89', '90', '91', '92', '93', '95', '96', '97',
                       '98', '99', '100', '101', '102', '103', '111', '127')

        if event.lower() == 'hangup' and message.cause == '0':
            print(f'{self.number} Не взял трубку!!!!')
            self.call_object.call_not_answered = True
            self.call_object.end_time = datetime.datetime.now()
            self.status = False
            
        elif event.lower() == 'hangup' and message.cause in ('17', '21'):   
            print(f'{self.number} Вызов отклонен!!!! ')
            self.call_object.call_rejected = True
            self.call_object.end_code = message.cause
            self.call_object.end_time = datetime.datetime.now()
            self.status = False

        elif event.lower() == 'hangup' and message.cause == '16':
            self.call_object.end_time = datetime.datetime.now()   
            print(f'{self.number} Вызов завершен нормально!!!!')
            self.call_object.end_code = message.cause
            self.status = False
        
        elif event.lower() == 'hangup' and message.cause in cause_codes:   
            print(f'Вызов {self.number} завершен с кодом {message.cause}')
            self.call_object.call_no_response = True
            self.call_object.end_time = datetime.datetime.now()
            self.call_object.end_code = message.cause
            self.status = False

        elif event.lower() == 'hangup' and message.cause not in cause_codes and message.cause != '0' and message.cause != '17':
            print(f'Вызов {self.number} завершен с неизвестным кодом {message.cause}')
            self.call_object.end_code = message.cause
            self.call_object.end_time = datetime.datetime.now()
            self.status = False

        elif event.lower() == 'dialend' and message.DialStatus == 'ANSWER':
            self.call_object.call_answered = True
            await sync_to_async(self.call_object.save)()
            print(f'Номер {self.number} взял трубку!!!!')

        elif event.lower() == 'varset' and message.Variable == 'user_input':
            self.call_object.user_input = message.Value
            if message.Value == str(self.code): 
                self.call_object.confirmed = True
                await sync_to_async(self.call_object.save)()
            else:
                self.call_object.incorrect_input_count += 1
                await sync_to_async(self.call_object.save)()
            print(f'Номер {self.number} ввел {message.Value}! Количество неверных попыток {self.call_object.incorrect_input_count}')
        
        elif event.lower() == 'originateresponse' and message.Response == 'Failure':
            self.call_object.call_error = True
            print(f'Вызов на номер {self.number} невозможен!!!!Ошибка станции!!!')
            self.call_object.end_time = datetime.datetime.now()
            self.status = False
        


    def run(self):
        self.loop.run_until_complete(self.handle_call())
        self.loop.close()
            


@shared_task() 
def abonent_call(sound, code, report_id, abonent_id, call_list_id):
    call_list = CallList.objects.get(id=call_list_id)
    report = Report.objects.get(id=report_id)
    abonent = Abonent.objects.get(id=abonent_id)
    call_object = None
    if call_list.main_phone:
        print(f'Оповещение по номеру {abonent.mobile_phone_number} начато')
        manager = AMImanager(number=abonent.mobile_phone_number, sound=sound, code=code, report=report_id, abonent=abonent_id)
        try:
            manager.run() 
        except:
            manager.call_object.asterisk_no_answer = True
            manager.call_object.end_time = datetime.datetime.now()
        call_object = manager.call_object.confirmed
        manager.call_object.save()
        del manager
        print(f'Оповещение по номеру {abonent.mobile_phone_number} завершено')
    if call_list.second_phone and not call_object:
        print(f'Оповещение по номеру {abonent.secondary_mobile_phone_number} начато')
        manager = AMImanager(number=abonent.secondary_mobile_phone_number, sound=sound, code=code, report=report, abonent=abonent_id)
        try:
            manager.run()
        except:
            manager.call_object.asterisk_no_answer = True
            manager.call_object.end_time = datetime.datetime.now()
        call_object = manager.call_object.confirmed
        manager.call_object.save()
        del manager
        print(f'Оповещение по номеру {abonent.secondary_mobile_phone_number} завершено')
    if call_list.work_phone and not call_object:
        print(f'Оповещение по номеру {abonent.work_phone_number} начато')
        manager = AMImanager(number=abonent.work_phone_number, sound=sound, code=code, report=report, abonent=abonent_id)
        try:
            manager.run()
        except:
            manager.call_object.asterisk_no_answer = True
            manager.call_object.end_time = datetime.datetime.now()
        call_object = manager.call_object.confirmed
        manager.call_object.save()
        del manager
        print(f'Оповещение по номеру {abonent.work_phone_number} завершено')
    #report.save() 
    return call_object    



@shared_task() 
def list_call(call_list_id, report_id):
    print('Обзвон листа')
    print(report_id)
    try:
        call_list = CallList.objects.get(id=call_list_id)
        report = Report.objects.get(id=report_id)
        sound = call_list.sound.get_full_path()[:-4]
        code = call_list.accept_combination
        results = []
        print(f'Лист {call_list.list_name} начат')
        for abonent in call_list.abonents.all():
            abonent_id = abonent.id
            res = abonent_call.apply_async(args=[sound, code, report.id, abonent_id, call_list_id], queue='celery')
            print(f'Запущено оповещение абонента {abonent.full_name()}')
            results.append(str(res))
        report.call_queue = len(results)
        report.save()
        while results:
            for result in results:
                if AsyncResult(id=result).ready():
                    print('Прошло завершение')
                    results.remove(result)
                    report.call_queue = len(results)
                    if  AsyncResult(id=result).result == True:
                        report.checked_abonents += 1
                    else:
                        report.unchecked_abonents += 1
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
    print(report_id)
    print('Запуск листа')
    list_call.apply_async(args=[call_list_id, report_id], queue='hipri')
    return report_id




    


