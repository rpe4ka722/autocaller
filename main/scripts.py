from django.http import HttpResponse


def parse_ami_response(s:str):
    result = dict()
    raw_list = []
    raw_list = s.split('\r\n')
    for raw in raw_list:
        if raw != '':
            result[raw.split(': ')[0]] = raw.split(': ')[1]
    return result


def is_staff(view_func):
    def decorator(request, *args, **kwargs):
        u = request.user
        if u.is_active and u.is_staff:
            return view_func(request, *args, **kwargs)
        else:
            msg = 'У вас недостаточно прав для данной операции. Обратитесь к администратору либо авторизуйтесь под ' \
                  'другим именем.'
            return HttpResponse(msg, status=500)
    return decorator