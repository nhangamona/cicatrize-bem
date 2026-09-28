from django.urls import path
from . import views

app_name = 'acompanhamento'

urlpatterns = [
    path('', views.home_redirect, name='home'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('cadastro/paciente/', views.cadastro_paciente, name='cadastro_paciente'),
    path('cadastro/medico/', views.cadastro_medico, name='cadastro_medico'),
    
    # Paciente
    path('paciente/', views.paciente_dashboard, name='paciente_dashboard'),
    path('paciente/termo/', views.paciente_termo, name='paciente_termo'),
    path('paciente/etapa/<uuid:etapa_id>/enviar/', views.paciente_enviar_etapa, name='paciente_enviar_etapa'),
    path('paciente/videos/', views.paciente_videos, name='paciente_videos'),
    path('paciente/mensagens/', views.paciente_mensagens, name='paciente_mensagens'),
    path('paciente/perfil/', views.paciente_perfil, name='paciente_perfil'),

    # Médico
    path('medico/', views.medico_dashboard, name='medico_dashboard'),
    path('medico/avaliacao/<uuid:etapa_id>/', views.medico_avaliacao, name='medico_avaliacao'),
    path('medico/cirurgia/nova/', views.medico_nova_cirurgia, name='medico_nova_cirurgia'),
    path('medico/pacientes/', views.medico_pacientes, name='medico_pacientes'),
    path('medico/mensagens/', views.medico_mensagens, name='medico_mensagens'),
    path('medico/mensagens/<uuid:cirurgia_id>/', views.medico_mensagens_chat, name='medico_mensagens_chat'),
    path('medico/alertas/', views.medico_alertas, name='medico_alertas'),
    path('medico/perfil/', views.medico_perfil, name='medico_perfil'),
    path('medico/alta/<uuid:cirurgia_id>/', views.medico_dar_alta, name='medico_dar_alta'),
    path('medico/arquivar/<uuid:cirurgia_id>/', views.medico_arquivar, name='medico_arquivar'),
]
