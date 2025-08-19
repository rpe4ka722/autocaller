from django.contrib import admin
from account.models import CustomUser
from django.contrib.auth.admin import UserAdmin
# Register your models here.


class CustomUserAdmin(UserAdmin):
    model = CustomUser
    list_display = ['username','first_name', 'last_name', 'department',]
    fieldsets = UserAdmin.fieldsets + (
            (None, {'fields': ('department', 'patronymic')}),
    )
admin.site.register(CustomUser, CustomUserAdmin)