let progress = document.getElementById("bar_percents");
let report_id = document.getElementById("rep_id").innerText;
let url = '/percent_status/'+ report_id;
let end_url = '/report_status/'+ report_id;
let confirmed_count = document.getElementById("confirmed_count");
let unconfirmed_count = document.getElementById("unconfirmed_count");
let confirmed = '';
let unconfirmed = '';
let repeat_call_url = '/repeat_unconfirmed/' + report_id;


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
    let end_response = await fetch(end_url);
    let end_data = await end_response.json();
    let unconfirmedAbonentsList = end_data.unconfirmed_abonents.map(abonent => abonent.full_name).join('\n');
    alert("Оповещение завершено. Оповещено: " + confirmed + ". Не оповещено: " + unconfirmed  
        + '\n' + "Перечень абонентов не подтвердивших получение сообщения: " + '\n' + unconfirmedAbonentsList);
    window.open('/', '_parent');
    // if (result) {
    //   window.open(repeat_call_url, '_parent');
    // } else {
    //   window.open('/', '_parent');
    // } 
    
}

// async function progress_bar() {
//     let flag = true;
//     try {
//         do {
//             await delay(1000);
//             let response = await fetch(url);
            
//             if (!response.ok) {
//                 throw new Error(`HTTP error! status: ${response.status}`);
//             }
            
//             let data = await response.json();
            
//             // Обновление UI
//             progress.style.width = data.percents + '%';
//             progress.innerHTML = data.percents + '%';
//             confirmed_count.innerHTML = 'Абонентов оповещено: ' + data.abonent_confirmed;
//             confirmed = data.abonent_confirmed;
//             unconfirmed_count.innerHTML = 'Абонентов не оповещено: ' + data.abonent_unconfirmed;
//             unconfirmed = data.abonent_unconfirmed;
//             flag = data.in_progress;
            
//         } while (flag === true);
        
//         await delay(1000);
        
//         // Финальный запрос
//         let end_response = await fetch(end_url);
//         if (!end_response.ok) {
//             throw new Error('Ошибка при получении финального статуса');
//         }
        
//         let end_data = await end_response.json();
//         let unconfirmedAbonentsList = '';
        
//         // Проверка существования массива
//         if (Array.isArray(end_data.unconfirmed_abonents)) {
//             unconfirmedAbonentsList = end_data.unconfirmed_abonents
//                 .map(abonent => abonent.full_name)
//                 .filter(name => name) // Фильтрация пустых имен
//                 .join('\n');
//         }
        
//         // Создание более читаемого сообщения
//         let message = `Оповещение завершено.\n\n` +
//                      `Оповещено: ${confirmed}\n` +
//                      `Не оповещено: ${unconfirmed}`;
        
//         if (unconfirmedAbonentsList) {
//             message += `\n\nПеречень абонентов, не подтвердивших получение сообщения:\n${unconfirmedAbonentsList}`;
//         }
        
//         alert(message);
//         window.open('/', '_parent');
        
//     } catch (error) {
//         console.error('Ошибка в progress_bar:', error);
//         alert(`Ошибка: ${error.message}. Попробуйте обновить страницу.`);
//         window.open('/', '_parent');
//     }
// }

progress_bar()