function removeExtension(filename){
  var lastDotPosition = filename.lastIndexOf(".");
  if (lastDotPosition === -1) return filename;
  else return filename.substr(0, lastDotPosition);
}


let create_form = document.getElementById('create_sound_form');
let download_form =  document.getElementById('download_sound');
let divs = document.querySelectorAll('.file-cell');
let names = [];
for (let div of divs){
  names.push(div.textContent);
}  
create_form.addEventListener('submit', function(event) {
    let filename = document.getElementById('filename_input').value + '.wav';
    if (names.includes(filename)) {
      let result = confirm('Файл с таким именем уже существует. Перезаписать?');
      if (!result) {
        event.preventDefault();
      }
      else {
        create_form.onsubmit()
      } 
    }
});
download_form.addEventListener('submit', function(event) {
  let file = document.getElementById('file_input').files[0];
  let full_file_name = file.name
  file_name = removeExtension(full_file_name) + '.wav'
  if (names.includes(file_name)) {
    let result = confirm('Файл с таким именем уже существует. Перезаписать?');
    if (!result) {
      event.preventDefault();
    }
    else {
      download_form.onsubmit();
    } 
  }
});


function Deletesound(filename, id) {
  console.log(filename)
  let delete_message = document.getElementById('delete_sound_message');
  let delete_sound_form = document.getElementById("delete_sound_form");
  delete_message.innerHTML = 'Вы действительно хотите удалить файл ' + filename + '?';
  delete_sound_form.action = '/delete_sound/' + id;
}