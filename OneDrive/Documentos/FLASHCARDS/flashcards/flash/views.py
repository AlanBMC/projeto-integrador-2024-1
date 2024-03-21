from django.shortcuts import render
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_exempt
from django.urls import reverse
from django.contrib.auth.models import User
from django.contrib.auth import authenticate
from django.contrib.auth import login as login_django
from django.db import IntegrityError
from .models import Usuario, Pagina, Cards, Simulados, EstatisticasSimulado, EnemRespostas, EstatisticasEnem_usuario, EstatisticasSimulado_compartilhada
from django.contrib import messages
from django.contrib.auth import logout
from django.core.exceptions import ObjectDoesNotExist
import requests
import google.generativeai as genai
from django.contrib.auth import update_session_auth_hash
import random
from collections import defaultdict

# Create your views here.


# ---- INICO BLOCO: login e cadastro
def cadastro(request):
    """
    View para processar o formulário de cadastro de usuários.

    Recebe um objeto 'request' e verifica se o método é POST.
    Se for POST, extrai os dados do formulário e cria um novo usuário.
    Se o nome de usuário já existir, exibe uma mensagem de erro.
    Salva o usuário e sua foto de perfil se fornecida.
    Cria páginas iniciais para o usuário e redireciona para a página de login.
    Se o método não for POST, renderiza a página de cadastro.

    Parâmetros:
        - request: objeto HttpRequest contendo os dados da requisição.

    Retorno:
        - Se o método for POST e o cadastro for bem-sucedido, redireciona para a página de login.
        - Se o método não for POST, renderiza a página de cadastro.
        - Se o nome de usuário já existir, renderiza a página de cadastro com uma mensagem de erro.
    """
    if request.method == 'POST':
        username = request.POST.get('username')
        arroba = request.POST.get('arroba')
        senha = request.POST.get('password')
        tipo_user = request.POST.get('tipo_user')
        img = request.FILES.get('imagem_de_perfil', None)
        if User.objects.filter(username=username).exists():
            # Usar mensagens para enviar feedback ao usuário
            return render(request, 'cadastro.html', {'error_message': 'Nome de usuário já existe. Por favor, escolha outro nome.'})
        else:
            user = User.objects.create_user(
                username=username, email=arroba, password=senha)
            user.save()
            usuario = Usuario(arroba=username, tipo_user=tipo_user)
            if img:
                usuario.foto_perfil = img
            else:
                messages.error(request, 'Coloque uma foto de perfil')
                return redirect('cadastro')
            usuario.save()
            # retirar perguntas e respostas.
            pagina = Pagina.objects.create(
                titulo='Home')
            primeira_pagina_simulado = Pagina.objects.create(
                titulo='Crie simulados')
            Simulados.objects.create(pergunta='No botao a esquerda vc cria pergunta com alternativas', alternativa_a='No botão sol existe uma IA que traduz e uma api que gera algumas questoes.',
                                     alternativa_b='Preencha todas as questoes e veja as estatisticas quando quiser', alternativa_c='As estatisticas fica na parte inferior da aba perfil, ao lado da configuração', alternativa_d='Isso é tudo, bons estudos', pagina=primeira_pagina_simulado)
            usuario.paginas.add(pagina)
            usuario.paginas.add(primeira_pagina_simulado)
            return redirect('login')
    else:
        return render(request, 'cadastro.html')


def home(request):
    """
    View para renderizar a página inicial.

    Recebe um objeto 'request' e renderiza o template 'home.html'.

    Parâmetros:
        - request: objeto HttpRequest contendo os dados da requisição.

    Retorno:
        - Renderiza a página inicial 'home.html'.
    """
    return render(request, 'home.html')


def login_user(request):
    """
    View para processar o formulário de login do usuário.

    Recebe um objeto 'request' e verifica se o método é POST.
    Se for POST, autentica o usuário e realiza o login.
    Redireciona para a página correspondente ao usuário após o login.
    Se o método não for POST, renderiza a página de login.

    Parâmetros:
        - request: objeto HttpRequest contendo os dados da requisição.

    Retorno:
        - Se o método for POST e o login for bem-sucedido, redireciona para a página correspondente ao usuário.
        - Se o método não for POST, renderiza a página de login.
        - Se as credenciais estiverem incorretas, renderiza a página de login com uma mensagem de erro.
    """
    if request.method == 'POST':
        nome = request.POST.get('username')
        senha = request.POST.get('password')
        user = authenticate(username=nome, password=senha)
        if user:
            login_django(request, user)
            try:
                usuario = Usuario.objects.get(arroba=nome)
                pagina = usuario.paginas.all().first()
                if pagina:
                    # ATENCAO : REDIRECT PAGINA.
                    return redirect('paginas', pagina.id)
                else:
                    return redirect('login')
            except Usuario.DoesNotExist:

                return render(request, 'login', {'erro': 'Usuário ou Senha Incorreto'})

        else:
            return render(request, 'login.html', {'erro': 'Usuário ou Senha Incorreto'})
    else:
        return render(request, 'login.html')


def logout_view(request):
    """
    View para realizar o logout do usuário.

    Realiza o logout do usuário e redireciona para a página de login.

    Parâmetros:
        - request: objeto HttpRequest contendo os dados da requisição.

    Retorno:
        - Redireciona para a página de login após o logout.
    """
    logout(request)
    return redirect('login')
# ---- FIM BLOCO login e cadastro


# ---- INICO BLOCO: paginacao
@login_required(login_url="/usuario/login/")
def paginas(request, pagina_id):
    """
    View para exibir as páginas do usuário.

    Recebe um objeto 'request' e o 'pagina_id' da página a ser exibida.
    Verifica se o usuário está autenticado e se possui permissão para acessar a página.
    Renderiza a página correspondente ao tipo de usuário (aluno ou professor).
    Se o usuário não tiver permissão para acessar a página, renderiza a página padrão.

    Parâmetros:
        - request: objeto HttpRequest contendo os dados da requisição.
        - pagina_id: identificador da página a ser exibida.

    Retorno:
        - Renderiza a página correspondente ao tipo de usuário.
        - Se o usuário não tiver permissão para acessar a página, renderiza a página padrão.
    """
    usuario_nome = request.user.username
    print(pagina_id)
    usuario = get_object_or_404(Usuario, arroba=usuario_nome)
    conteudos = conteudo_geral(request, pagina_id)

    if usuario.paginas.filter(id=pagina_id).exists():
        if usuario.tipo_user == 'aluno':
            return render(request, 'aluno.html', conteudos)
        elif usuario.tipo_user == 'professor':
            return render(request, 'professor.html', conteudos)

    return render(request, 'pagina.html', conteudos)
# ---- FIM BLOCO: paginacao


