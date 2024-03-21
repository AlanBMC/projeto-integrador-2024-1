from django.urls import path
from . import views
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [

    path('', views.home, name='home'),
    path('cadastro/', views.cadastro, name='cadastro'),
    path('login/', views.login_user, name='login'),
    path('logout/', views.logout_view, name='logout'),

    # paginas
    path('paginas/<int:pagina_id>', views.paginas, name='paginas'),

    # cards
    path('pagina_card_add/', views.add_pagina_card, name='add_pagina_card'),
    path('add_cards/', views.add_cards, name='add_cards'),
    path('edit_cards/', views.edit_cards, name='edit_cards'),
    path('delete_card/', views.delete_card, name='delete_card'),

    # simulado
    path('simulado/<int:simulado_id>', views.simulado, name='simulado'),
    path('add_pagina_simulado/', views.add_pagina_simulado,
         name='add_pagina_simulado'),
    path('add_questoes_simulado/', views.questao_simulado, name='questao_simulado'),
    path('edit_questao/', views.edit_questao, name='edit_questao'),
    path('delete_questao/', views.delete_questao, name='delete_questao'),
    path('checa_resposta_simulado/', views.checa_resposta_simulado,
         name='checa_resposta_simulado'),
    path('sol/', views.sol, name='sol'),

    path('enem/<int:enem_d>', views.enem, name='enem'),
    path('resposta_enem/', views.resposta_enem, name='resposta_enem'),
    path('processa_dados_enem/<int:enem_dia_ano>', views.processa_dados_enem, name='processa_dados_enem'),

    #configurar
    path('configurar/', views.configurar, name='configurar'),
    path('edit_paginas/', views.edit_paginas_conf, name='edit_paginas_conf' ),
    path('delete_pg/', views.delete_pg, name='delete_pg'),
    path('edit_titulo_pg/', views.edit_titulo_pg, name='edit_titulo_pg'),

    #compartilhamento
    path('add_alunos/', views.add_alunos, name='add_alunos'),

    #paginas compartilhadas
    path('paginas_compartilhadas_cards/<int:pagina_compartilhada_id>', views.paginas_compartilhadas_cards, name='paginas_compartilhadas_cards'),
    path('paginas_compartilhadas_simulados/<int:pagina_compartilhada_id>', views.paginas_compartilhadas_simulados, name='paginas_compartilhadas_simulados'),

    #checa respostas das paginas compartilhadas
    path('checa_resposta_simulado_prof/', views.checa_resposta_simulado_prof, name='checa_resposta_simulado_prof'),
    path('estatisticas_prof/', views.estatisticas_prof, name='estatisticas_prof'),

    path('estatisticas_simulado/', views.estatisticas_simulado, name='estatisticas_simulado')
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
