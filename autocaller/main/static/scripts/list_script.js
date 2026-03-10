function EditFunc(cardid, name, description, abon_list, is_mobile, is_secondary, is_work, accept_code, password) {
    let list_id = 'card_' + cardid;
    let card = document.getElementById(list_id);
    let myModal = document.getElementById('EditList');
    let delete_form = document.getElementById('delete_list_form');
    let title = document.getElementById('EditListModalTitle');
    let list_description = document.getElementById('list_description');
    let timestamp = new Date().getTime();
    let abon_set = abon_list.split(';').slice(0, -1)
    let call_paragraph_div = document.getElementById('call_paragaph');
    let abonents_list_ul= document.getElementById('abonents_list_id');
    let edit_button = document.getElementById('edit_button_url');
    let accept_code_block = document.getElementById('accept_code_modal');
    let password_block = document.getElementById('password_modal');

    call_paragraph_div.innerHTML = '';
    abonents_list_ul.innerHTML = '';

    if (is_mobile === 'True') {
        let paragraph = document.createElement('p');
        paragraph.class = 'call_method_id';
        paragraph.innerHTML = '<i class="bi bi-phone"></i> - на мобильный';
        call_paragraph_div.append(paragraph);
    } else {
        null;
    }
    if (is_secondary === 'True') {
        let paragraph = document.createElement('p');
        paragraph.class = 'call_method_id';
        paragraph.innerHTML = '<i class="bi bi-phone"></i> - на дополнительный';
        call_paragraph_div.append(paragraph);
    } else {
        null;
    }
    if (is_work === 'True') {
        let paragraph = document.createElement('p');
        paragraph.class = 'call_method_id';
        paragraph.innerHTML = '<i class="bi bi-telephone"></i> - на рабочий';
        call_paragraph_div.append(paragraph);
    } else {
        null;
    }
    for (let abon of abon_set) {
        let li = document.createElement('li');
        li.innerHTML = abon;
        abonents_list_ul.append(li);
    }

    title.innerHTML = 'Список оповещения ' + name;
    list_description.innerHTML = description;
    accept_code_modal.innerHTML = accept_code;
    password_modal.innerHTML = password;
    delete_form.action = 'delete_list/' + cardid;
    card.style = 'box-shadow: 2px 2px 4px rgba(10, 10, 10, 0.5); transform: translate(-5px, -5px);';
    myModal.addEventListener('hide.bs.modal', () => {
        card.style = '';
        call_paragraph_div.innerHTML = '';
        abonents_list_ul.innerHTML = '';
    })
}

function CreateFunc() {
    let card = document.getElementById('create_card');
    let myModal = document.getElementById('CreateList');
    let form = document.getElementById('create_list_form');
    card.style = 'box-shadow: 2px 2px 4px rgba(10, 10, 10, 0.5); transform: translate(-5px, -5px);';
    myModal.addEventListener('hide.bs.modal', () => {
        card.style = '';
        form.reset();
        abonent_list = [];   
        document.querySelectorAll('.added_abonents_div').forEach(div => div.remove());
    }, { once: true })
}

let abonent_list = [];
const abonents_input = document.getElementById('abonents_input');
const abonents_datalist = document.getElementById('abonents_add');
const form = document.getElementById('create_list_form');

function AddAbonentFunc() {
    let abonent_option = document.querySelector("#abonents_add option[value='" + abonents_input.value + "']");
    console.log(abonent_option)
    if (abonents_input.value == "") {
        null;   
    }
    else if (abonent_option == null) {
        alert('Выберите абонента из списка')
    }
    else {
        abonent_list.push(abonents_input.value);
        let opt_value_list = abonents_datalist.querySelectorAll('option');
        for (let opt of opt_value_list) {
            if (opt.value === abonents_input.value) {
                opt.remove();
            }
            else {
                null;
            }
        }

        //создаем новый элемент с ФИО абонента
        let div = document.createElement('div');
        div.className = "added_abonents_div";
        div.id = 'div_' + abonents_input.value.replaceAll(' ', '');
        div.innerHTML = abonents_input.value; 

        //добавляем блок ссылки удаления элемента
        let div_buttton = document.createElement('div');
        div_buttton.className = "trash_div_abonents";
        
        //добавляем ссылку удаления элемента
        let del_button = document.createElement('a');
        del_button.className = "trash-icon";
        del_button.id = abonents_input.value.replaceAll(' ', '');
        del_button.innerHTML = '<i class="bi bi-x-lg"></i>';

        //функция кнопки удаления
        del_button.onclick = (event) => {
            let id = del_button.id
            let added_abonent_item = document.getElementById('div_' + id);
            let added_abonent_item_text = added_abonent_item.textContent
            let new_option = document.createElement('option');
            new_option.value = added_abonent_item_text;
            abonents_datalist.append(new_option);
            added_abonent_item.remove();
            let abonents_index = abonent_list.indexOf(added_abonent_item_text);
            abonent_list.splice(abonents_index, 1);
            console.log(abonent_list);
        }

        //размещение элементов
        form.append(div);
        div.append(div_buttton);
        div_buttton.append(del_button);
        //очищение поля ввода
        abonents_input.value = '';
        //вывод итогового списка
        console.log(abonent_list);
    }
}

function PasswordFunc() {
    let checkbox = document.getElementById('is_passwd_switch');
    let input_area = document.querySelector('.password_input_class');
    let password_input = document.getElementById('password_input');

    if (checkbox.checked) {
        input_area.style.display = 'none';
        password_input.required = false;
        password_input.value = '';
    } else {
        input_area.style.display = 'block';
        password_input.required = true;
        
    }
}

form.addEventListener('submit', function(event) {
    event.preventDefault();
    let xhr = new XMLHttpRequest();
    let formData = new FormData(form);
    if (abonent_list.length !== 0)    {
        formData.append('abonents_list', abonent_list);
        data = formData;
        xhr.open('POST','/create_list', false);
        xhr.send(data);
        if (xhr.readyState == 4) {
            if (xhr.status == 200) {
                window.open('/lists', '_parent');
            }
        else {
            alert(xhr.responseText);
        }    
        }
    } else if (abonent_list.length === 0) {
        alert('Вы не добавили абонентов в список');
    }
    else {
        null;
    }
  });

