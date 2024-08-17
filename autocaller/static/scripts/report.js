function Deletereport(id) {
    let form = document.getElementById("delete_report_form");
    form.action = '/report_delete/' + id;
    }  


function Exportreport(id) {
    let export_form = document.getElementById("export_report_form");
    url = '/report_export/' + id;
    function handle_submit(event) {
        event.preventDefault();
        console.log('123')
        let xhr = new XMLHttpRequest();
        xhr.open('GET', url, false);
        xhr.send();
        if (xhr.readyState == 4) {
            console.log('111')
            if (xhr.status == 200) {
                window.open(url, '_parent');
            }
            else {
                alert(xhr.responseText);
            }
            export_form.removeEventListener('submit', handle_submit);    
        }
        };
    export_form.addEventListener('submit', handle_submit)
    }  

    