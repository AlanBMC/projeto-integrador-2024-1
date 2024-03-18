function abremodal_addpg_card_aluno() {
    console.log('abrindo modal add pagina card aluno')
    var modal = document.getElementById('modal_add_pg_card')
    modal.style.display = 'block'
}
function fechamodal_addpg_aluno() {
    console.log('fechando modal add pg aluno')
    var modal = document.getElementById('modal_add_pg_card')
    modal.style.display = "none"
}

// ---------------------------------------------------- fazer
function abremodal_addpg_simulado_aluno() {
    console.log('abrindo modal add pg simulado')
}

// -----------------------------------------------------fim simulado



function ver_resposta_card_aluno(cardId) {
    var div_resposta = document.getElementById('ver_resposta_' + cardId);
    if (div_resposta.style.display === 'block') {
        div_resposta.style.display = 'none';
    } else {
        div_resposta.style.display = 'block';
    }
}
function abre_modal_add_cards() {
    var modal = document.getElementById('modal_add_flashcard')
    modal.style.display = 'block'
}
function fecha_modal_add_card() {
    var modal = document.getElementById('modal_add_flashcard')
    modal.style.display = 'none'
}




function abre_modal_edit_cards(cardid, pergunta, resposta) {
    var modal = document.getElementById('modal_edit_card_aluno')
    modal.style.display = 'block'
    document.getElementById('card_id').value = cardid
    document.getElementById('pergunta_card').value = pergunta
    document.getElementById('resposta_card').value = resposta
}

function fecha_modal_edit_card() {
    var modal = document.getElementById('modal_edit_card_aluno')
    modal.style.display = 'none'
}



function abre_modal_delete_card_aluno(cardid, paginaid) {
    var modal = document.getElementById('modal_delete_card')
    modal.style.display = "block"
    document.getElementById('id_card').value = cardid
    document.getElementById('id_pagina_do_card').value = paginaid
}

function delete_card_fecha_modal() {
    var modal = document.getElementById('modal_delete_card')
    modal.style.display = 'none'
}

function abre_modal_add_pagina_simulado_e_pergunta() {
    var modal = document.getElementById('modal_adiciona_pagina_simulado_e_pergunta')
    modal.style.display = 'block'
}

function fecha_modal_add_pagina_simulado_e_pergunta() {
    var modal = document.getElementById('modal_adiciona_pagina_simulado_e_pergunta')
    modal.style.display = 'none'
}
// TEMPLATE SIMULADO_ALUNO
function abre_modal_add_perguntas_simulados() {

}

function abre_modal_edit_questao(simuladoid, pergunta, a, b, c, d, paginaid) {
    var modal = document.getElementById('modal_edit_questao_aluno')
    modal.style.display = 'block'
    var aa = document.getElementById('alternativaa')
    var bb = document.getElementById('alternativab')
    var cc = document.getElementById('alternativac')
    var dd = document.getElementById('alternativad')
    var perg = document.getElementById('perguntaa')
    var qid = document.getElementById('id_questao')
    var pgid = document.getElementById('id_pagina')
    pgid.value = paginaid
    qid.value = simuladoid
    perg.value = pergunta
    aa.value = a
    bb.value = b
    cc.value = c
    dd.value = d
    console.log(pergunta, a, b, c, paginaid)
}

function fecha_modal_edit_questao() {
    var modal = document.getElementById('modal_edit_questao_aluno')
    modal.style.display = 'none'

}

function abrir_modal_delete_questao(paginaid, simuladoid) {
    var modal = document.getElementById('modal_delete_questao')
    modal.style.display = 'block'
    document.getElementById('id_questao_delete').value = simuladoid
    document.getElementById('id_pagina_delete').value = paginaid
}

function fechar_modal_delete_questao() {
    var modal = document.getElementById('modal_delete_questao')
    modal.style.display = 'none'
}