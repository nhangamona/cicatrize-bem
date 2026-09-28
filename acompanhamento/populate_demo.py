import os
from datetime import date, timedelta
from django.utils import timezone
from django.contrib.auth.hashers import make_password
from acompanhamento.models import (
    LocalAtendimento, Medico, Paciente, Cirurgia,
    EtapaAcompanhamento, EnvioFoto, Anamnese, Mensagem,
    VideoEducativo, Notificacao
)

def populate():
    print("Iniciando carregamento de dados de teste...")

    # 1. Locais de Atendimento
    uepa, _ = LocalAtendimento.objects.get_or_create(
        nome="Serviço de Dermatologia da Universidade do Estado do Pará",
        municipio="Belém",
        uf="PA"
    )
    cesupa, _ = LocalAtendimento.objects.get_or_create(
        nome="Centro Universitário do Estado do Pará",
        municipio="Belém",
        uf="PA"
    )
    ufpa, _ = LocalAtendimento.objects.get_or_create(
        nome="Universidade Federal do Pará",
        municipio="Belém",
        uf="PA"
    )

    # 2. Médicos
    senha_hash = make_password("12345678")
    
    medico_fernanda, _ = Medico.objects.get_or_create(
        cpf="11122233344",
        defaults={
            'nome_completo': "Dra. Fernanda Santos",
            'email': "fernanda@uepa.br",
            'data_nascimento': date(1985, 4, 15),
            'crm': "12345",
            'uf_crm': "PA",
            'tipo_perfil': "staff",
            'senha_hash': senha_hash
        }
    )
    medico_fernanda.locais_atendimento.add(uepa)

    medico_natalia, _ = Medico.objects.get_or_create(
        cpf="22233344455",
        defaults={
            'nome_completo': "Dra. Natalia Senado",
            'email': "natalia@uepa.br",
            'data_nascimento': date(1992, 8, 20),
            'crm': "54321",
            'uf_crm': "PA",
            'tipo_perfil': "residente",
            'senha_hash': senha_hash
        }
    )
    medico_natalia.locais_atendimento.add(uepa)

    # 3. Pacientes (como no mockup imagem3.jpeg e imagem5.jpg)
    paciente_paulo, _ = Paciente.objects.get_or_create(
        cpf="12345678901",
        defaults={
            'nome_completo': "Paulo Andrade",
            'cartao_sus': "700000000000001",
            'data_nascimento': date(1962, 5, 10),
            'cep': "66000000",
            'endereco': "Rua Principal, 120",
            'municipio': "Tucuruí - PA",
            'telefone': "(91) 98111-2222",
            'servico_atendimento': uepa,
            'senha_hash': senha_hash,
            'termo_aceito': True,
            'termo_aceito_em': timezone.now()
        }
    )

    paciente_larissa, _ = Paciente.objects.get_or_create(
        cpf="23456789012",
        defaults={
            'nome_completo': "Larissa Sousa",
            'cartao_sus': "700000000000002",
            'data_nascimento': date(1995, 3, 22),
            'cep': "68550000",
            'endereco': "Av. Brasil, 45",
            'municipio': "Redenção - PA",
            'telefone': "(94) 98222-3333",
            'servico_atendimento': uepa,
            'senha_hash': senha_hash,
            'termo_aceito': True,
            'termo_aceito_em': timezone.now()
        }
    )

    paciente_andre, _ = Paciente.objects.get_or_create(
        cpf="34567890123",
        defaults={
            'nome_completo': "André Carvalho",
            'cartao_sus': "700000000000003",
            'data_nascimento': date(1978, 11, 5),
            'cep': "68700000",
            'endereco': "Tv. 15 de Novembro, 88",
            'municipio': "Capanema - PA",
            'telefone': "(91) 98333-4444",
            'servico_atendimento': uepa,
            'senha_hash': senha_hash,
            'termo_aceito': True,
            'termo_aceito_em': timezone.now()
        }
    )

    # 4. Cirurgias
    hoje = date.today()
    data_cirurgia_paulo = hoje - timedelta(days=3)  # Exatamente no D3

    cirurgia_paulo, _ = Cirurgia.objects.get_or_create(
        paciente=paciente_paulo,
        tipo_cirurgia="Retalho de avanço para fechamento de defeito na região frontal",
        defaults={
            'medico': medico_natalia,
            'local_atendimento': uepa,
            'data_cirurgia': data_cirurgia_paulo,
            'status': "a_ser_avaliado"
        }
    )

    # Gera etapas D0, D3, D7, D14, D28 para Paulo
    etapas_dias = [0, 3, 7, 14, 28]
    for dia in etapas_dias:
        data_prevista = data_cirurgia_paulo + timedelta(days=dia)
        status = 'bloqueado'
        if dia == 0:
            status = 'concluido'
        elif dia == 3:
            status = 'pendente'

        etapa, created = EtapaAcompanhamento.objects.get_or_create(
            cirurgia=cirurgia_paulo,
            dia_pos_operatorio=dia,
            defaults={
                'data_prevista': data_prevista,
                'data_liberacao': data_prevista,
                'horario_lembrete': '08:00',
                'status': status
            }
        )

        if dia == 3:
            # Foto e Anamnese para teste de avaliação
            envio_foto, _ = EnvioFoto.objects.get_or_create(
                etapa=etapa,
                defaults={
                    'url_foto': '/static/img/imagem5.jpg'
                }
            )
            anamnese, _ = Anamnese.objects.get_or_create(
                etapa=etapa,
                defaults={
                    'tem_dor': False,
                    'intensidade_dor': 0,
                    'ferida_sangrando': True,
                    'secrecao_pus': False,
                    'inchaco': False,
                    'hematoma': False,
                    'febre_calafrios': False,
                    'mensagem_opcional': "Dra Fernanda, meus pontos romperam hoje. Preciso voltar na uepa?"
                }
            )

    # Cirurgia Larissa
    Cirurgia.objects.get_or_create(
        paciente=paciente_larissa,
        tipo_cirurgia="Lobuloplastia",
        defaults={
            'medico': medico_fernanda,
            'local_atendimento': uepa,
            'data_cirurgia': hoje - timedelta(days=2),
            'status': "a_ser_avaliado"
        }
    )

    # Cirurgia André
    Cirurgia.objects.get_or_create(
        paciente=paciente_andre,
        tipo_cirurgia="Cirurgia de Rinofima",
        defaults={
            'medico': medico_fernanda,
            'local_atendimento': uepa,
            'data_cirurgia': hoje - timedelta(days=5),
            'status': "a_ser_avaliado"
        }
    )

    # 5. Vídeos Educativos (conforme mockup imagem4.jpg)
    VideoEducativo.objects.get_or_create(
        titulo="Cuidados importantes no pós-operatório",
        defaults={
            'descricao': "Orientações gerais para evitar complicações e acelerar a recuperação.",
            'categoria': "cuidados",
            'url_video': "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
            'thumbnail_url': "/static/img/imagem5.jpg",
            'duracao_segundos': 140
        }
    )
    VideoEducativo.objects.get_or_create(
        titulo="Como realizar o curativo",
        defaults={
            'descricao': "Veja como fazer o curativo de forma correta e segura.",
            'categoria': "curativos",
            'url_video': "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
            'thumbnail_url': "/static/img/imagem1.jpeg",
            'duracao_segundos': 190
        }
    )
    VideoEducativo.objects.get_or_create(
        titulo="Complicações comuns após uma cirurgia",
        defaults={
            'descricao': "Saiba identificar sinais de alerta e quando procurar atendimento.",
            'categoria': "complicacoes",
            'url_video': "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
            'thumbnail_url': "/static/img/imagem6.jpeg",
            'duracao_segundos': 165
        }
    )
    VideoEducativo.objects.get_or_create(
        titulo="Exposição ao sol: quando é segura?",
        defaults={
            'descricao': "Entenda os cuidados com o sol durante o período de recuperação.",
            'categoria': "cuidados",
            'url_video': "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
            'thumbnail_url': "/static/img/imagem7.jpeg",
            'duracao_segundos': 90
        }
    )

    print("Carga de dados de teste finalizada com sucesso!")

if __name__ == "__main__":
    populate()
