from django.shortcuts import render
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from django.http import HttpResponse, HttpResponseRedirect
from django.views.decorators.csrf import csrf_exempt
from django.urls import reverse
from django.contrib.auth.models import User
from django.contrib.auth import authenticate
from django.contrib.auth import login as login_django
from django.db import IntegrityError
from .models import Usuario, Pagina, Cards, Simulados, EstatisticasSimulado, EnemRespostas, EstatisticasEnem_usuario,EstatisticasSimulado_compartilhada
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
            Simulados.objects.create(pergunta='No botao a esquerda vc cria pergunta com alternativas', alternativa_a='No botão sol existe uma IA que traduz e uma api que gera algumas questoes.', alternativa_b='Preencha todas as questoes e veja as estatisticas quando quiser', alternativa_c='As estatisticas fica na parte inferior da aba perfil, ao lado da configuração', alternativa_d='Isso é tudo, bons estudos', pagina=primeira_pagina_simulado)
            usuario.paginas.add(pagina)
            usuario.paginas.add(primeira_pagina_simulado)
            return redirect('login')
    else:
        return render(request, 'cadastro.html')


def login_user(request):
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
    logout(request)
    return redirect('login')
# ---- FIM BLOCO login e cadastro


# ---- INICO BLOCO: paginacao
@login_required(login_url="/usuario/login/")
def paginas(request, pagina_id):
    usuario_nome = request.user.username
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

    conteudos_ = conteudo_geral(request, simulado_id)
    return render(request, 'simulado.html',  conteudos_)


@login_required
@require_POST
def add_pagina_simulado(request):
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
    if request.method == 'POST':

        pergunta_simulado = request.POST.get('pergunta_simulado')
        alternativa_a = request.POST.get('alternativa_a_simulado')
        alternativa_b = request.POST.get('alternativa_b_simulado')
        alternativa_c = request.POST.get('alternativa_c_simulado')
        alternativa_d = request.POST.get('alternativa_d_simulado')
        alternativa_correta = request.POST.get('alternativa_correta')
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
    if request.method == 'POST':
        id_questao = request.POST.get('id_questao')
        id_pagina = request.POST.get('id_pagina')
        simulado = get_object_or_404(Simulados, id=id_questao)
        simulado.delete()
        return redirect('simulado', id_pagina)


@login_required
def checa_resposta_simulado(request):
    if request.method == 'POST':
        usuario = request.user.username
        usuario_ = Usuario.objects.get(arroba=usuario)
        id_pagina = request.POST.get('id_pagina')

        pagina = get_object_or_404(Pagina, id=id_pagina)

        estatisticas = EstatisticasSimulado.objects.create(
            usuario=usuario_, pagina=pagina)
        
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
                request, f'Parabéns! Você acertou todas as {acertos + erros} questões. De {acertos + erros} questões')
        else:
            messages.error(
                request, f'Você acertou {acertos} questões e errou {erros}. De {acertos + erros} questões')

        # jogar para uma outra pagina de sucesso.
        return redirect('simulado', id_pagina)

# ---- FIM BLOCO: SIMULADO


# ---- INICO BLOCO: enem
def enem(request, enem_d):

    conteudo = conteudo_geral_enem(request, enem_d)

    return render(request, 'enem.html', conteudo)


def resposta_enem(request):
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
    user_atual = request.user.username
    usuario_atual = Usuario.objects.get(arroba=user_atual)
    pagina_principal = usuario_atual.paginas.all().first()
    conteudo_ = conteudo_geral2(request, enem_dia_ano)

    dia = conteudo_['dia']
    ano = conteudo_['ano']
    usuario = conteudo_['usuario2']

    conteudo = processar_dados_enem_para_grafico_dois(usuario, ano, dia)
    processar_dados_enem_para_grafico(usuario, ano, dia)
    dados = {'dados_enem': conteudo,
     'pagina_princial':pagina_principal}
    
    return render(request, 'estatisticas_enem.html', dados)


def processar_dados_enem_para_grafico_dois(usuario, ano, dia):
    estatisticas = EstatisticasEnem_usuario.objects.filter(
        usuario=usuario,
        questao__ano=ano,
        questao__dia=dia,
    ).order_by('data_da_tentativa')

    # Estrutura para acumular os resultados por tentativa e área
    resultados_por_tentativa_area = defaultdict(lambda: defaultdict(lambda: {'acertos': 0, 'erros': 0}))

    if dia == '2':
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
        area = next((area for area, (inicio, fim) in areas.items() if inicio <= numero_questao <= fim), None)

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

    print(dados_grafico_final)
    return dados_grafico_final


