function ModalEdit(id, first_name, last_name, patronymic, work_phone_number='-', mobile_phone_number='-', secondary_mobile_phone_number='-') {
    console.log(id, first_name, last_name, patronymic, work_phone_number, mobile_phone_number, secondary_mobile_phone_number)
    let first_name_input = document.getElementById("first_name");
    let last_name_input = document.getElementById("last_name");
    let patronymic_input = document.getElementById("patronymic");
    let work_phone_number_input = document.getElementById("work_phone_number");
    let mobile_phone_number_input = document.getElementById("mobile_phone_number");
    let secondary_mobile_phone_number_input = document.getElementById("secondary_mobile_phone_number");
    first_name_input.value = first_name;
    last_name_input.value = last_name;
    patronymic_input.value = patronymic;

    if (work_phone_number === 'None') {
        work_phone_number_input.value = ''
    } else {
        work_phone_number_input.value = work_phone_number;

    }
    if (mobile_phone_number === 'None') {
        mobile_phone_number_input.value = ''
    } else {
        mobile_phone_number_input.value = mobile_phone_number.slice(2);
    }
    if (secondary_mobile_phone_number === 'None') {
        secondary_mobile_phone_number_input.value = ''
    } else {
        secondary_mobile_phone_number_input.value = secondary_mobile_phone_number.slice(2);
    }  
  
    let delete_abonent_form = document.getElementById("delete_abonent_form");
    let edit_abonent_form = document.getElementById("edit_abonent_form");
    edit_abonent_form.action = '/edit_abonent/' + id;
    delete_abonent_form.action = '/delete_abonent/' + id;
    edit_abonent_form.addEventListener('submit', function(event) {
        event.preventDefault();
        let xhr_edit = new XMLHttpRequest();
        let formData = new FormData(edit_abonent_form);
        xhr_edit.open('POST','/edit_abonent/'+ id, false);
        xhr_edit.send(formData);
        if (xhr_edit.readyState == 4) {
            if (xhr_edit.status == 200) {
                window.open('/abonents', '_parent');
                } else {
                alert(xhr_edit.responseText);
                }    
            }
        });
}

let form = document.getElementById("create_abonent");

form.addEventListener('submit', function(event) {
    event.preventDefault();
    let xhr = new XMLHttpRequest();
    let formData = new FormData(form);
    xhr.open('POST','/create_abonent', false);
    xhr.send(formData);
    if (xhr.readyState == 4) {
        if (xhr.status == 200) {
            window.open('/abonents', '_parent');
            } else {
            alert(xhr.responseText);
            }    
        }
    }); 