# ---- INICO BLOCO: cards
def add_pagina_card(request):
    """
    View para adicionar um card à página.

    Recebe um objeto 'request' e verifica se o método é POST.
    Extrai os dados do formulário e cria um novo card associado à página do usuário.
    Redireciona para a página com o novo card adicionado.

    Parâmetros:
        - request: objeto HttpRequest contendo os dados da requisição.

    Retorno:
        - Se o método for POST e o card for adicionado com sucesso, redireciona para a página com o novo card.
    """
    if request.method == 'POST':
        titulo = request.POST.get('titulo_pg_card')
        pergunta = request.POST.get('pergunta_card')
        resposta = request.POST.get('resposta_card')
        user_arroba = request.user.username
        usuario = Usuario.objects.get(arroba=user_arroba)
        nova_pagina = Pagina.objects.create(titulo=titulo)
        usuario.paginas.add(nova_pagina)
        Cards.objects.create(perguntas=pergunta,
                             respostas=resposta, pagina=nova_pagina)
        return redirect('paginas', nova_pagina.id)


def add_cards(request):
    """
    View para adicionar um card à página.

    Recebe um objeto 'request' e verifica se o método é POST.
    Extrai os dados do formulário e cria um novo card associado à página especificada.
    Redireciona para a página com o novo card adicionado.

    Parâmetros:
        - request: objeto HttpRequest contendo os dados da requisição.

    Retorno:
        - Se o método for POST e o card for adicionado com sucesso, redireciona para a página com o novo card.
    """
    if request.method == 'POST':
        pergunta = request.POST.get('pergunta_card')
        resposta = request.POST.get('resposta_card')
        id_pagina = request.POST.get('id_pagina')
        pagina = Pagina.objects.get(id=id_pagina)
        Cards.objects.create(perguntas=pergunta,
                             respostas=resposta, pagina=pagina)
        return redirect('paginas', id_pagina)


@login_required
@require_POST
def edit_cards(request):
    """
    View para editar um card.

    Recebe um objeto 'request' e verifica se o método é POST.
    Extrai os dados do formulário e atualiza o card correspondente.
    Redireciona para a página onde o card foi editado.

    Parâmetros:
        - request: objeto HttpRequest contendo os dados da requisição.

    Retorno:
        - Se o método for POST e o card for editado com sucesso, redireciona para a página onde o card foi editado.
    """
    if request.method == 'POST':
        card_id = request.POST.get('card_id')
        pagina_id = request.POST.get('pagina_id')
        pergunta_card = request.POST.get('pergunta_editada')
        resposta_card = request.POST.get('resposta_editada')
        Cards.objects.filter(id=card_id).update(
            perguntas=pergunta_card, respostas=resposta_card)
        return redirect('paginas', pagina_id)


@require_POST
def delete_card(request):
    """
    View para excluir um card.

    Recebe um objeto 'request' e verifica se o método é POST.
    Extrai o ID do card a ser excluído e o exclui do banco de dados.
    Redireciona para a página onde o card foi excluído.

    Parâmetros:
        - request: objeto HttpRequest contendo os dados da requisição.

    Retorno:
        - Se o método for POST e o card for excluído com sucesso, redireciona para a página onde o card foi excluído.
    """
    if request.method == 'POST':
        card_id = request.POST.get('id_card')
        id_pagina = request.POST.get('id_pagina_do_card')
        card = get_object_or_404(Cards, id=card_id)
        card.delete()
        return redirect('paginas', id_pagina)
# ---- FIM BLOCO: cards


# ---- INICO BLOCO: SIMULADO
@login_required
def simulado(request, simulado_id):
    """
    View para exibir um simulado.

    Recebe um objeto 'request' e o 'simulado_id' do simulado a ser exibido.
    Retorna a renderização da página do simulado com os conteúdos correspondentes.

    Parâmetros:
        - request: objeto HttpRequest contendo os dados da requisição.
        - simulado_id: identificador do simulado a ser exibido.

    Retorno:
        - Renderiza a página do simulado com os conteúdos correspondentes.
    """

    conteudos_ = conteudo_geral(request, simulado_id)
    return render(request, 'simulado.html',  conteudos_)


@login_required
@require_POST
def add_pagina_simulado(request):
    """
    View para adicionar uma nova página de simulado.

    Recebe um objeto 'request' e verifica se o método é POST.
    Extrai os dados do formulário e cria uma nova página de simulado associada ao usuário atual.
    Redireciona para a página de simulado correspondente.

    Parâmetros:
        - request: objeto HttpRequest contendo os dados da requisição.

    Retorno:
        - Se o método for POST e a página de simulado for adicionada com sucesso, redireciona para a página de simulado correspondente.
    """
    user_atual = request.user.username
    usuario_atual = Usuario.objects.get(arroba=user_atual)

    todas_as_paginas = usuario_atual.paginas.all()
    paginas_simulados = Simulados.objects.filter(
        pagina__in=todas_as_paginas).distinct()
    primeira_pagina_simulado = paginas_simulados.first()

    if request.method == 'POST':
        titulo = request.POST.get('titulo_pagina')
        pergunta_simulado = request.POST.get('pergunta_simulado')
        alternativa_a = request.POST.get('alternativa_a_simulado')
        alternativa_b = request.POST.get('alternativa_b_simulado')
        alternativa_c = request.POST.get('alternativa_c_simulado')
        alternativa_d = request.POST.get('alternativa_d_simulado')
        alternativa_correta = request.POST.get('alternativa_correta')
        nova_pagina = Pagina.objects.create(titulo=titulo)
        if not alternativa_correta:
            messages.error(request, 'Adicione uma alternativa correta')
            return redirect('simulado', primeira_pagina_simulado.id)
        Simulados.objects.create(pergunta=pergunta_simulado, alternativa_a=alternativa_a,
                                 alternativa_b=alternativa_b, alternativa_c=alternativa_c,
                                 alternativa_d=alternativa_d, correta=alternativa_correta, pagina=nova_pagina)
        usuario_atual = request.user.username
        usuario = Usuario.objects.get(arroba=usuario_atual)
        usuario.paginas.add(nova_pagina)
        return redirect('simulado', nova_pagina.id)
    else:
        return redirect('simulado', nova_pagina.id)


@login_required
@require_POST
def questao_simulado(request):
    """
    View para adicionar uma nova questão ao simulado.

    Recebe um objeto 'request' e verifica se o método é POST.
    Extrai os dados do formulário e cria uma nova questão associada à página de simulado especificada.
    Redireciona para a página de simulado correspondente.

    Parâmetros:
        - request: objeto HttpRequest contendo os dados da requisição.

    Retorno:
        - Se o método for POST e a questão for adicionada com sucesso, redireciona para a página de simulado correspondente.
    """
    if request.method == 'POST':

        pergunta_simulado = request.POST.get('pergunta_simulado')
        alternativa_a = request.POST.get('alternativa_a_simulado')
        alternativa_b = request.POST.get('alternativa_b_simulado')
        alternativa_c = request.POST.get('alternativa_c_simulado')
        alternativa_d = request.POST.get('alternativa_d_simulado')
        alternativa_correta = request.POST.get('alternativa_correta')
        id_pagina = request.POST.get('id_pagina')
        if not alternativa_correta:
            messages.error(
                request, "Você precisa marcar a alternativa correta")
            return redirect('simulado', id_pagina)
        id_pagina = request.POST.get('id_pagina')
        pagina = Pagina.objects.get(id=id_pagina)
        simulado = Simulados.objects.create(pergunta=pergunta_simulado, alternativa_a=alternativa_a,
                                            alternativa_b=alternativa_b, alternativa_c=alternativa_c,
                                            alternativa_d=alternativa_d, correta=alternativa_correta, pagina=pagina)

        simulado.save()
        return redirect('simulado', id_pagina)
    else:
        return redirect('simulado', id_pagina)


