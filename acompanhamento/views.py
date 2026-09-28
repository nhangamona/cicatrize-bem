import json
import re
from datetime import date, datetime, timedelta
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.hashers import check_password, make_password
from django.http import JsonResponse, HttpResponseRedirect, HttpResponse
from django.conf import settings
from django.urls import reverse
from django.utils import timezone
from django.db.models import Q

from .models import (
    Paciente, Medico, Cirurgia, EtapaAcompanhamento,
    EnvioFoto, Anamnese, Alerta, Mensagem, Notificacao,
    VideoEducativo, LocalAtendimento
)
from .forms import (
    LoginForm, CadastroPacienteForm, CadastroMedicoForm,
    EnvioEtapaForm, NovaCirurgiaForm, normalizar_documento
)


# ==========================================
# Helpers de Autenticação e Sessão
# ==========================================

def get_usuario_logado(request):
    tipo = request.session.get('tipo_usuario')
    usuario_id = request.session.get('usuario_id')
    if not tipo or not usuario_id:
        return None, None

    if tipo == 'paciente':
        try:
            return 'paciente', Paciente.objects.get(id=usuario_id)
        except Paciente.DoesNotExist:
            return None, None
    elif tipo == 'medico':
        try:
            return 'medico', Medico.objects.get(id=usuario_id)
        except Medico.DoesNotExist:
            return None, None
    return None, None


def login_usuario(request, usuario, tipo):
    request.session['usuario_id'] = str(usuario.id)
    request.session['tipo_usuario'] = tipo
    request.session['usuario_nome'] = usuario.nome_completo


def logout_usuario(request):
    request.session.flush()


def paciente_required(view_func):
    def wrapper(request, *args, **kwargs):
        tipo, usuario = get_usuario_logado(request)
        if tipo != 'paciente':
            messages.warning(request, "Por favor, faça login como paciente para acessar esta área.")
            return redirect('acompanhamento:login')
        request.paciente = usuario
        return view_func(request, *args, **kwargs)
    return wrapper


def medico_required(view_func):
    def wrapper(request, *args, **kwargs):
        tipo, usuario = get_usuario_logado(request)
        if tipo != 'medico':
            messages.warning(request, "Acesso restrito para a equipe médica.")
            return redirect('acompanhamento:login')
        request.medico = usuario
        return view_func(request, *args, **kwargs)
    return wrapper


# ==========================================
# Regras Clínicas e Protocolos Dermatológicos
# ==========================================

DIAS_PROTOCOLO = [0, 3, 7, 14, 28]

def gerar_etapas_protocolo(cirurgia):
    """Gera automaticamente as 5 etapas pós-operatórias para a cirurgia dermatológica."""
    hoje = date.today()
    for dia in DIAS_PROTOCOLO:
        data_prevista = cirurgia.data_cirurgia + timedelta(days=dia)
        data_liberacao = data_prevista
        
        status = 'bloqueado'
        if data_liberacao <= hoje:
            status = 'pendente'
            
        EtapaAcompanhamento.objects.get_or_create(
            cirurgia=cirurgia,
            dia_pos_operatorio=dia,
            defaults={
                'data_prevista': data_prevista,
                'data_liberacao': data_liberacao,
                'horario_lembrete': '08:00',
                'status': status,
            }
        )


