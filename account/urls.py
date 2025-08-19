from django.urls import path
from . import views

app_name = 'account'

urlpatterns = [
    path('index', views.account_index, name='index'),
    path('index/<str:msg>', views.account_index, name='index'),
    path('create_user', views.create_user, name='create_user'),
    path('delete_user/<int:id>', views.delete_user, name='delete_user'),
    path('edit_user/<int:id>', views.edit_user, name='edit_user'),
    path('login', views.login_user, name='login'),
    path('logout', views.logout_view, name='logout')
]