@login_required
@require_POST
def edit_questao(request):
    """
    View para editar uma questão do simulado.

    Recebe um objeto 'request' e verifica se o método é POST.
    Extrai os dados do formulário e atualiza a questão correspondente.
    Redireciona para a página de simulado correspondente.

    Parâmetros:
        - request: objeto HttpRequest contendo os dados da requisição.

    Retorno:
        - Se o método for POST e a questão for editada com sucesso, redireciona para a página de simulado correspondente.
    """
    if request.method == 'POST':
        pergunta_simulado = request.POST.get('pergunta_questao_aluno')
        alternativa_a = request.POST.get('alternativa_a_q_aluno')
        alternativa_b = request.POST.get('alternativa_b_q_aluno')
        alternativa_c = request.POST.get('alternativa_c_q_aluno')
        alternativa_d = request.POST.get('alternativa_d_q_aluno')
        alternativa_correta = request.POST.get('alternativa_correta_aluno')
        id_pagina = request.POST.get('id_pagina')
        id_questao = request.POST.get('id_questao')
        print(pergunta_simulado, alternativa_a, alternativa_b, alternativa_c,
              alternativa_d, alternativa_correta, id_pagina, id_questao)
        if not alternativa_correta:
            messages.error(request, 'Adicione uma alternativa correta')
            return redirect('simulado', id_pagina)
        Simulados.objects.filter(id=id_questao).update(pergunta=pergunta_simulado,
                                                       alternativa_a=alternativa_a,
                                                       alternativa_b=alternativa_b,
                                                       alternativa_c=alternativa_c,
                                                       alternativa_d=alternativa_d,
                                                       correta=alternativa_correta)
        messages.success(
            request, 'Questão atualizada')
        return redirect('simulado', id_pagina)


@require_POST
@login_required
def delete_questao(request):
    """
    View para excluir uma questão do simulado.

    Recebe um objeto 'request' e verifica se o método é POST.
    Extrai o ID da questão a ser excluída e a exclui do banco de dados.
    Redireciona para a página de simulado correspondente.

    Parâmetros:
        - request: objeto HttpRequest contendo os dados da requisição.

    Retorno:
        - Se o método for POST e a questão for excluída com sucesso, redireciona para a página de simulado correspondente.
    """
    if request.method == 'POST':
        id_questao = request.POST.get('id_questao')
        id_pagina = request.POST.get('id_pagina')
        simulado = get_object_or_404(Simulados, id=id_questao)
        simulado.delete()
        return redirect('simulado', id_pagina)


@login_required
def checa_resposta_simulado(request):
    """
    View para verificar as respostas do simulado submetido pelo usuário.

    Recebe um objeto 'request' e verifica se o método é POST.
    Extrai as respostas do usuário e verifica se estão corretas.
    Atualiza as estatísticas do simulado do usuário com as respostas.
    Redireciona para a página do simulado.

    Parâmetros:
        - request: objeto HttpRequest contendo os dados da requisição.

    Retorno:
        - Se o método for POST e as respostas forem verificadas com sucesso, redireciona para a página do simulado.
    """
    if request.method == 'POST':
        usuario = request.user.username
        usuario_ = Usuario.objects.get(arroba=usuario)
        id_pagina = request.POST.get('id_pagina')
        pergunta_simulado = request.POST.get('pergunta_simulado')
        pagina = get_object_or_404(Pagina, id=id_pagina)

        estatisticas = EstatisticasSimulado.objects.create(
            usuario=usuario_, pagina=pagina)

        questoes = Simulados.objects.filter(pagina_id=id_pagina)
        acertos = 0
        erros = 0
        for questao in questoes:
            alternativa_correta_marcada = request.POST.get(
                f'alternativas_{questao.id}')
            if pergunta_simulado == 'No botão sol existe uma IA que traduz e uma api que gera algumas questoes. RESPOSTA CORRETA É A LETRA A':
                estatisticas.questoes_corretas.add(questao)
                acertos += 1
            else:
                if alternativa_correta_marcada and alternativa_correta_marcada == questao.correta:
                    estatisticas.questoes_corretas.add(questao)
                    acertos += 1
                else:
                    estatisticas.questoes_erradas.add(questao)
                    erros += 1
        if acertos == len(questoes):
            messages.success(
                request, f'Parabéns! Você acertou todas as {acertos + erros} questões. De {acertos + erros} questões')
        else:
            messages.error(
                request, f'Você acertou {acertos} questões e errou {erros}. De {acertos + erros} questões')

        # jogar para uma outra pagina de sucesso.
        return redirect('simulado', id_pagina)

# ---- FIM BLOCO: SIMULADO


# ---- INICO BLOCO: enem
def enem(request, enem_d):
    """
    View para exibir a página do simulado ENEM.

    Recebe um objeto 'request' e o 'enem_d' (identificador do simulado ENEM) a ser exibido.
    Retorna a renderização da página do simulado ENEM com os conteúdos correspondentes.

    Parâmetros:
        - request: objeto HttpRequest contendo os dados da requisição.
        - enem_d: identificador do simulado ENEM a ser exibido.

    Retorno:
        - Renderiza a página do simulado ENEM com os conteúdos correspondentes.
    """
    conteudo = conteudo_geral_enem(request, enem_d)

    return render(request, 'enem.html', conteudo)


def resposta_enem(request):
    """
    View para processar as respostas do simulado ENEM submetido pelo usuário.

    Recebe um objeto 'request' e verifica se o método é POST.
    Extrai as respostas do usuário, verifica se estão corretas e atualiza as estatísticas do simulado ENEM.
    Redireciona para a página do simulado ENEM.

    Parâmetros:
        - request: objeto HttpRequest contendo os dados da requisição.

    Retorno:
        - Se o método for POST e as respostas forem processadas com sucesso, redireciona para a página do simulado ENEM.
    """
    if request.method == 'POST':
        dia = request.POST.get('dia')
        ano = request.POST.get('ano')
        enem_d = f'{ano}' + f'{dia}'
        respostas = {}
        idioma = ''
        if dia == '1':
            idioma = request.POST.get('idioma')
            for i in range(1, 90):
                resposta = request.POST.get(f'resposta{i}')
                respostas[f'{i}'] = resposta
        elif dia == '2':
            for i in range(91, 180):
                resposta = request.POST.get(f'resposta{i}')
                respostas[f'{i}'] = resposta
        verifica_resposta(request, respostas, ano, dia, idioma)
        return redirect('enem', enem_d)