def processar_alertas_clinicos(anamnese):
    """
    Avalia os sinais flogísticos e sintomas informados pelo paciente.
    Gera alertas clínicos automáticos e notifica a equipe médica.
    """
    etapa = anamnese.etapa
    cirurgia = etapa.cirurgia
    alertas_criados = []

    # 1. Febre
    if anamnese.febre_calafrios:
        alerta, _ = Alerta.objects.get_or_create(
            etapa=etapa, tipo='febre', status='pendente'
        )
        alertas_criados.append("Febre / Calafrios")

    # 2. Deiscência de sutura / Ponto solto
    if anamnese.ponto_solto_ferida_abriu:
        alerta, _ = Alerta.objects.get_or_create(
            etapa=etapa, tipo='deiscencia', status='pendente'
        )
        alertas_criados.append("Ponto solto / Deiscência")

    # 3. Sangramento
    if anamnese.ferida_sangrando:
        alerta, _ = Alerta.objects.get_or_create(
            etapa=etapa, tipo='sangramento', status='pendente'
        )
        alertas_criados.append("Sangramento ativo")

    # 4. Secreção purulenta
    if anamnese.secrecao_pus:
        alerta, _ = Alerta.objects.get_or_create(
            etapa=etapa, tipo='secrecao', status='pendente'
        )
        alertas_criados.append("Secreção purulenta")

    # 5. Dor Intensa (escala >= 7)
    if anamnese.intensidade_dor >= 7:
        alerta, _ = Alerta.objects.get_or_create(
            etapa=etapa, tipo='dor_intensa', status='pendente'
        )
        alertas_criados.append(f"Dor intensa (nível {anamnese.intensidade_dor}/10)")

    # Se houve alertas, marcar a cirurgia como precisando de avaliação urgente
    cirurgia.status = 'a_ser_avaliado'
    cirurgia.save()

    # Notificar médico responsável ou equipe do serviço
    if cirurgia.medico:
        conteudo = f"Novo envio de {cirurgia.paciente.nome_completo} (D{etapa.dia_pos_operatorio})."
        if alertas_criados:
            conteudo += f" ATENÇÃO: {', '.join(alertas_criados)}."
            tipo_notif = 'novo_alerta'
        else:
            tipo_notif = 'lembrete_envio'

        Notificacao.objects.create(
            destinatario_tipo='medico',
            destinatario_id=cirurgia.medico.id,
            tipo=tipo_notif,
            conteudo=conteudo
        )


# ==========================================
# Views de Acesso Público e Autenticação
# ==========================================

def home_redirect(request):
    tipo, _ = get_usuario_logado(request)
    if tipo == 'paciente':
        return redirect('acompanhamento:paciente_dashboard')
    elif tipo == 'medico':
        return redirect('acompanhamento:medico_dashboard')
    return redirect('acompanhamento:login')


def login_view(request):
    tipo, _ = get_usuario_logado(request)
    if tipo == 'paciente':
        return redirect('acompanhamento:paciente_dashboard')
    elif tipo == 'medico':
        return redirect('acompanhamento:medico_dashboard')

    if request.method == 'POST':
        form = LoginForm(request.POST)
        if form.is_valid():
            cpf = form.cleaned_data['cpf']
            senha = form.cleaned_data['senha']

            # Tenta autenticar como Paciente primeiro
            paciente = Paciente.objects.filter(cpf=cpf).first()
            if paciente and check_password(senha, paciente.senha_hash):
                login_usuario(request, paciente, 'paciente')
                if not paciente.termo_aceito:
                    return redirect('acompanhamento:paciente_termo')
                return redirect('acompanhamento:paciente_dashboard')

            # Tenta autenticar como Médico
            medico = Medico.objects.filter(cpf=cpf).first()
            if medico and check_password(senha, medico.senha_hash):
                login_usuario(request, medico, 'medico')
                return redirect('acompanhamento:medico_dashboard')

            messages.error(request, "CPF ou senha incorretos. Por favor, tente novamente.")
    else:
        form = LoginForm()

    return render(request, 'acompanhamento/login.html', {'form': form})


def logout_view(request):
    logout_usuario(request)
    messages.info(request, "Você saiu da sua conta.")
    return redirect('acompanhamento:login')


def cadastro_paciente(request):
    if request.method == 'POST':
        form = CadastroPacienteForm(request.POST)
        if form.is_valid():
            paciente = form.save()
            login_usuario(request, paciente, 'paciente')
            messages.success(request, "Cadastro realizado com sucesso! Por favor, leia o Termo de Consentimento.")
            return redirect('acompanhamento:paciente_termo')
    else:
        form = CadastroPacienteForm()

    locais = LocalAtendimento.objects.all()
    return render(request, 'acompanhamento/cadastro_paciente.html', {'form': form, 'locais': locais})


def cadastro_medico(request):
    if request.method == 'POST':
        form = CadastroMedicoForm(request.POST)
        if form.is_valid():
            medico = form.save()
            login_usuario(request, medico, 'medico')
            messages.success(request, "Cadastro médico concluído com sucesso!")
            return redirect('acompanhamento:medico_dashboard')
    else:
        form = CadastroMedicoForm()

    locais = LocalAtendimento.objects.all()
    return render(request, 'acompanhamento/cadastro_medico.html', {'form': form, 'locais': locais})


# ==========================================
# Portal do Paciente
# ==========================================

