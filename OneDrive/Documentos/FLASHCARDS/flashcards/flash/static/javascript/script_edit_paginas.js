function abre_modal_delete_pg(pagina_id, pagina_titulo){
    var modal = document.getElementById('modal_delete_pg')
    modal.style.display = 'block'
    console.log(pagina_titulo)
    document.getElementById('id_pagina_delete').value = pagina_id
    document.getElementById('titulo').textContent  = pagina_titulo
}

function fecha_modal_delete_pg(){
    var modal = document.getElementById('modal_delete_pg')
    modal.style.display = 'none'
}

function abre_modal_edit_pg(titulo, pagina_id){
    var modal = document.getElementById('modal_edit_titulo_pg')
    modal.style.display = 'block'
    console.log(titulo)
    document.getElementById('id_pagina_edit').value = pagina_id
    document.getElementById('titulo2').value = titulo
}
function fecha_modal_edit_pg(){
    var modal = document.getElementById('modal_edit_titulo_pg')
    modal.style.display = 'none'
}