def verifica_resposta(request, resposta_usuario, ano, dia, idioma):
    """
    Função auxiliar para verificar as respostas do simulado ENEM.

    Recebe um objeto 'request', as respostas do usuário, o ano, o dia e o idioma do simulado ENEM.
    Verifica se as respostas estão corretas e atualiza as estatísticas do simulado ENEM.

    Parâmetros:
        - request: objeto HttpRequest contendo os dados da requisição.
        - resposta_usuario: dicionário contendo as respostas do usuário.
        - ano: ano do simulado ENEM.
        - dia: dia do simulado ENEM.
        - idioma: idioma do simulado ENEM.

    Retorno:
        - Não há retorno explícito.
    """
    resposta = EnemRespostas.objects.filter(ano=ano, dia=dia)
    user_atual = request.user.username
    usuario_atual = Usuario.objects.get(arroba=user_atual)
    idioma_c = 1
    if idioma == 'ingles':
        resposta = EnemRespostas.objects.filter(
            ano=ano, dia=1).exclude(espanhol=True, ingles=False)
        idioma_c = 1
    elif idioma == 'espanhol':
        resposta = EnemRespostas.objects.filter(
            ano=ano, dia=1).exclude(espanhol=False, ingles=True)
        idioma_c = 0

    correta_errada = False

    for checa in resposta:
        numero_q = checa.numero_questao
        resposta_u = resposta_usuario.get(str(numero_q))
        if resposta_u and checa.resposta == resposta_u:
            correta_errada = True

        else:
            correta_errada = False
        print(resposta_u)

        EstatisticasEnem_usuario.objects.create(
            usuario=usuario_atual,
            resposta_usuario=resposta_u or 'Vazio',
            numero_questao=numero_q,
            correto_errada=correta_errada,
            idioma_escolhido=idioma_c,
            questao=checa,
        )


def processa_dados_enem(request, enem_dia_ano):
    """
    View para processar os dados do simulado ENEM.

    Recebe um objeto 'request' e o 'enem_dia_ano' (identificador do simulado ENEM) a ser processado.
    Processa os dados do simulado ENEM e retorna a renderização da página de estatísticas do simulado ENEM.

    Parâmetros:
        - request: objeto HttpRequest contendo os dados da requisição.
        - enem_dia_ano: identificador do simulado ENEM a ser processado.

    Retorno:
        - Renderiza a página de estatísticas do simulado ENEM com os dados processados.
    """
    user_atual = request.user.username
    usuario_atual = Usuario.objects.get(arroba=user_atual)
    pagina_principal = usuario_atual.paginas.all().first()
    print(pagina_principal.id)
    conteudo_ = conteudo_geral2(request, enem_dia_ano)

    dia = conteudo_['dia']
    ano = conteudo_['ano']
    usuario = conteudo_['usuario2']

    conteudo = processar_dados_enem_para_grafico_dois(usuario, ano, dia)
    dados = {'dados_enem': conteudo,
             'pagina_principal': pagina_principal.id,
             'foto_perfil': usuario_atual.foto_perfil.url}

    return render(request, 'estatisticas_enem.html', dados)


def processar_dados_enem_para_grafico_dois(usuario, ano, dia):
    """
    Processa os dados do simulado ENEM para gerar o gráfico de desempenho por área e tentativa.

    Recebe um objeto 'usuario', o 'ano' e o 'dia' do simulado ENEM.
    Retorna uma lista de dados formatados para o gráfico de desempenho por área e tentativa.

    Parâmetros:
        - usuario: objeto do tipo Usuario representando o usuário atual.
        - ano: ano do simulado ENEM.
        - dia: dia do simulado ENEM.

    Retorno:
        - Uma lista de dicionários contendo os dados para o gráfico de desempenho por área e tentativa.
    """
    estatisticas = EstatisticasEnem_usuario.objects.filter(
        usuario=usuario,
        questao__ano=ano,
        questao__dia=dia,
    ).order_by('data_da_tentativa')

    # Estrutura para acumular os resultados por tentativa e área
    resultados_por_tentativa_area = defaultdict(
        lambda: defaultdict(lambda: {'acertos': 0, 'erros': 0}))

    if dia == 2:
        areas = {
            'Ciências da Natureza': (91, 135),
            'Matemática': (136, 180)
        }
    else:
        areas = {
            'Linguagens e Códigos': (1, 45),
            'Ciências Humanas': (46, 90)
        }
    for estatistica in estatisticas:
        tentativa = estatistica.data_da_tentativa.strftime('%Y-%m-%d %H:%M')
        numero_questao = estatistica.questao.numero_questao
        area = next((area for area, (inicio, fim) in areas.items()
                    if inicio <= numero_questao <= fim), None)

        if area:
            if estatistica.correto_errada:
                resultados_por_tentativa_area[tentativa][area]['acertos'] += 1
            else:
                resultados_por_tentativa_area[tentativa][area]['erros'] += 1

    # Convertendo os resultados acumulados para a lista de dados para o gráfico
    dados_grafico_final = []
    for tentativa, areas_resultados in resultados_por_tentativa_area.items():
        for area, resultados in areas_resultados.items():
            categoria = f'Tentativa {tentativa} - {area}'
            dados_grafico_final.append({
                'categoria': categoria,
                'acertos': resultados['acertos'],
                'erros': resultados['erros']
            })

    return dados_grafico_final


# ---- FIM BLOCO: enem


# ------- INICIO BLOCO: CONFIGURACAO
@login_required
def configurar(request):
    """
    View para configurar as informações do perfil do usuário.

    Recebe um objeto 'request' e processa as informações do formulário para atualizar o perfil do usuário.
    Retorna a renderização da página de configurações do perfil do usuário.

    Parâmetros:
        - request: objeto HttpRequest contendo os dados da requisição.

    Retorno:
        - Renderiza a página de configurações do perfil do usuário com as informações atualizadas.
    """
    user_atual = request.user
    usuario_atual = Usuario.objects.get(arroba=user_atual.username)
    if request.method == 'POST':
        nome_arroba = request.POST.get('nome_arroba')
        senha = request.POST.get('senha1')
        senha2 = request.POST.get('senha2')
        foto = request.FILES.get('foto_perfil')
        if nome_arroba != user_atual.username and Usuario.objects.filter(arroba=nome_arroba).exists():
            messages.error(request, 'Este nome de usuário já está em uso.')
            return render(request, 'configuracoes.html', conteudo_geral(request, usuario_atual.paginas.first().id))
        if senha and senha == senha2:
            user_atual.set_password(senha)
            user_atual.save()
            # Important to not log out the user
            update_session_auth_hash(request, user_atual)
            messages.success(request, 'Senha atualizada com sucesso.')

        if foto:
            usuario_atual.foto_perfil = foto
            usuario_atual.save()
            messages.success(request, 'Foto de perfil atualizada com sucesso.')

        if nome_arroba:

            user_atual.username = nome_arroba
            usuario_atual.arroba = nome_arroba
            user_atual.save()
            usuario_atual.save()
            messages.success(
                request, 'Nome de usuário atualizado com sucesso.')

    conteudos_ = conteudo_geral(request, usuario_atual.paginas.first().id)
    return render(request, 'configuracoes.html', conteudos_)


