from django.forms import ModelForm
from .models import CustomUser
from django.contrib.auth.forms import UserChangeForm
from django import forms


class CustomUserForm(ModelForm):
    class Meta:
        model = CustomUser
        fields = ['username', 'password', 'first_name', 'last_name', 'patronymic']


class CustomUserEditForm(ModelForm):
    class Meta:
        model = CustomUser
        fields = ['first_name', 'last_name', 'patronymic']

