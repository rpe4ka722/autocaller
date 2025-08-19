from django.shortcuts import render, redirect
from .models import CustomUser
from .forms import CustomUserForm, CustomUserEditForm
from .scripts import form_errors_text
from django.shortcuts import get_object_or_404, HttpResponse
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from main.scripts import is_staff


# Create your views here.
@login_required(login_url='account:login')
def account_index(request, msg=''):
    dep = request.user.department
    adm = False
    if dep == 'ALL':
        users = CustomUser.objects.all()
        adm = True
    else: 
        users = CustomUser.objects.filter(department=dep)
    context = {'users': users, 'msg': msg, 'adm': adm}
    return render(request, 'account/templates/account.html', context)


@is_staff
@login_required(login_url='account:login')
def create_user(request):
    dep = request.user.department
    msg=''
    if request.method == 'POST':
        form = CustomUserForm(request.POST or None)
        is_staff = False
        if request.POST.get('role') == '2':
            is_staff = True
        if form.is_valid():
            cd = form.cleaned_data
            user = CustomUser.objects.create_user(username=cd['username'], password=cd['password'], first_name=cd['first_name'],
                                                  last_name=cd['last_name'], patronymic=cd['patronymic'])
            user.is_staff = is_staff
            if dep != 'ALL':
                user.department = dep
            else: 
                user.department = cd['department']
            user.save()
        else:
            msg = form_errors_text(form)
            return  HttpResponse(msg, status=500)
    return HttpResponse(msg, status=200)


@is_staff
@login_required(login_url='account:login')
def delete_user(request, id):
    try:
        user = get_object_or_404(CustomUser, pk=id)
        user.delete()
    except CustomUser.DoesNotExist:
        pass
    return redirect('account:index')


@is_staff
@login_required(login_url='account:login')
def edit_user(request, id):
    dep = request.user.department
    try:
        user = get_object_or_404(CustomUser, pk=id)
        if request.method == 'POST':
            form = CustomUserEditForm(request.POST or None)
            is_staff = False
            if request.POST.get('role') == '2':
                is_staff = True
            if form.is_valid():
                cd = form.cleaned_data
                user.first_name = cd['first_name']
                user.last_name = cd['last_name']
                user.patronymic = cd['patronymic']
                user.is_staff = is_staff
                user.is_staff = is_staff
                if dep != 'ALL':
                    user.department = dep
                else:
                    user.department = request.POST.get('department')
                user.save()
            else:
                msg = form_errors_text(form)
                return redirect('account:index', msg)
    except CustomUser.DoesNotExist:
        pass
    return redirect('account:index')
    

def login_user(request):
    if request.user.is_authenticated:
        return redirect('main:index')
    else:
        if request.method == 'POST':
            username = request.POST.get('login')
            password = request.POST.get('password')
            user = authenticate(username=username, password=password)
            if user is not None:
                login(request, user)
                return redirect('main:index')
            else:
                pass
    return render(request, 'account/templates/login.html')



def logout_view(request):
    logout(request)
    return redirect('account:login')