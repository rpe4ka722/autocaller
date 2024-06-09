from django.forms import ModelForm
from .models import Abonent


class AbonentForm(ModelForm):
    class Meta:
        model = Abonent
        fields = ['first_name', 'last_name', 'patronymic', 'work_phone_number', 'mobile_phone_number', 'secondary_mobile_phone_number']