from django.contrib.auth.models import AbstractUser
from django.db import models

# Create your models here.
class CustomUser(AbstractUser):
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

    patronymic = models.CharField(verbose_name="Отчетство", max_length=30, blank=True, null=True)
    department = models.CharField(max_length=4, choices=DEPARTMENT_CHOICES, blank=True, null=True)


    def __str__(self):
        return self.username 
    
    
    def str_department(self):
        return self.get_department_display()