@paciente_required
def paciente_termo(request):
    paciente = request.paciente
    if request.method == 'POST':
        paciente.termo_aceito = True
        paciente.termo_aceito_em = timezone.now()
        paciente.save()
        messages.success(request, "Termo aceito com sucesso. Bem-vindo(a) ao Cicatrize Bem!")
        return redirect('acompanhamento:paciente_dashboard')

    return render(request, 'acompanhamento/paciente_termo.html', {'paciente': paciente})


@paciente_required
def paciente_dashboard(request):
    paciente = request.paciente
    if not paciente.termo_aceito:
        return redirect('acompanhamento:paciente_termo')

    cirurgia = Cirurgia.objects.filter(paciente=paciente).exclude(status='arquivado').order_by('-data_cirurgia').first()

    proxima_etapa = None
    dias_restantes = None
    etapas = []

    if cirurgia:
        hoje = date.today()
        todas_etapas = cirurgia.etapas.all().order_by('dia_pos_operatorio')
        
        for e in todas_etapas:
            # Calcular dias de diferença
            dias_diff = (e.data_prevista - hoje).days
            e.dias_diff = dias_diff
            
            # Se a etapa ainda não foi enviada e já está liberada
            if e.status != 'concluido' and e.data_liberacao <= hoje:
                e.status = 'pendente'
            elif e.status != 'concluido' and e.data_liberacao > hoje:
                e.status = 'bloqueado'
                
            if not proxima_etapa and e.status != 'concluido':
                proxima_etapa = e
                dias_restantes = max(0, dias_diff)

        etapas = todas_etapas

    notificacoes_count = Notificacao.objects.filter(
        destinatario_tipo='paciente', destinatario_id=paciente.id, lida=False
    ).count()

    context = {
        'paciente': paciente,
        'cirurgia': cirurgia,
        'proxima_etapa': proxima_etapa,
        'dias_restantes': dias_restantes,
        'etapas': etapas,
        'notificacoes_count': notificacoes_count,
        'aba_ativa': 'inicio',
    }
    return render(request, 'acompanhamento/paciente_dashboard.html', context)


@paciente_required
def paciente_enviar_etapa(request, etapa_id):
    paciente = request.paciente
    etapa = get_object_or_404(EtapaAcompanhamento, id=etapa_id, cirurgia__paciente=paciente)

    if request.method == 'POST':
        form = EnvioEtapaForm(request.POST, request.FILES)
        if form.is_valid():
            # 1. Salvar Foto
            foto_file = request.FILES.get('foto')
            envio_foto = EnvioFoto.objects.create(
                etapa=etapa,
                imagem=foto_file,
                url_foto=''
            )

            # 2. Salvar Anamnese
            anamnese = form.save(commit=False)
            anamnese.etapa = etapa
            anamnese.tem_dor = (anamnese.intensidade_dor > 0)
            anamnese.save()

            # 3. Atualizar Etapa
            etapa.status = 'concluido'
            etapa.data_envio_real = timezone.now()
            etapa.save()

            # 4. Avaliar Alertas
            processar_alertas_clinicos(anamnese)

            # 5. Se o paciente escreveu mensagem, criar registro no chat
            if anamnese.mensagem_opcional:
                Mensagem.objects.create(
                    cirurgia=etapa.cirurgia,
                    remetente_tipo='paciente',
                    remetente_id=paciente.id,
                    conteudo=anamnese.mensagem_opcional
                )

            messages.success(request, f"Fotos e respostas do D{etapa.dia_pos_operatorio} enviadas com sucesso! A equipe médica irá avaliar.")
            return redirect('acompanhamento:paciente_dashboard')
    else:
        form = EnvioEtapaForm()

    context = {
        'paciente': paciente,
        'etapa': etapa,
        'form': form,
        'aba_ativa': 'envios',
    }
    return render(request, 'acompanhamento/paciente_enviar_etapa.html', context)


@paciente_required
def paciente_videos(request):
    paciente = request.paciente
    categoria = request.GET.get('categoria', 'todos')

    videos = VideoEducativo.objects.all()
    if categoria and categoria != 'todos':
        videos = videos.filter(categoria=categoria)

    context = {
        'paciente': paciente,
        'videos': videos,
        'categoria_ativa': categoria,
        'aba_ativa': 'orientacoes',
    }
    return render(request, 'acompanhamento/paciente_videos.html', context)


