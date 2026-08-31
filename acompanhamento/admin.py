from django.contrib import admin
from .models import (
    LocalAtendimento, Medico, Paciente, Cirurgia,
    EtapaAcompanhamento, EnvioFoto, Anamnese, Alerta,
    Mensagem, Notificacao, VideoEducativo,
)

admin.site.register(LocalAtendimento)
admin.site.register(Medico)
admin.site.register(Paciente)
admin.site.register(Cirurgia)
admin.site.register(EtapaAcompanhamento)
admin.site.register(EnvioFoto)
admin.site.register(Anamnese)
admin.site.register(Alerta)
admin.site.register(Mensagem)
admin.site.register(Notificacao)
admin.site.register(VideoEducativo)