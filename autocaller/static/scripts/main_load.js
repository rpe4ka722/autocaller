let progress = document.getElementById("bar_percents");
let report_id = document.getElementById("rep_id").innerText;
let url = '/percent_status/'+ report_id;
let confirmed_count = document.getElementById("confirmed_count");
let unconfirmed_count = document.getElementById("unconfirmed_count");
let confirmed = '';
let unconfirmed = '';


function delay(ms) {
    return new Promise(resolve => setTimeout(resolve, ms));
  }

async function progress_bar() {
    let flag = true;
    do {
        await delay(1000);
        let response = await fetch(url);
        if (response.ok) {
            let data = await response.json();
            progress.style.width = data.percents + '%';
            progress.innerHTML = data.percents + '%';
            confirmed_count.innerHTML ='Абонентов оповещено: ' + data.abonent_confirmed;
            confirmed =  data.abonent_confirmed;
            unconfirmed_count.innerHTML ='Абонентов не оповещено: ' + data.abonent_unconfirmed;
            unconfirmed =  data.abonent_unconfirmed;
            flag = data.in_progress;
        } else {
            alert("Неизвестная ошибка");
            window.open('/', '_parent');
        }
    }   while (flag == true);
    await delay(1000);
    alert("Оповещение завершено. Оповещено: " + confirmed + ". Не оповещено: " + unconfirmed) 
    window.open('/', '_parent');
}

progress_bar()