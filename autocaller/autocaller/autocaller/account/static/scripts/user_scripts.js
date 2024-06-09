function UserEdit(id, first_name, last_name, patronymic,login, role) {
    console.log(id, first_name, last_name, patronymic, login, role)
    let first_name_input = document.getElementById("first_name");
    let last_name_input = document.getElementById("last_name");
    let patronymic_input = document.getElementById("patronymic");
    first_name_input.value = first_name;
    last_name_input.value = last_name;
    patronymic_input.value = patronymic;

    let edit_abonent_form = document.getElementById("edit_user_form");
    let delete_abonent_form = document.getElementById("delete_user_form");
    let user_edit_modal = document.getElementById("user_edit_modal");
    let role_select = document.getElementById("role_select");
    edit_abonent_form.action = '/account/edit_user/' + id;
    delete_abonent_form.action = '/account/delete_user/' + id;
    user_edit_modal.innerHTML = 'Редактирование пользователя ' + login;
    if (role === 'True') {
        role_select.value = "2";
    }
    else {
        role_select.value = "1";
    }   
}

let create_user_form = document.getElementById("create_user");

create_user_form.addEventListener('submit', function(event) {
    event.preventDefault();
    let xhr = new XMLHttpRequest();
    let formData = new FormData(create_user_form);
    xhr.open('POST','/account/create_user', false);
    xhr.send(formData);
    if (xhr.readyState == 4) {
        if (xhr.status == 200) {
            window.open('/abonents', '_parent');
            } else {
            alert(xhr.responseText);
            }    
        }
    });