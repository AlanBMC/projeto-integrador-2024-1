$(".sidebar-dropdown > a").click(function () {
    $(".sidebar-submenu").slideUp(200);
    if ($(this).parent().hasClass("active")) {
        $(".sidebar-dropdown").removeClass("active");
        $(this).parent().removeClass("active");
    } else {
        $(".sidebar-dropdown").removeClass("active");
        $(this).next(".sidebar-submenu").slideDown(200);
        $(this).parent().addClass("active");
    }
});
$("#close-sidebar").click(function () {
    $(".page-wrapper").removeClass("toggled");
});
$("#show-sidebar").click(function () {
    $(".page-wrapper").addClass("toggled");
});

function ver_resposta(cardId) {
    var div_resposta = document.getElementById('ver_resposta_' + cardId);
    if (div_resposta.style.display === 'block') {
        div_resposta.style.display = 'none';
    } else {
        div_resposta.style.display = 'block';
    }
}


function abre_modal_sol(){
    var modal = document.getElementById('modalSol')
    modal.style.display='block'
    
}

function fecha_modal_sol(){
    var modal = document.getElementById('modalSol')
    modal.style.display='none'
}

function updateLabel() {
    var input = document.getElementById('imagem');
    var fileName = input.files[0].name;
    document.getElementById('file-chosen').innerText = fileName;
}