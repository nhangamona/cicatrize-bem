from datetime import date
from django.test import TestCase, Client
from django.urls import reverse
from acompanhamento.models import (
    LocalAtendimento, Medico, Paciente, Cirurgia, EtapaAcompanhamento
)

class TelasSistemaTestCase(TestCase):
    def setUp(self):
        self.client = Client()
        self.local = LocalAtendimento.objects.create(
            nome="Serviço de Dermatologia da UEPA",
            municipio="Belém",
            uf="PA"
        )
        self.medico = Medico.objects.create(
            nome_completo="Dra. Fernanda Santos",
            cpf="11122233344",
            email="fernanda@uepa.br",
            data_nascimento=date(1985, 4, 15),
            crm="12345",
            uf_crm="PA",
            tipo_perfil="staff",
            senha_hash="dummy"
        )
        self.paciente = Paciente.objects.create(
            nome_completo="Paulo Andrade",
            cpf="12345678901",
            data_nascimento=date(1962, 5, 10),
            cep="66000000",
            endereco="Rua Principal",
            municipio="Tucuruí - PA",
            telefone="(91) 98111-2222",
            servico_atendimento=self.local,
            senha_hash="dummy",
            termo_aceito=True
        )
        self.cirurgia = Cirurgia.objects.create(
            paciente=self.paciente,
            medico=self.medico,
            tipo_cirurgia="Retalho de avanço frontal",
            data_cirurgia=date.today(),
            local_atendimento=self.local,
            status="a_ser_avaliado"
        )
        self.etapa = EtapaAcompanhamento.objects.create(
            cirurgia=self.cirurgia,
            dia_pos_operatorio=3,
            data_prevista=date.today(),
            data_liberacao=date.today(),
            status="pendente"
        )

    def test_tela_login(self):
        response = self.client.get(reverse('acompanhamento:login'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Cicatrize Bem")

    def test_tela_cadastro_paciente(self):
        response = self.client.get(reverse('acompanhamento:cadastro_paciente'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Cadastro do paciente")

    def test_tela_cadastro_medico(self):
        response = self.client.get(reverse('acompanhamento:cadastro_medico'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Cadastro médico")

    def test_tela_paciente_dashboard(self):
        # Simula sessão de paciente logado
        session = self.client.session
        session['usuario_id'] = str(self.paciente.id)
        session['tipo_usuario'] = 'paciente'
        session['usuario_nome'] = self.paciente.nome_completo
        session.save()

        response = self.client.get(reverse('acompanhamento:paciente_dashboard'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Seu acompanhamento")

    def test_tela_paciente_enviar_etapa(self):
        session = self.client.session
        session['usuario_id'] = str(self.paciente.id)
        session['tipo_usuario'] = 'paciente'
        session['usuario_nome'] = self.paciente.nome_completo
        session.save()

        response = self.client.get(reverse('acompanhamento:paciente_enviar_etapa', args=[self.etapa.id]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Enviar fotos - D3")
        self.assertContains(response, "Como tirar uma boa foto")
        self.assertContains(response, "Escala de dor (0 a 10)")

    def test_tela_paciente_videos(self):
        session = self.client.session
        session['usuario_id'] = str(self.paciente.id)
        session['tipo_usuario'] = 'paciente'
        session['usuario_nome'] = self.paciente.nome_completo
        session.save()

        response = self.client.get(reverse('acompanhamento:paciente_videos'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Vídeos")
        self.assertContains(response, "Curativos")

    def test_tela_medico_dashboard(self):
        session = self.client.session
        session['usuario_id'] = str(self.medico.id)
        session['tipo_usuario'] = 'medico'
        session['usuario_nome'] = self.medico.nome_completo
        session.save()

        response = self.client.get(reverse('acompanhamento:medico_dashboard'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "A serem avaliados")
        self.assertContains(response, "Em acompanhamento")

    def test_tela_medico_avaliacao(self):
        session = self.client.session
        session['usuario_id'] = str(self.medico.id)
        session['tipo_usuario'] = 'medico'
        session['usuario_nome'] = self.medico.nome_completo
        session.save()

        response = self.client.get(reverse('acompanhamento:medico_avaliacao', args=[self.etapa.id]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Avaliação do paciente")
        self.assertContains(response, "Resposta ao paciente")