@paciente_required
def paciente_mensagens(request):
    paciente = request.paciente
    cirurgia = Cirurgia.objects.filter(paciente=paciente).exclude(status='arquivado').order_by('-data_cirurgia').first()

    if not cirurgia:
        messages.info(request, "Nenhuma cirurgia ativa vinculada para envio de mensagens.")
        return redirect('acompanhamento:paciente_dashboard')

    if request.method == 'POST':
        conteudo = request.POST.get('conteudo', '').strip()
        arquivo = request.FILES.get('anexo')
        if conteudo or arquivo:
            Mensagem.objects.create(
                cirurgia=cirurgia,
                remetente_tipo='paciente',
                remetente_id=paciente.id,
                conteudo=conteudo or '(Arquivo anexado)',
                anexo_arquivo=arquivo
            )
            # Notificar médico
            if cirurgia.medico:
                Notificacao.objects.create(
                    destinatario_tipo='medico',
                    destinatario_id=cirurgia.medico.id,
                    tipo='nova_mensagem',
                    conteudo=f"Nova mensagem de {paciente.nome_completo}"
                )
            return redirect('acompanhamento:paciente_mensagens')

    mensagens = cirurgia.mensagens.all().order_by('enviado_em')

    context = {
        'paciente': paciente,
        'cirurgia': cirurgia,
        'mensagens': mensagens,
        'aba_ativa': 'mensagens',
    }
    return render(request, 'acompanhamento/paciente_mensagens.html', context)


@paciente_required
def paciente_perfil(request):
    paciente = request.paciente
    context = {
        'paciente': paciente,
        'aba_ativa': 'perfil',
    }
    return render(request, 'acompanhamento/paciente_perfil.html', context)


# ==========================================
# Portal do Médico / Clinical Hub
# ==========================================

@medico_required
def medico_dashboard(request):
    medico = request.medico

    # Filtros e Busca
    busca = request.GET.get('busca', '').strip()
    ordem = request.GET.get('ordem', 'data_cirurgia')

    cirurgias = Cirurgia.objects.all().select_related('paciente', 'medico', 'local_atendimento')

    if busca:
        cirurgias = cirurgias.filter(
            Q(paciente__nome_completo__icontains=busca) |
            Q(tipo_cirurgia__icontains=busca) |
            Q(paciente__municipio__icontains=busca)
        )

    # Ordenação
    if ordem == 'nome_paciente':
        cirurgias = cirurgias.order_by('paciente__nome_completo')
    elif ordem == 'nome_cirurgiao':
        cirurgias = cirurgias.order_by('medico__nome_completo')
    else:
        cirurgias = cirurgias.order_by('-data_cirurgia')

    # Separação por seções (como no mockup imagem3.jpeg)
    a_ser_avaliados = []
    em_acompanhamento = []
    altas = []

    hoje = date.today()

    for c in cirurgias:
        # Calcular status da última etapa
        etapa_recente = c.etapas.filter(status='concluido', parecer_medico__isnull=True).order_by('-dia_pos_operatorio').first()
        c.etapa_pendente_avaliacao = etapa_recente

        # Cálculo de atraso geral
        etapa_atrasada = c.etapas.filter(status='pendente', data_prevista__lt=hoje).first()
        if etapa_atrasada:
            c.dias_atraso = (hoje - etapa_atrasada.data_prevista).days
            c.status_label = f"Atrasado {c.dias_atraso} dia{'s' if c.dias_atraso > 1 else ''}"
            c.status_tipo = 'atrasado'
        else:
            c.status_label = "Em dia"
            c.status_tipo = 'em_dia'

        if c.status == 'alta':
            altas.append(c)
        elif c.status == 'a_ser_avaliado' or etapa_recente:
            a_ser_avaliados.append(c)
        elif c.status == 'em_acompanhamento':
            em_acompanhamento.append(c)

    notificacoes_count = Notificacao.objects.filter(
        destinatario_tipo='medico', destinatario_id=medico.id, lida=False
    ).count()

    alertas_count = Alerta.objects.filter(status='pendente').count()

    context = {
        'medico': medico,
        'a_ser_avaliados': a_ser_avaliados,
        'em_acompanhamento': em_acompanhamento,
        'altas': altas,
        'total_a_avaliar': len(a_ser_avaliados),
        'total_em_acompanhamento': len(em_acompanhamento),
        'total_altas': len(altas),
        'notificacoes_count': notificacoes_count,
        'alertas_count': alertas_count,
        'busca': busca,
        'ordem': ordem,
        'aba_ativa': 'dashboard',
    }
    return render(request, 'acompanhamento/medico_dashboard.html', context)