def edit_paginas_conf(request):
    """
    View para editar as páginas configuradas pelo usuário.

    Recebe um objeto 'request' e renderiza a página de edição das páginas configuradas pelo usuário.

    Parâmetros:
        - request: objeto HttpRequest contendo os dados da requisição.

    Retorno:
        - Renderiza a página de edição das páginas configuradas pelo usuário.
    """
    user_atual = request.user
    usuario_atual = Usuario.objects.get(arroba=user_atual.username)
    conteudos_ = conteudo_geral(request, usuario_atual.paginas.first().id)
    return render(request, 'edit_paginas.html', conteudos_)


def edit_titulo_pg(request):
    """
    View para editar o título de uma página configurada pelo usuário.

    Recebe um objeto 'request' e verifica se o método é POST.
    Extrai o ID da página e o novo título, e atualiza o título da página no banco de dados.
    Redireciona para a página de edição das páginas configuradas pelo usuário.

    Parâmetros:
        - request: objeto HttpRequest contendo os dados da requisição.

    Retorno:
        - Se o método for POST e o título for editado com sucesso, redireciona para a página de edição das páginas configuradas pelo usuário.
    """
    if request.method == 'POST':
        id_pagina = request.POST.get('id_pagina')
        titulo = request.POST.get('titulo_pagina')
        Pagina.objects.filter(id=id_pagina).update(titulo=titulo)

        return redirect('edit_paginas_conf')
    pass


def delete_pg(request):
    """
    View para excluir uma página configurada pelo usuário.

    Recebe um objeto 'request' e verifica se o método é POST.
    Extrai o ID da página a ser excluída e a exclui do banco de dados.
    Redireciona para a página de edição das páginas configuradas pelo usuário.

    Parâmetros:
        - request: objeto HttpRequest contendo os dados da requisição.

    Retorno:
        - Se o método for POST e a página for excluída com sucesso, redireciona para a página de edição das páginas configuradas pelo usuário.
    """
    if request.method == 'POST':
        user_atual = request.user
        usuario_atual = Usuario.objects.get(arroba=user_atual.username)
        id_pagina = request.POST.get('id_pagina')
        pagina = get_object_or_404(Pagina, id=id_pagina)
        if usuario_atual.paginas.count() == 1:
            messages.error(
                request, 'Você não pode excluir a única página que possui.')
            return redirect('edit_paginas_conf')
        pagina.delete()
        return redirect('edit_paginas_conf')
# ------- FIM BLOCO: CONFIGURACAO


# ---- INICIO BLOCO: ESTATISTICAS SIMULADO
@login_required
def estatisticas_simulado(request):
    """
    View para exibir as estatísticas do simulado do usuário.

    Recebe um objeto 'request' e retorna a renderização da página de estatísticas do simulado.

    Parâmetros:
        - request: objeto HttpRequest contendo os dados da requisição.

    Retorno:
        - Renderiza a página de estatísticas do simulado.
    """
    conteudo = estatisticas_conteudo(request)

    return render(request, 'estatisticas.html', conteudo)


def estatisticas_conteudo(request):
    """
    Função auxiliar para obter o conteúdo das estatísticas do simulado.

    Recebe um objeto 'request' e retorna um dicionário contendo os dados das estatísticas do simulado.

    Parâmetros:
        - request: objeto HttpRequest contendo os dados da requisição.

    Retorno:
        - Um dicionário contendo os dados das estatísticas do simulado.
    """
    user_atual = request.user.username
    usuario_atual = Usuario.objects.get(arroba=user_atual)
    pagina_principal = usuario_atual.paginas.all().first()
    dados_esta = processa_dados_estatisticas(request)

    return {'dados_estatisticas': dados_esta,
            'pagina_principal': pagina_principal,
            'foto_perfil': usuario_atual.foto_perfil.url
            }
# ---- FIM BLOCO: ESTATISTICAS SIMULADO


# ----------BLOCO: INICIO SOL


def sol(request):
    """
    View para obter e traduzir uma pergunta para o simulado.

    Recebe um objeto 'request' e verifica se o método é POST.
    Extrai a dificuldade, categoria e ID da página do formulário.
    Obtém e traduz uma pergunta usando a API fictícia e a IA generativa.
    Redireciona para a página do simulado.

    Parâmetros:
        - request: objeto HttpRequest contendo os dados da requisição.

    Retorno:
        - Se o método for POST, redireciona para a página do simulado.
    """
    if request.method == 'POST':
        id_pagina = request.POST.get('id_pagina')
        dificuldade = request.POST.get('dificuldade_questao')
        categoria = request.POST.get('categoria_questao')

        pergunta_respostas = obter_e_traduzir_perguntas(
            dificuldade, categoria, id_pagina)
        print(pergunta_respostas)
        return redirect('simulado', id_pagina)
# -------------------------- FIM AREA DOS SIMULADOS --------------------------------


# ---------------- funções API e IA -------------------------
def genai_configurar():
    """
    Configura a chave da API e inicializa o modelo generativo.

    Retorna o modelo generativo inicializado.

    Retorno:
        - Um objeto do modelo generativo inicializado.
    """
    genai.configure(api_key="AIzaSyC_-yuJYc59iZFcC91YpEdJvjMtbM4d2wE")
    model = genai.GenerativeModel('gemini-pro')
    return model

# Função para traduzir texto usando a API generativa fictícia


def obter_e_traduzir_perguntas(dificuldade, categoria, id_pagina):
    """
    Obtém e traduz uma pergunta usando a API  e a IA generativa.

    Recebe a dificuldade, categoria e ID da página.
    Retorna a pergunta traduzida.

    Parâmetros:
        - dificuldade: string representando a dificuldade da pergunta.
        - categoria: string representando a categoria da pergunta.
        - id_pagina: ID da página onde a pergunta será salva.

    Retorno:
        - Uma string contendo a pergunta traduzida.
    """
    url = f"https://opentdb.com/api.php?amount=1&category={categoria}&difficulty={dificuldade}&type=multiple"

    response = requests.get(url)
    data = response.json()
    model = genai_configurar()
    indice = ['a', 'b', 'c', 'd']
    perguntasList = []
    respostaList = []
    pergunta_resposta = ''
    if data['response_code'] == 0:
        for i, question in enumerate(data['results'], start=1):
            perguntasList.append(question['question'])

            respostaList.append(
                question['incorrect_answers'] + [question['correct_answer']])
            pergunta_resposta = perguntasList[0]
        # Aqui, assumimos que você quer a primeira lista de respostas
        for i, respostas in enumerate(respostaList[0]):
            # Adiciona cada resposta na string, com a letra correspondente (a-d)
            pergunta_resposta += f'\n{["a", "b", "c", "d"][i]}) {respostas}'
        pergunta_resposta += f'\nResposta correta: {respostaList[0][-1]}'

    texto_traduzido = traduzir_texto(model, pergunta_resposta)
    salvar_pergunta_resposta_na_pagina(id_pagina, texto_traduzido)
    return texto_traduzido