def processar_dados_enem_para_grafico(usuario, ano, dia):
    estatisticas = EstatisticasEnem_usuario.objects.filter(
        usuario=usuario,
        questao__ano=ano,
        questao__dia=dia,
    )
    print(dia, ano)

    # Inicialização dos contadores de acertos e erros por área
    acertos_linguagens = estatisticas.filter(correto_errada=True, questao__numero_questao__range=(1, 45)).count()
    erros_linguagens = estatisticas.filter(correto_errada=False, questao__numero_questao__range=(1, 45)).count()

    acertos_ciencias_humanas = estatisticas.filter(correto_errada=True, questao__numero_questao__range=(46, 90)).count()
    erros_ciencias_humanas = estatisticas.filter(correto_errada=False, questao__numero_questao__range=(46, 90)).count()

    if dia == 2:  # Apenas para o segundo dia
        acertos_ciencias_natureza = estatisticas.filter(correto_errada=True, questao__numero_questao__range=(91, 135)).count()
        erros_ciencias_natureza = estatisticas.filter(correto_errada=False, questao__numero_questao__range=(91, 135)).count()

        acertos_matematica = estatisticas.filter(correto_errada=True, questao__numero_questao__range=(136, 180)).count()
        erros_matematica = estatisticas.filter(correto_errada=False, questao__numero_questao__range=(136, 180)).count()
        print(erros_matematica, erros_ciencias_natureza)

    # Organizando os dados para o gráfico
    dados_grafico = {
        'Linguagens e Códigos': {'Acertos': acertos_linguagens, 'Erros': erros_linguagens},
        'Ciências Humanas': {'Acertos': acertos_ciencias_humanas, 'Erros': erros_ciencias_humanas},
    }

    if dia == 2:  # Adicionando as áreas do segundo dia se aplicável
        dados_grafico.update({
            'Ciências da Natureza': {'Acertos': acertos_ciencias_natureza, 'Erros': erros_ciencias_natureza},
            'Matemática': {'Acertos': acertos_matematica, 'Erros': erros_matematica},
        })

    
    print(dados_grafico)
# ---- FIM BLOCO: enem


# ------- INICIO BLOCO: CONFIGURACAO
@login_required
def configurar(request):
    user_atual = request.user
    usuario_atual = Usuario.objects.get(arroba=user_atual.username)
    if request.method == 'POST':
        nome_arroba = request.POST.get('nome_arroba')
        senha = request.POST.get('senha1')
        senha2 = request.POST.get('senha2')
        foto = request.FILES.get('foto_perfil')

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
    user_atual = request.user
    usuario_atual = Usuario.objects.get(arroba=user_atual.username)
    conteudos_ = conteudo_geral(request, usuario_atual.paginas.first().id)
    return render(request, 'edit_paginas.html', conteudos_)


def edit_titulo_pg(request):
    if request.method == 'POST':
        id_pagina = request.POST.get('id_pagina')
        titulo = request.POST.get('titulo_pagina')
        Pagina.objects.filter(id=id_pagina).update(titulo=titulo)

        return redirect('edit_paginas_conf')
    pass


def delete_pg(request):
    if request.method == 'POST':
        id_pagina = request.POST.get('id_pagina')
        pagina = get_object_or_404(Pagina, id=id_pagina)
        pagina.delete()
        return redirect('edit_paginas_conf')
# ------- FIM BLOCO: CONFIGURACAO



# ---- INICIO BLOCO: ESTATISTICAS SIMULADO
@login_required
def estatisticas_simulado(request):
    conteudo = estatisticas_conteudo(request)

    return render(request, 'estatisticas.html', conteudo)


def estatisticas_conteudo(request):
    dados_esta = processa_dados_estatisticas(request)

    return {'dados_estatisticas': dados_esta}
# ---- FIM BLOCO: ESTATISTICAS SIMULADO




# ----------BLOCO: INICIO SOL


def sol(request):
    if request.method == 'POST':
        id_pagina = request.POST.get('id_pagina')
        dificuldade = request.POST.get('dificuldade_questao')
        categoria = request.POST.get('categoria_questao')

        pergunta_respostas = obter_e_traduzir_perguntas(dificuldade, categoria, id_pagina)
        print(pergunta_respostas)
        return redirect('simulado', id_pagina)
# -------------------------- FIM AREA DOS SIMULADOS --------------------------------


# ---------------- funções API e IA -------------------------
def genai_configurar():
    genai.configure(api_key="AIzaSyC_-yuJYc59iZFcC91YpEdJvjMtbM4d2wE")
    model = genai.GenerativeModel('gemini-pro')
    return model

