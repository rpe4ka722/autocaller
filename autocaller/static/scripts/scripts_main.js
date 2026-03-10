let currentListId = null;

function PlayFunc(cardid, list_name) {
    let list_id = 'card_' + cardid;
    let card = document.getElementById(list_id);
    let myModal = document.getElementById('PlayList');
    let message = document.getElementById('play_list_message');
    let soundform = document.getElementById('sound_input');

    currentListId = cardid;

    card.style = 'box-shadow: 2px 2px 4px rgba(10, 10, 10, 0.5); transform: translate(-5px, -5px);';
    message.innerHTML = 'Вы действительно хотите запустить оповещение абонентов по списку ' + list_name + '?';
    myModal.addEventListener('hide.bs.modal', () => {
        card.style = '';    
    })
    

    document.getElementById('play_button').disabled = true;
    soundform.value = '';
}

function SoundPick() {
    let form = document.getElementById('start_call');
    let soundform = document.getElementById('sound_input');
    let encoded_soundname = encodeURIComponent(soundform.value);
    let button = document.getElementById('play_button');
    let list_start_call_url = 'start_list/' + currentListId + '/' + encoded_soundname;
    form.action = list_start_call_url

    button.disabled = false;
    console.log(`Сформированный URL: ${list_start_call_url}`);

}