@medico_required
def medico_avaliacao(request, etapa_id):
    """
    Tela de avaliação médica da etapa (fiel a imagem5.jpg):
    Foto enviada, respostas de anamnese, mensagem do paciente e formulário de resposta médica.
    """
    medico = request.medico
    etapa = get_object_or_404(
        EtapaAcompanhamento.objects.select_related('cirurgia__paciente', 'cirurgia__medico', 'cirurgia__local_atendimento'),
        id=etapa_id
    )
    cirurgia = etapa.cirurgia
    paciente = cirurgia.paciente

    foto = etapa.fotos.order_by('-data_envio').first()
    anamnese = getattr(etapa, 'anamnese', None)
    mensagens_paciente = cirurgia.mensagens.filter(remetente_tipo='paciente').order_by('-enviado_em').first()

    if request.method == 'POST':
        resposta_texto = request.POST.get('resposta', '').strip()
        classificacao = request.POST.get('classificacao_cicatrizacao', 'favoravel')

        if resposta_texto:
            etapa.parecer_medico = resposta_texto
            etapa.classificacao_cicatrizacao = classificacao
            etapa.avaliado_por = medico
            etapa.avaliado_em = timezone.now()
            etapa.save()

            # Envia mensagem no chat da cirurgia
            Mensagem.objects.create(
                cirurgia=cirurgia,
                remetente_tipo='medico',
                remetente_id=medico.id,
                conteudo=resposta_texto
            )

            # Notificar paciente
            Notificacao.objects.create(
                destinatario_tipo='paciente',
                destinatario_id=paciente.id,
                tipo='resposta_medico',
                conteudo=f"A equipe médica avaliou o seu D{etapa.dia_pos_operatorio}. Veja as orientações."
            )

            # Resolver alertas pendentes desta etapa
            etapa.alertas.filter(status='pendente').update(status='resolvido')

            # Atualizar status da cirurgia para em_acompanhamento se não houver mais avaliações pendentes
            cirurgia.status = 'em_acompanhamento'
            cirurgia.save()

            messages.success(request, f"Avaliação registrada e resposta enviada para {paciente.nome_completo}!")
            return redirect('acompanhamento:medico_dashboard')

    # Calcular idade do paciente
    idade = None
    if paciente.data_nascimento:
        hoje = date.today()
        idade = hoje.year - paciente.data_nascimento.year - (
            (hoje.month, hoje.day) < (paciente.data_nascimento.month, paciente.data_nascimento.day)
        )

    context = {
        'medico': medico,
        'etapa': etapa,
        'cirurgia': cirurgia,
        'paciente': paciente,
        'idade': idade,
        'foto': foto,
        'anamnese': anamnese,
        'ultima_mensagem': mensagens_paciente,
        'aba_ativa': 'dashboard',
    }
    return render(request, 'acompanhamento/medico_avaliacao.html', context)


@medico_required
def medico_nova_cirurgia(request):
    medico = request.medico
    if request.method == 'POST':
        form = NovaCirurgiaForm(request.POST)
        if form.is_valid():
            cirurgia = form.save(commit=False)
            cirurgia.medico = medico
            cirurgia.status = 'em_acompanhamento'
            cirurgia.save()

            # Gerar automaticamente D0, D3, D7, D14, D28
            gerar_etapas_protocolo(cirurgia)

            messages.success(request, f"Cirurgia cadastrada e protocolo D0-D28 gerado com sucesso para {cirurgia.paciente.nome_completo}!")
            return redirect('acompanhamento:medico_dashboard')
    else:
        form = NovaCirurgiaForm()

    return render(request, 'acompanhamento/medico_nova_cirurgia.html', {'form': form, 'medico': medico})


@medico_required
def medico_pacientes(request):
    medico = request.medico
    pacientes = Paciente.objects.all().order_by('nome_completo')
    return render(request, 'acompanhamento/medico_pacientes.html', {'medico': medico, 'pacientes': pacientes, 'aba_ativa': 'pacientes'})