# Função para traduzir texto usando a API generativa fictícia





def obter_e_traduzir_perguntas(dificuldade, categoria, id_pagina):
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
    prompt_traduzir = f'Traduza: {texto}'
    response = model.generate_content(prompt_traduzir)
    return response.text


def salvar_pergunta_resposta_na_pagina(id_pagina, texto_traduzido):
    from django.db.models import F  # Importando aqui caso precise atualizar algum campo no banco
    pagina = Pagina.objects.get(id=id_pagina)
    
    # Encontra o índice do início da primeira alternativa "a)"
    indice_inicio_alternativas = texto_traduzido.find("a)")
    pergunta = texto_traduzido[:indice_inicio_alternativas].strip()
    
    # Encontra a resposta correta no final do texto
    inicio_resposta_correta = texto_traduzido.find("Resposta correta:")
    resposta_correta_descricao = texto_traduzido[inicio_resposta_correta:].split(":")[1].strip()
    
    # Extrai as alternativas do texto
    alternativas_texto = texto_traduzido[indice_inicio_alternativas:inicio_resposta_correta].strip().split('\n')
    alternativas = [alt[3:].strip() for alt in alternativas_texto]  # Remove 'a) ', 'b) ', etc.
    
    # Embaralha as alternativas e mantém o índice da resposta correta
    indices_originais = list(range(len(alternativas)))
    pares_alternativa_indice = list(zip(alternativas, indices_originais))
    random.shuffle(pares_alternativa_indice)
    alternativas, indices_originais = zip(*pares_alternativa_indice)
    
    # Atualiza a lista de alternativas com a ordem embaralhada
    alternativas = list(alternativas)
    
    # Encontra a nova posição da resposta correta após o embaralhamento
    nova_posicao_resposta_correta = alternativas.index(resposta_correta_descricao)
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
    conteudo_ = conteudo_geral(request, 1)

    if request.method == 'POST':
        nome_usuario_aluno = request.POST.get('arroba_aluno')
        paginas_ids = request.POST.getlist('paginas_compartilhadas')
        usuario_aluno = Usuario.objects.get(
            arroba=nome_usuario_aluno, tipo_user='aluno')
        try:
            usuario_aluno = Usuario.objects.get(
                arroba=nome_usuario_aluno, tipo_user='aluno')
            for pagina_id in paginas_ids:
                pagina = Pagina.objects.get(id=pagina_id)

                usuario_aluno.paginas_compartilhadas.add(pagina)
            messages.success(request, 'Páginas compartilhadas com sucesso.')
            return render(request, 'add_alunos.html', conteudo_)
        except ObjectDoesNotExist:
            messages.error(request, 'O aluno especificado não existe.')
            return HttpResponseRedirect(request.META.get('HTTP_REFERER', '/'))
    else:

        return render(request, 'add_alunos.html', conteudo_)
# ------- BLOCO: FIM ADD ALUNO




# --------- BLOCO: INICIO PAGINAS COMPARTILHADAS
    

@login_required
def paginas_compartilhadas_cards(request, pagina_compartilhada_id):
    conteudo_ = conteudo_geral(request, pagina_compartilhada_id)
    return render(request, 'paginas_compartilhadas_cards.html', conteudo_)

def paginas_compartilhadas_simulados(request, pagina_compartilhada_id):
    conteudo_ = conteudo_geral(request,pagina_compartilhada_id)
    return render(request, 'paginas_compartilhadas_simulados.html', conteudo_)


# --------- BLOCO: FIM PAGINAS COMPARTILHADAS

# ------------------- BLOCO: INICIO CHECA RESPOSTA PARA PROF
@login_required
def checa_resposta_simulado_prof(request):
    if request.method == 'POST':
        usuario = request.user.username
        usuario_atual = Usuario.objects.get(arroba= usuario)

        id_pagina = request.POST.get('id_pagina')
        pagina = get_object_or_404(Pagina, id=id_pagina)
        id_prof = request.POST.get('id_prof')
        prof = get_object_or_404(Usuario, id=id_prof)
        
        estatisticas = EstatisticasSimulado_compartilhada.objects.create(aluno=usuario_atual, prof=prof, pagina=pagina)
        
        questoes = Simulados.objects.filter(pagina_id=id_pagina)
        acertos = 0
        erros = 0
        
        for questao in questoes:
            alternativa_correta_marcada = request.POST.get(f'alternativa_{questao.id}')
            if alternativa_correta_marcada and alternativa_correta_marcada == questao.correta:
                estatisticas.questoes_corretas.add(questao)
                acertos += 1
            else:
                estatisticas.questoes_erradas.add(questao)
                erros += 1
        
        if acertos == len(questoes):
            messages.success(request, f'Parabéns! Você acertou todas as {acertos} questões.')
        else:
            messages.error(request, f'Você acertou {acertos} questões e errou {erros}.')
        

        return redirect('paginas_compartilhadas_simulados', id_pagina)

