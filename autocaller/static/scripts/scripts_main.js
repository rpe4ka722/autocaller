function PlayFunc(cardid, list_name) {
    let list_id = 'card_' + cardid;
    let card = document.getElementById(list_id);
    let myModal = document.getElementById('PlayList');
    let message = document.getElementById('play_list_message');
    let form = document.getElementById('start_call');
    let list_start_call_url = 'start_list/' + cardid;
    card.style = 'box-shadow: 2px 2px 4px rgba(10, 10, 10, 0.5); transform: translate(-5px, -5px);';
    message.innerHTML = 'Вы действительно хотет запустить оповещение абонентов по списку ' + list_name + '?';
    myModal.addEventListener('hide.bs.modal', () => {
        card.style = '';    
    })
    form.action = list_start_call_url
}


