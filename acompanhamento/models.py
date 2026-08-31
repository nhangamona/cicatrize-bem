import uuid
from django.db import models


class LocalAtendimento(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    nome = models.CharField(max_length=200)
    municipio = models.CharField(max_length=100)
    uf = models.CharField(max_length=2)

    def __str__(self):
        return self.nome


class Medico(models.Model):
    TIPO_PERFIL_CHOICES = [
        ('residente', 'Residente'),
        ('staff', 'Staff'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    nome_completo = models.CharField(max_length=200)
    cpf = models.CharField(max_length=11, unique=True)
    email = models.EmailField(unique=True)
    data_nascimento = models.DateField()
    crm = models.CharField(max_length=20)
    uf_crm = models.CharField(max_length=2)
    tipo_perfil = models.CharField(max_length=10, choices=TIPO_PERFIL_CHOICES)
    senha_hash = models.CharField(max_length=255)
    foto_perfil_url = models.URLField(blank=True, null=True)
    locais_atendimento = models.ManyToManyField(LocalAtendimento, related_name='medicos')
    criado_em = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.nome_completo


class Paciente(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    nome_completo = models.CharField(max_length=200)
    cartao_sus = models.CharField(max_length=15, blank=True, null=True)
    cpf = models.CharField(max_length=11, unique=True)
    data_nascimento = models.DateField()
    cep = models.CharField(max_length=8)
    endereco = models.CharField(max_length=255)
    municipio = models.CharField(max_length=100)
    telefone = models.CharField(max_length=20)
    servico_atendimento = models.ForeignKey(
        LocalAtendimento, on_delete=models.SET_NULL, null=True, related_name='pacientes'
    )
    senha_hash = models.CharField(max_length=255)
    criado_em = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.nome_completo


class Cirurgia(models.Model):
    STATUS_CHOICES = [
        ('a_ser_avaliado', 'A ser avaliado'),
        ('em_acompanhamento', 'Em acompanhamento'),
        ('alta', 'Alta'),
        ('arquivado', 'Arquivado'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    paciente = models.ForeignKey(Paciente, on_delete=models.CASCADE, related_name='cirurgias')
    medico = models.ForeignKey(Medico, on_delete=models.SET_NULL, null=True, related_name='cirurgias')
    tipo_cirurgia = models.CharField(max_length=255)
    local_atendimento = models.ForeignKey(
        LocalAtendimento, on_delete=models.SET_NULL, null=True, related_name='cirurgias'
    )
    data_cirurgia = models.DateField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='a_ser_avaliado')
    data_alta = models.DateField(blank=True, null=True)
    criado_em = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.paciente.nome_completo} - {self.tipo_cirurgia}"


class EtapaAcompanhamento(models.Model):
    STATUS_CHOICES = [
        ('bloqueado', 'Bloqueado'),
        ('pendente', 'Pendente'),
        ('atrasado', 'Atrasado'),
        ('concluido', 'Concluído'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    cirurgia = models.ForeignKey(Cirurgia, on_delete=models.CASCADE, related_name='etapas')
    dia_pos_operatorio = models.PositiveIntegerField()  # 0, 3, 7, 14, 28
    data_prevista = models.DateField()
    data_liberacao = models.DateField()
    horario_lembrete = models.TimeField(default='08:00')
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='bloqueado')
    data_envio_real = models.DateTimeField(blank=True, null=True)

    class Meta:
        ordering = ['dia_pos_operatorio']

    def __str__(self):
        return f"D{self.dia_pos_operatorio} - {self.cirurgia.paciente.nome_completo}"


class EnvioFoto(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    etapa = models.ForeignKey(EtapaAcompanhamento, on_delete=models.CASCADE, related_name='fotos')
    url_foto = models.URLField()
    data_envio = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Foto - {self.etapa}"


class Anamnese(models.Model):
    EVOLUCAO_DOR_CHOICES = [
        ('melhorando', 'Melhorando'),
        ('piorando', 'Piorando'),
    ]
    PERCEPCAO_CHOICES = [
        ('melhor', 'Melhor'),
        ('igual', 'Igual'),
        ('pior', 'Pior'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    etapa = models.OneToOneField(EtapaAcompanhamento, on_delete=models.CASCADE, related_name='anamnese')
    tem_dor = models.BooleanField(default=False)
    intensidade_dor = models.PositiveSmallIntegerField(default=0)  # 0 a 10
    evolucao_dor = models.CharField(max_length=10, choices=EVOLUCAO_DOR_CHOICES, blank=True, null=True)
    ferida_sangrando = models.BooleanField(default=False)
    secrecao_pus = models.BooleanField(default=False)
    inchaco = models.BooleanField(default=False)
    hematoma = models.BooleanField(default=False)
    ponto_solto_ferida_abriu = models.BooleanField(default=False)
    febre_calafrios = models.BooleanField(default=False)
    conseguiu_curativo = models.BooleanField(default=True)
    percepcao_geral = models.CharField(max_length=10, choices=PERCEPCAO_CHOICES, blank=True, null=True)
    mensagem_opcional = models.CharField(max_length=200, blank=True)
    respondido_em = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Anamnese - {self.etapa}"


class Alerta(models.Model):
    TIPO_CHOICES = [
        ('dor_intensa', 'Dor intensa'),
        ('sangramento', 'Sangramento'),
        ('febre', 'Febre'),
        ('deiscencia', 'Deiscência'),
        ('secrecao', 'Secreção'),
        ('outro', 'Outro'),
    ]
    STATUS_CHOICES = [
        ('pendente', 'Pendente'),
        ('visualizado', 'Visualizado'),
        ('resolvido', 'Resolvido'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    etapa = models.ForeignKey(EtapaAcompanhamento, on_delete=models.CASCADE, related_name='alertas')
    tipo = models.CharField(max_length=20, choices=TIPO_CHOICES)
    status = models.CharField(max_length=15, choices=STATUS_CHOICES, default='pendente')
    criado_em = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Alerta {self.tipo} - {self.etapa}"


class Mensagem(models.Model):
    REMETENTE_CHOICES = [
        ('paciente', 'Paciente'),
        ('medico', 'Médico'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    cirurgia = models.ForeignKey(Cirurgia, on_delete=models.CASCADE, related_name='mensagens')
    remetente_tipo = models.CharField(max_length=10, choices=REMETENTE_CHOICES)
    remetente_id = models.UUIDField()
    conteudo = models.TextField()
    anexo_url = models.URLField(blank=True, null=True)
    enviado_em = models.DateTimeField(auto_now_add=True)
    lida = models.BooleanField(default=False)

    class Meta:
        ordering = ['enviado_em']

    def __str__(self):
        return f"{self.remetente_tipo}: {self.conteudo[:30]}"


class Notificacao(models.Model):
    DESTINATARIO_CHOICES = [
        ('paciente', 'Paciente'),
        ('medico', 'Médico'),
    ]
    TIPO_CHOICES = [
        ('lembrete_envio', 'Lembrete de envio'),
        ('novo_alerta', 'Novo alerta'),
        ('nova_mensagem', 'Nova mensagem'),
        ('resposta_medico', 'Resposta do médico'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    destinatario_tipo = models.CharField(max_length=10, choices=DESTINATARIO_CHOICES)
    destinatario_id = models.UUIDField()
    tipo = models.CharField(max_length=20, choices=TIPO_CHOICES)
    conteudo = models.CharField(max_length=255)
    lida = models.BooleanField(default=False)
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-criado_em']

    def __str__(self):
        return f"{self.tipo} - {self.destinatario_tipo}"


class VideoEducativo(models.Model):
    CATEGORIA_CHOICES = [
        ('curativos', 'Curativos'),
        ('cuidados', 'Cuidados'),
        ('complicacoes', 'Complicações'),
        ('outros', 'Outros'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    titulo = models.CharField(max_length=200)
    descricao = models.CharField(max_length=500)
    categoria = models.CharField(max_length=15, choices=CATEGORIA_CHOICES)
    url_video = models.URLField()
    thumbnail_url = models.URLField(blank=True, null=True)
    duracao_segundos = models.PositiveIntegerField()

    def __str__(self):
        return self.titulo