def estatisticas_prof(request):
    conteudo = processa_dados_estatisticas_prof(request)
    
    user_atual = request.user.username
    usuario_atual = Usuario.objects.get(arroba=user_atual)
    pagina_principal = usuario_atual.paginas.all().first()
    dados = {'dados_estatisticas': conteudo,
     'pagina_princial':pagina_principal}
    return render(request, 'estatisticas_prof.html', dados ) 




def processa_dados_estatisticas_prof(request):
    # Assume-se que o usuário atual é o professor
    professor_atual = Usuario.objects.get(arroba=request.user.username)

    # Filtrar estatísticas das páginas compartilhadas pelo professor
    estatisticas = EstatisticasSimulado_compartilhada.objects.filter(
        prof=professor_atual).order_by('pagina', 'ultima_tentativa')

    dados_por_pagina = {}

    for estatistica in estatisticas:
        pagina_titulo = estatistica.pagina.titulo
        aluno_nome = estatistica.aluno.arroba

        # Inicializa a estrutura de dados para a página, se necessário
        if pagina_titulo not in dados_por_pagina:
            dados_por_pagina[pagina_titulo] = {}

        # Inicializa a estrutura de dados para o aluno, se necessário
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

    # Transformar os dados agregados em uma lista para facilitar a manipulação no template
    dados_grafico = []
    for pagina, alunos in dados_por_pagina.items():
        for aluno, estatisticas in alunos.items():
            dados_grafico.append({
                'pagina': pagina,
                'aluno': aluno,
                **estatisticas  # Desempacota as estatísticas do aluno
            })
    
    return dados_grafico



# ------------------- BLOCO: FIM CHECA RESPOSTA PARA PROF




# ------INICIO BLOCO: PROCESSA DADOS DAS ESTATICICAS SIMULADO

def processa_dados_estatisticas(request):
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
                'acertos': tentativa['erros'],
                'erros': tentativa['acertos'],
                'tentativas': i
            })
    return dados_grafico


def conteudo_geral(request, id_pagina):
    user_atual = request.user.username
    usuario_atual = Usuario.objects.get(arroba=user_atual)

    todas_as_paginas = usuario_atual.paginas.all()
    pagina_principal = usuario_atual.paginas.all().first()
    paginas_flashcards_compartilhadas = usuario_atual.paginas_compartilhadas.filter(cards__isnull=False).distinct()
    paginas_simulados_compartilhadas = usuario_atual.paginas_compartilhadas.filter(simulado__isnull=False).distinct()

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

    #--------------- prof
    dono = Usuario.objects.filter(paginas__id=id_pagina).first()
    id_dono = dono.id
    
    #--------------- prof
    
    # ------- fim area de card -------
    conteudo = {'pagina_principal': pagina_principal,
                'pagina_atual': id_pagina,
                'cards': cards,
                'cards_compartilhados': cards_compartilhados,
                'paginas_compartilhadas_cards': paginas_flashcards_compartilhadas,
                'paginas_compartilhadas_simulados':paginas_simulados_compartilhadas,
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
    dia= conteudo['dia']
    return conteudo

def conteudo_geral_enem(request, id_pagina):
    user_atual = request.user.username
    usuario_atual = Usuario.objects.get(arroba=user_atual)

    todas_as_paginas = usuario_atual.paginas.all()
    pagina_principal = usuario_atual.paginas.all().first()
    paginas_flashcards_compartilhadas = usuario_atual.paginas_compartilhadas.filter(cards__isnull=False).distinct()
    paginas_simulados_compartilhadas = usuario_atual.paginas_compartilhadas.filter(simulado__isnull=False).distinct()

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
                'paginas_compartilhadas_simulados':paginas_simulados_compartilhadas,
                
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
    dia= conteudo['dia']
    return conteudo


def conteudo_geral2(request, id_pagina):
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
                'usuario2':usuario_atual,
                'numero': numeros_1_a_90,
                'numero2': numeros_91_a_181,
                'enem_ano_dia': enem_ano_dia
                }
    dia= conteudo['dia']
    return conteudo
# ---- FIM BLOCO: retorna conteudos
