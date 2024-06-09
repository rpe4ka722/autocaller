def form_errors_text(form):
    error_list = []
    for field in form:
        error_list.append(field.errors.as_text().replace('* ', ''))
    return ' '.join(error_list).strip()