from django.db import models
from account.models import CustomUser
from django.core.validators import MinValueValidator, MaxValueValidator


# Create your models here.
class Abonent(models.Model):
    DEPARTMENT_CHOICES = (
    ("NUR", 'Ново-Уренгойское ЛПУМГ'),
    ("PURP", 'Пурпейское ЛПУМГ'),
    ("GUBK", 'Губкинское ЛПУМГ'),
    ("VING", 'Вынгапуровское ЛПУМГ'),
    ("ORTJ", 'Ортьягунское ЛПУМГ'),
    ("SRGT", 'Сургутское ЛПУМГ'),
    ("YBLK", 'Южно-Балыкское ЛПУМГ'),
    ("SAMS", 'Самсоновское ЛПУМГ'),
    ("DMNK", 'Демьянское ЛПУМГ'),
    ("TRTS", 'Туртасское ЛПУМГ'),
    ("TBL", 'Тобольское ЛПУМГ'),
    ("YARK", 'Ярковское ЛПУМГ'),
    ("BGND", 'Богандинское ЛПУМГ'),
    ("ISHM", 'Ишимское ЛПУМГ'),
    ("ADM", 'Администрация'),
    ("US", 'Управление связи'),
    ("UAVR", 'Управление аварийно-восстановительных работ'),
    ("UEZS", 'Управление по эксплуатации зданий и сооружений'),
    ("ITC", 'Инженерно-технический центр'),
    ("MSCH", 'Медико-санитарная часть'),
    ("UTT", 'Управление транспорта и специальной техники'),
    ("ALL", 'Все филиалы')
    )

    first_name = models.CharField(verbose_name="Имя", max_length=30, blank=True, null=True)
    last_name = models.CharField(verbose_name="Фамилия", max_length=30, blank=True, null=True)
    patronymic = models.CharField(verbose_name="Отчетство", max_length=30, blank=True, null=True)
    work_phone_number = models.IntegerField(verbose_name="Рабочий номер телефона", blank=True, null=True)
    mobile_phone_number = models.CharField(verbose_name="Мобильный номер телефона", max_length=12, blank=True, null=True)
    secondary_mobile_phone_number = models.CharField(verbose_name="Дополнительный номер телефона", max_length=12, blank=True, null=True)
    department = models.CharField(verbose_name="Филиал", max_length=4, choices=DEPARTMENT_CHOICES,)


    def full_name(self):
        first_name = self.first_name
        patronymic = self.patronymic
        last_name = self.last_name
        if first_name is None:
            first_name = ''
        if patronymic is None:
            patronymic = ''
        if last_name is None:
            last_name = ''
        full_name = last_name + ' ' + first_name + ' ' + patronymic
        return full_name
    

    def str_department(self):
        return self.get_department_display()
    

class SoundFile(models.Model):
    dir = models.CharField(max_length=100)
    filename = models.CharField(max_length=100)
    department = models.CharField(max_length=4)

    def get_full_path(self):
        path = self.dir + self.filename
        return path
    
    def get_url(self):
        url = '/media/sounds/' + self.department + '/' + self.filename
        return url
    

class CallList(models.Model):
    list_name = models.CharField(verbose_name="Имя", max_length=20)
    list_description = models.CharField(verbose_name="Фамилия", max_length=100)
    abonents = models.ManyToManyField(Abonent)
    last_edit_user = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True)
    last_edit_time = models.DateTimeField(auto_now_add=True)
    department = models.CharField(max_length=4)
    main_phone = models.BooleanField(default=True)
    second_phone = models.BooleanField(default=False)
    work_phone = models.BooleanField(default=False)
    sound = models.ForeignKey(SoundFile, on_delete=models.CASCADE, null=True)
    accept_combination = models.IntegerField(default=5, validators=[MinValueValidator(0), MaxValueValidator(9)])
    tries_number = models.IntegerField(default=1, validators=[MinValueValidator(1), MaxValueValidator(3)])
    password = models.IntegerField(default=5, validators=[MinValueValidator(0), MaxValueValidator(9)])



    def abonents_count(self):
        return self.abonents.count()
    

class Report(models.Model):
    start_time = models.DateTimeField(auto_now_add=True)
    end_time = models.DateTimeField(null=True)
    list = models.ForeignKey(CallList, on_delete=models.CASCADE, null=True)
    in_progress = models.BooleanField(default=False)
    department = models.CharField(max_length=4, null=True)
    call_queue = models.IntegerField(default=None, null=True)
    create_by_user = models.ForeignKey(CustomUser, default=None, on_delete=models.SET_NULL, null=True)
    checked_abonents = models.IntegerField(default=0, null=True)
    unchecked_abonents = models.IntegerField(default=0, null=True)

    def save(self, *args, **kwargs):
        if self.department is not None:
            super(Report, self).save(*args, **kwargs)
        else:
            self.department = self.list.department
            super(Report, self).save(*args, **kwargs)




class Call(models.Model):
    abonent = models.ForeignKey(Abonent, on_delete=models.SET_NULL, null=True)
    phone_type = models.CharField(max_length=15, default=None, null=True)
    abonent_number = models.CharField(verbose_name="Номер телефона", max_length=12)
    start_time = models.DateTimeField(auto_now_add=True)
    call_rejected = models.BooleanField(default=False)
    call_not_answered = models.BooleanField(default=False)
    call_no_response = models.BooleanField(default=False)
    call_answered = models.BooleanField(default=False)
    call_error = models.BooleanField(default=False)
    call_timeout = models.BooleanField(default=False)
    user_input = models.CharField(max_length=3, null=True)
    incorrect_input_count = models.IntegerField(default=0, null=True)
    user_pass_input = models.CharField(max_length=3, null=True)
    incorrect_pass_input_count = models.IntegerField(default=0, null=True)
    pass_confirmed = models.BooleanField(default=False)
    asterisk_no_answer = models.BooleanField(default=False)
    ats_no_answer = models.BooleanField(default=False)
    end_code = models.IntegerField(null=True)
    end_time = models.DateTimeField(null=True)
    report = models.ForeignKey(Report, null=True, on_delete=models.CASCADE, related_name='call')
    confirmed = models.BooleanField(default=False)