def traduzir_texto(model, texto):
    """
    Traduz um texto usando a IA generativa.

    Recebe o modelo generativo e o texto a ser traduzido.
    Retorna o texto traduzido.

    Parâmetros:
        - model: objeto do modelo generativo.
        - texto: texto a ser traduzido.

    Retorno:
        - Uma string contendo o texto traduzido.
    """
    prompt_traduzir = f'Traduza: {texto}'
    response = model.generate_content(prompt_traduzir)
    return response.text


def salvar_pergunta_resposta_na_pagina(id_pagina, texto_traduzido):
    """
    Salva a pergunta e suas respostas na página especificada.

    Recebe o ID da página e o texto da pergunta traduzida.
    Salva a pergunta e suas respostas na página especificada no banco de dados.

    Parâmetros:
        - id_pagina: ID da página onde a pergunta será salva.
        - texto_traduzido: pergunta traduzida a ser salva na página.
    """
    # Importando aqui caso precise atualizar algum campo no banco
    from django.db.models import F
    pagina = Pagina.objects.get(id=id_pagina)

    # Encontra o índice do início da primeira alternativa "a)"
    indice_inicio_alternativas = texto_traduzido.find("a)")
    pergunta = texto_traduzido[:indice_inicio_alternativas].strip()

    # Encontra a resposta correta no final do texto
    inicio_resposta_correta = texto_traduzido.find("Resposta correta:")
    resposta_correta_descricao = texto_traduzido[inicio_resposta_correta:].split(":")[
        1].strip()

    # Extrai as alternativas do texto
    alternativas_texto = texto_traduzido[indice_inicio_alternativas:inicio_resposta_correta].strip(
    ).split('\n')
    # Remove 'a) ', 'b) ', etc.
    alternativas = [alt[3:].strip() for alt in alternativas_texto]

    # Embaralha as alternativas e mantém o índice da resposta correta
    indices_originais = list(range(len(alternativas)))
    pares_alternativa_indice = list(zip(alternativas, indices_originais))
    random.shuffle(pares_alternativa_indice)
    alternativas, indices_originais = zip(*pares_alternativa_indice)

    # Atualiza a lista de alternativas com a ordem embaralhada
    alternativas = list(alternativas)

    # Encontra a nova posição da resposta correta após o embaralhamento
    nova_posicao_resposta_correta = alternativas.index(
        resposta_correta_descricao)
    letra_resposta_correta = 'ABCD'[nova_posicao_resposta_correta]

    print(pergunta, alternativas, letra_resposta_correta, pagina)

    simulado = Simulados(
        pergunta=pergunta,
        alternativa_a=alternativas[0],
        alternativa_b=alternativas[1],
        alternativa_c=alternativas[2],
        alternativa_d=alternativas[3],
        correta=letra_resposta_correta,
        pagina=pagina
    )
    simulado.save()
    # Cria e salva o novo objeto Simulado

# ----------BLOCO: FINAL SOL


# ------- BLOCO: INICIO ADD ALUNO
@login_required
def add_alunos(request):
    """
    View para adicionar páginas compartilhadas com alunos.

    Recebe um objeto 'request' e verifica se o método é POST.
    Extrai o nome do usuário do aluno e as IDs das páginas compartilhadas do formulário.
    Tenta encontrar o usuário do aluno e adicionar as páginas compartilhadas a ele.
    Retorna mensagens de sucesso ou erro dependendo do resultado da operação.

    Parâmetros:
        - request: objeto HttpRequest contendo os dados da requisição.

    Retorno:
        - Se o método for POST, retorna para a página 'add_alunos'.
    """
    conteudo_ = conteudo_geral(request, 1)

    if request.method == 'POST':
        nome_usuario_aluno = request.POST.get('arroba_aluno')
        paginas_ids = request.POST.getlist('paginas_compartilhadas')

        try:
            usuario_aluno = Usuario.objects.get(
                arroba=nome_usuario_aluno, tipo_user='aluno')
            for pagina_id in paginas_ids:
                pagina = Pagina.objects.get(id=pagina_id)

                usuario_aluno.paginas_compartilhadas.add(pagina)
            messages.success(request, 'Páginas compartilhadas com sucesso.')
            return render(request, 'add_alunos.html', conteudo_)
        except Usuario.DoesNotExist:
            messages.error(request, 'O aluno especificado não existe.')
            return render(request, 'add_alunos.html', conteudo_)

    else:

        return render(request, 'add_alunos.html', conteudo_)
# ------- BLOCO: FIM ADD ALUNO


# --------- BLOCO: INICIO PAGINAS COMPARTILHADAS


@login_required
def paginas_compartilhadas_cards(request, pagina_compartilhada_id):
    """
    View para exibir páginas compartilhadas com cards.

    Recebe um objeto 'request' e o ID da página compartilhada.
    Retorna a renderização da página 'paginas_compartilhadas_cards.html' com o conteúdo.

    Parâmetros:
        - request: objeto HttpRequest contendo os dados da requisição.
        - pagina_compartilhada_id: ID da página compartilhada.

    Retorno:
        - Renderização da página 'paginas_compartilhadas_cards.html' com o conteúdo.
    """
    conteudo_ = conteudo_geral(request, pagina_compartilhada_id)
    return render(request, 'paginas_compartilhadas_cards.html', conteudo_)


def paginas_compartilhadas_simulados(request, pagina_compartilhada_id):
    """
    View para exibir páginas compartilhadas com simulados.

    Recebe um objeto 'request' e o ID da página compartilhada.
    Retorna a renderização da página 'paginas_compartilhadas_simulados.html' com o conteúdo.

    Parâmetros:
        - request: objeto HttpRequest contendo os dados da requisição.
        - pagina_compartilhada_id: ID da página compartilhada.

    Retorno:
        - Renderização da página 'paginas_compartilhadas_simulados.html' com o conteúdo.
    """
    conteudo_ = conteudo_geral(request, pagina_compartilhada_id)
    return render(request, 'paginas_compartilhadas_simulados.html', conteudo_)


# --------- BLOCO: FIM PAGINAS COMPARTILHADAS

# ------------------- BLOCO: INICIO CHECA RESPOSTA PARA PROF
@login_required
def checa_resposta_simulado_prof(request):
    """
    View para verificar as respostas dos alunos para um simulado compartilhado com um professor.

    Recebe um objeto 'request' e verifica se o método é POST.
    Extrai informações como usuário atual, página, professor e respostas do formulário.
    Registra estatísticas de respostas corretas e erradas dos alunos para o simulado.
    Retorna mensagens de sucesso ou erro dependendo do resultado da operação.

    Parâmetros:
        - request: objeto HttpRequest contendo os dados da requisição.

    Retorno:
        - Redireciona para a página 'paginas_compartilhadas_simulados' após o processamento.
    """
    if request.method == 'POST':
        usuario = request.user.username
        usuario_atual = Usuario.objects.get(arroba=usuario)

        id_pagina = request.POST.get('id_pagina')
        pagina = get_object_or_404(Pagina, id=id_pagina)
        id_prof = request.POST.get('id_prof')
        prof = get_object_or_404(Usuario, id=id_prof)

        estatisticas = EstatisticasSimulado_compartilhada.objects.create(
            aluno=usuario_atual, prof=prof, pagina=pagina)

        questoes = Simulados.objects.filter(pagina_id=id_pagina)
        acertos = 0
        erros = 0

        for questao in questoes:
            alternativa_correta_marcada = request.POST.get(
                f'alternativas_{questao.id}')

            if alternativa_correta_marcada and alternativa_correta_marcada == questao.correta:
                estatisticas.questoes_corretas.add(questao)
                acertos += 1
            else:
                estatisticas.questoes_erradas.add(questao)
                erros += 1

        if acertos == len(questoes):
            messages.success(
                request, f'Parabéns! Você acertou todas as {acertos} questões.')
        else:
            messages.error(
                request, f'Você acertou {acertos} questões e errou {erros}.')

        return redirect('paginas_compartilhadas_simulados', id_pagina)


