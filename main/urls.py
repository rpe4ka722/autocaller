from django.urls import path
from . import views

app_name = 'main'

urlpatterns = [
    path('', views.index, name='index'),
    path('ping', views.ping, name='ping'),
    path('abonents/', views.abonents, name='abonents'),
    path('abonents/<str:msg>', views.abonents, name='abonents'),
    path('create_abonent', views.create_abonent, name='create_abonent'),
    path('edit_abonent/<int:id>', views.edit_abonent, name='edit_abonent'),
    path('delete_abonent/<int:id>', views.delete_abonent, name='delete_abonent'),
    path('sounds', views.sounds, name='sounds'),
    path('create_sound', views.create_sound, name='create_sound'),
    path('download_sound', views.download_sound, name='download_sound'),
    path('delete_sound/<int:id>', views.delete_sound, name='delete_sound'),
    path('lists', views.lists, name='lists'),
    path('create_list', views.create_list, name='create_list'),
    path('delete_list/<int:list_id>', views.delete_list, name='delete_list'),
    path('report', views.report, name='report'),
    path('start_list/<int:list_id>', views.start_list, name='start_list'),
    path('report_delete/<int:report_id>', views.report_delete, name='report_delete'),
    path('percent_status/<int:report_id>', views.percent_status, name='percent_status'),
    path('report_export/<int:report_id>', views.report_export, name='report_export'),
    path('report_time_status/<int:report_id>', views.report_time_status, name='report_time_status'),
    path('report_abon_status/<int:report_id>', views.report_abon_status, name='report_abon_status'),
]