@medico_required
def medico_mensagens(request):
    medico = request.medico
    cirurgias = Cirurgia.objects.filter(
        mensagens__isnull=False
    ).distinct().select_related('paciente').order_by('-criado_em')

    context = {
        'medico': medico,
        'cirurgias': cirurgias,
        'aba_ativa': 'mensagens',
    }
    return render(request, 'acompanhamento/medico_mensagens_lista.html', context)


@medico_required
def medico_mensagens_chat(request, cirurgia_id):
    medico = request.medico
    cirurgia = get_object_or_404(Cirurgia.objects.select_related('paciente'), id=cirurgia_id)

    if request.method == 'POST':
        conteudo = request.POST.get('conteudo', '').strip()
        arquivo = request.FILES.get('anexo')
        if conteudo or arquivo:
            Mensagem.objects.create(
                cirurgia=cirurgia,
                remetente_tipo='medico',
                remetente_id=medico.id,
                conteudo=conteudo or '(Arquivo anexado)',
                anexo_arquivo=arquivo
            )
            # Notificar paciente
            Notificacao.objects.create(
                destinatario_tipo='paciente',
                destinatario_id=cirurgia.paciente.id,
                tipo='nova_mensagem',
                conteudo=f"Nova mensagem da equipe médica."
            )
            return redirect('acompanhamento:medico_mensagens_chat', cirurgia_id=cirurgia.id)

    mensagens = cirurgia.mensagens.all().order_by('enviado_em')

    context = {
        'medico': medico,
        'cirurgia': cirurgia,
        'paciente': cirurgia.paciente,
        'mensagens': mensagens,
        'aba_ativa': 'mensagens',
    }
    return render(request, 'acompanhamento/medico_chat.html', context)


@medico_required
def medico_alertas(request):
    medico = request.medico
    alertas = Alerta.objects.filter(status='pendente').select_related(
        'etapa__cirurgia__paciente', 'etapa__cirurgia__medico'
    ).order_by('-criado_em')

    if request.method == 'POST':
        alerta_id = request.POST.get('alerta_id')
        if alerta_id:
            alerta = get_object_or_404(Alerta, id=alerta_id)
            alerta.status = 'resolvido'
            alerta.save()
            messages.success(request, f"Alerta de {alerta.get_tipo_display()} resolvido com sucesso.")
            return redirect('acompanhamento:medico_alertas')

    context = {
        'medico': medico,
        'alertas': alertas,
        'aba_ativa': 'alertas',
    }
    return render(request, 'acompanhamento/medico_alertas.html', context)


@medico_required
def medico_dar_alta(request, cirurgia_id):
    cirurgia = get_object_or_404(Cirurgia, id=cirurgia_id)
    cirurgia.status = 'alta'
    cirurgia.data_alta = date.today()
    cirurgia.save()
    messages.success(request, f"Alta concedida com sucesso para o paciente {cirurgia.paciente.nome_completo}!")
    return redirect('acompanhamento:medico_dashboard')


@medico_required
def medico_arquivar(request, cirurgia_id):
    cirurgia = get_object_or_404(Cirurgia, id=cirurgia_id)
    cirurgia.status = 'arquivado'
    cirurgia.save()
    messages.info(request, f"Cirurgia arquivada.")
    return redirect('acompanhamento:medico_dashboard')


@medico_required
def medico_perfil(request):
    medico = request.medico
    context = {
        'medico': medico,
        'aba_ativa': 'perfil',
    }
    return render(request, 'acompanhamento/medico_perfil.html', context)


# ==========================================
# PWA (Progressive Web App) Endpoints
# ==========================================

def service_worker_view(request):
    sw_path = settings.BASE_DIR / 'acompanhamento' / 'static' / 'js' / 'sw.js'
    try:
        with open(sw_path, 'r', encoding='utf-8') as f:
            content = f.read()
        response = HttpResponse(content, content_type='application/javascript')
        response['Service-Worker-Allowed'] = '/'
        return response
    except FileNotFoundError:
        return HttpResponse('// sw not found', content_type='application/javascript')


def manifest_view(request):
    manifest_path = settings.BASE_DIR / 'acompanhamento' / 'static' / 'manifest.json'
    try:
        with open(manifest_path, 'r', encoding='utf-8') as f:
            content = f.read()
        return HttpResponse(content, content_type='application/manifest+json')
    except FileNotFoundError:
        return HttpResponse('{}', content_type='application/manifest+json')