def estatisticas_prof(request):
    """
    View para exibir estatísticas de desempenho dos alunos em simulados compartilhados com o professor.

    Recebe um objeto 'request' e chama a função 'processa_dados_estatisticas_prof' para processar os dados.
    Retorna a renderização da página 'estatisticas_prof.html' com os dados processados.

    Parâmetros:
        - request: objeto HttpRequest contendo os dados da requisição.

    Retorno:
        - Renderização da página 'estatisticas_prof.html' com os dados das estatísticas.
    """
    conteudo = processa_dados_estatisticas_prof(request)

    user_atual = request.user.username
    usuario_atual = Usuario.objects.get(arroba=user_atual)
    pagina_principal = usuario_atual.paginas.all().first()
    dados = {'dados_estatisticas': conteudo,
             'pagina_principal': pagina_principal.id,
             'foto_perfil': usuario_atual.foto_perfil.url}
    return render(request, 'estatisticas_prof.html', dados)


def processa_dados_estatisticas_prof(request):
    """
    Função para processar os dados de estatísticas dos alunos em simulados compartilhados com o professor.

    Recebe um objeto 'request' para identificar o professor atual.
    Filtra as estatísticas das páginas compartilhadas pelo professor e as agrupa por página e aluno.
    Retorna os dados processados em um formato adequado para exibição no template.

    Parâmetros:
        - request: objeto HttpRequest contendo os dados da requisição.

    Retorno:
        - Lista de dicionários contendo os dados das estatísticas por página e aluno.
    """
    professor_atual = Usuario.objects.get(arroba=request.user.username)

    estatisticas = EstatisticasSimulado_compartilhada.objects.filter(
        prof=professor_atual).order_by('pagina', 'ultima_tentativa')

    dados_por_pagina = {}

    for estatistica in estatisticas:
        pagina_titulo = estatistica.pagina.titulo
        aluno_nome = estatistica.aluno.arroba

        if pagina_titulo not in dados_por_pagina:
            dados_por_pagina[pagina_titulo] = {}

        if aluno_nome not in dados_por_pagina[pagina_titulo]:
            dados_por_pagina[pagina_titulo][aluno_nome] = {
                'tentativas': 0,
                'acertos': 0,
                'erros': 0
            }

        # Agrega as estatísticas
        dados_aluno = dados_por_pagina[pagina_titulo][aluno_nome]
        dados_aluno['tentativas'] += 1
        dados_aluno['acertos'] += estatistica.questoes_corretas.count()
        dados_aluno['erros'] += estatistica.questoes_erradas.count()

    dados_grafico = []
    for pagina, alunos in dados_por_pagina.items():
        for aluno, estatisticas in alunos.items():
            dados_grafico.append({
                'Aluno / Pagina': pagina + ' \n ' + aluno,
                **estatisticas
            })
    print(dados_grafico)
    return dados_grafico


# ------------------- BLOCO: FIM CHECA RESPOSTA PARA PROF


# ------INICIO BLOCO: PROCESSA DADOS DAS ESTATICICAS SIMULADO

def processa_dados_estatisticas(request):
    """
    Função para processar os dados estatísticos dos simulados do usuário atual.

    Recebe um objeto 'request' contendo informações sobre o usuário atual.
    Retorna os dados estatísticos dos simulados do usuário em um formato adequado para exibição no gráfico.

    Parâmetros:
        - request: objeto HttpRequest contendo os dados da requisição.

    Retorno:
        - Lista de dicionários contendo os dados estatísticos dos simulados do usuário.
    """

    usuario_atual = Usuario.objects.get(arroba=request.user.username)
    estatisticas = EstatisticasSimulado.objects.filter(
        usuario=usuario_atual).order_by('pagina', 'data')

    estatisticas_por_tentativa = []

    for estatistica in estatisticas:
        acertos = estatistica.questoes_corretas.count()
        erros = estatistica.questoes_erradas.count()

        # Encontra a página na lista de estatísticas por tentativa, se já existir
        pagina_estatistica = next(
            (item for item in estatisticas_por_tentativa if item['pagina'] == estatistica.pagina.titulo), None)

        # Se a página ainda não foi adicionada, cria uma nova entrada
        if not pagina_estatistica:
            pagina_estatistica = {
                'pagina': estatistica.pagina.titulo,
                'tentativas': []
            }
            estatisticas_por_tentativa.append(pagina_estatistica)

        # Adiciona os detalhes da tentativa atual à página correspondente
        pagina_estatistica['tentativas'].append(
            {'acertos': acertos, 'erros': erros})

    # Transformar as estatísticas em um formato adequado para o gráfico
    dados_grafico = []
    for estatistica in estatisticas_por_tentativa:
        for i, tentativa in enumerate(estatistica['tentativas'], 1):
            dados_grafico.append({
                'pagina': f"{estatistica['pagina']}",
                'acertos': tentativa['acertos'],
                'erros': tentativa['erros'],
                'tentativas': i
            })
    return dados_grafico


def conteudo_geral(request, id_pagina):
    """
    Função para gerar o conteúdo geral da página, incluindo dados sobre simulados, cards, e outras informações.

    Recebe um objeto 'request' e o 'id_pagina' da página atual.
    Retorna um dicionário contendo o conteúdo geral da página, como cards, simulados, informações do usuário, etc.

    Parâmetros:
        - request: objeto HttpRequest contendo os dados da requisição.
        - id_pagina: ID da página atual.

    Retorno:
        - Dicionário contendo o conteúdo geral da página.
    """
    user_atual = request.user.username
    usuario_atual = Usuario.objects.get(arroba=user_atual)

    todas_as_paginas = usuario_atual.paginas.all()
    pagina_principal = usuario_atual.paginas.all().first()
    paginas_flashcards_compartilhadas = usuario_atual.paginas_compartilhadas.filter(
        cards__isnull=False).distinct()
    paginas_simulados_compartilhadas = usuario_atual.paginas_compartilhadas.filter(
        simulado__isnull=False).distinct()

    # simulado --------
    paginas_com_simulados = Pagina.objects.filter(
        simulado__isnull=False).distinct()

    pagina_ids = Simulados.objects.filter(
        pagina__in=todas_as_paginas).values_list('pagina', flat=True).distinct()

    paginas_simulados2 = Pagina.objects.filter(id__in=pagina_ids)

    paginas_simulados = Simulados.objects.filter(
        pagina__in=todas_as_paginas).distinct()
    primeira_pagina_simulado = paginas_simulados.first()
    # fim simulado ---------

    # ENEM AREA
    ano = str(id_pagina)[:4]
    dia = str(id_pagina)[-1]
    ano = int(ano)
    dia = int(dia)
    enem_ano_dia = f'{ano}' + f'{dia}'
    numeros_1_a_90 = list(range(1, 91))
    numeros_91_a_181 = list(range(91, 182))
    # ENEM AREA FIM

    # ------- area de card -------
    cards = Cards.objects.filter(pagina_id=id_pagina)
    cards_compartilhados = Cards.objects.filter(
        pagina_id=id_pagina)
    ids_paginas_simulados = paginas_simulados.values_list('pagina', flat=True)

    paginas_nao_simulados = todas_as_paginas.exclude(
        id__in=ids_paginas_simulados)
    # -------- fim area card ------------

    # --------------- prof
    dono = Usuario.objects.filter(paginas__id=id_pagina).first()
    if dono:
        id_dono = dono.id
    print('oi', primeira_pagina_simulado)
    # --------------- prof
    # ------- fim area de card -------
    conteudo = {'pagina_principal': pagina_principal,
                'pagina_atual': id_pagina,
                'cards': cards,
                'cards_compartilhados': cards_compartilhados,
                'paginas_compartilhadas_cards': paginas_flashcards_compartilhadas,
                'paginas_compartilhadas_simulados': paginas_simulados_compartilhadas,
                'id_prof': id_dono,
                'id_aluno': usuario_atual.id,
                'tipo_user': usuario_atual.tipo_user,
                'foto_perfil': usuario_atual.foto_perfil.url,
                'paginas_cards': paginas_nao_simulados,
                'paginas_simulados': paginas_simulados2,
                'simulados_questao': paginas_com_simulados,
                'primeira_pagina_simulado': primeira_pagina_simulado.id,
                'dia': dia,
                'ano': ano,
                'usuario': usuario_atual.arroba,
                'numero': numeros_1_a_90,
                'numero2': numeros_91_a_181,
                'enem_ano_dia': enem_ano_dia
                }
    dia = conteudo['dia']
    return conteudo


def conteudo_geral_enem(request, id_pagina):
    """
    Função para gerar o conteúdo geral da página relacionada ao ENEM, incluindo informações sobre cards, simulados, e outras informações.

    Recebe um objeto 'request' e o 'id_pagina' da página atual.
    Retorna um dicionário contendo o conteúdo geral da página relacionada ao ENEM.

    Parâmetros:
        - request: objeto HttpRequest contendo os dados da requisição.
        - id_pagina: ID da página atual.

    Retorno:
        - Dicionário contendo o conteúdo geral da página relacionada ao ENEM.
    """
    user_atual = request.user.username
    usuario_atual = Usuario.objects.get(arroba=user_atual)

    todas_as_paginas = usuario_atual.paginas.all()
    pagina_principal = usuario_atual.paginas.all().first()
    paginas_flashcards_compartilhadas = usuario_atual.paginas_compartilhadas.filter(
        cards__isnull=False).distinct()
    paginas_simulados_compartilhadas = usuario_atual.paginas_compartilhadas.filter(
        simulado__isnull=False).distinct()

    # simulado --------
    paginas_com_simulados = Pagina.objects.filter(
        simulado__isnull=False).distinct()

    pagina_ids = Simulados.objects.filter(
        pagina__in=todas_as_paginas).values_list('pagina', flat=True).distinct()

    paginas_simulados2 = Pagina.objects.filter(id__in=pagina_ids)

    paginas_simulados = Simulados.objects.filter(
        pagina__in=todas_as_paginas).distinct()
    primeira_pagina_simulado = paginas_simulados.first()
    # fim simulado ---------

    # ENEM AREA
    ano = str(id_pagina)[:4]
    dia = str(id_pagina)[-1]
    ano = int(ano)
    dia = int(dia)
    enem_ano_dia = f'{ano}' + f'{dia}'
    numeros_1_a_90 = list(range(1, 90))
    numeros_91_a_181 = list(range(91, 181))
    # ENEM AREA FIM

    # ------- area de card -------
    cards = Cards.objects.filter(pagina_id=id_pagina)
    cards_compartilhados = Cards.objects.filter(
        pagina_id=id_pagina)
    ids_paginas_simulados = paginas_simulados.values_list('pagina', flat=True)

    paginas_nao_simulados = todas_as_paginas.exclude(
        id__in=ids_paginas_simulados)
    # -------- fim area card ------------

    # ------- fim area de card -------
    conteudo = {'pagina_principal': pagina_principal,
                'pagina_atual': id_pagina,
                'cards': cards,
                'cards_compartilhados': cards_compartilhados,
                'paginas_compartilhadas_cards': paginas_flashcards_compartilhadas,
                'paginas_compartilhadas_simulados': paginas_simulados_compartilhadas,

                'id_aluno': usuario_atual.id,
                'tipo_user': usuario_atual.tipo_user,
                'foto_perfil': usuario_atual.foto_perfil.url,
                'paginas_cards': paginas_nao_simulados,
                'paginas_simulados': paginas_simulados2,
                'simulados_questao': paginas_com_simulados,
                'primeira_pagina_simulado': primeira_pagina_simulado.id,
                'dia': dia,
                'ano': ano,
                'usuario': usuario_atual.arroba,
                'numero': numeros_1_a_90,
                'numero2': numeros_91_a_181,
                'enem_ano_dia': enem_ano_dia
                }
    dia = conteudo['dia']
    return conteudo


def conteudo_geral2(request, id_pagina):
    """
    Função para gerar o conteúdo geral da página, incluindo informações sobre simulados do ENEM.

    Recebe um objeto 'request' e o 'id_pagina' da página atual.
    Retorna um dicionário contendo o conteúdo geral da página relacionada aos simulados do ENEM.

    Parâmetros:
        - request: objeto HttpRequest contendo os dados da requisição.
        - id_pagina: ID da página atual.

    Retorno:
        - Dicionário contendo o conteúdo geral da página relacionada aos simulados do ENEM.
    """
    user_atual = request.user.username
    usuario_atual = Usuario.objects.get(arroba=user_atual)

    todas_as_paginas = usuario_atual.paginas.all()

    paginas_simulados = Simulados.objects.filter(
        pagina__in=todas_as_paginas).distinct()

    # fim simulado ---------

    # ENEM AREA
    ano = str(id_pagina)[:4]
    dia = str(id_pagina)[-1]
    ano = int(ano)
    dia = int(dia)
    enem_ano_dia = f'{ano}' + f'{dia}'
    numeros_1_a_90 = list(range(1, 91))
    numeros_91_a_181 = list(range(91, 182))

    conteudo = {
        'dia': dia,
        'ano': ano,
        'usuario2': usuario_atual,
        'numero': numeros_1_a_90,
        'numero2': numeros_91_a_181,
        'enem_ano_dia': enem_ano_dia
    }
    dia = conteudo['dia']
    return conteudo
# ---- FIM BLOCO: retorna conteudos
