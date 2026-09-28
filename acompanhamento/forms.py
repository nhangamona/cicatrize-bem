import re
from django import forms
from django.contrib.auth.hashers import make_password
from .models import (
    Paciente, Medico, Cirurgia, EtapaAcompanhamento,
    EnvioFoto, Anamnese, Mensagem, LocalAtendimento
)

def normalizar_documento(doc):
    if not doc:
        return ''
    return re.sub(r'\D', '', str(doc))


class LoginForm(forms.Form):
    cpf = forms.CharField(
        label='CPF',
        max_length=14,
        widget=forms.TextInput(attrs={
            'class': 'form-input',
            'placeholder': 'Digite seu CPF',
            'id': 'cpf_input',
            'autocomplete': 'username',
        })
    )
    senha = forms.CharField(
        label='Senha',
        widget=forms.PasswordInput(attrs={
            'class': 'form-input',
            'placeholder': 'Digite sua senha',
            'id': 'senha_input',
            'autocomplete': 'current-password',
        })
    )

    def clean_cpf(self):
        cpf = normalizar_documento(self.cleaned_data.get('cpf'))
        if len(cpf) != 11:
            raise forms.ValidationError("Informe um CPF válido com 11 dígitos.")
        return cpf


class CadastroPacienteForm(forms.ModelForm):
    senha = forms.CharField(
        widget=forms.PasswordInput(attrs={'class': 'form-input', 'placeholder': 'Crie uma senha', 'id': 'senha'}),
        min_length=6
    )

    class Meta:
        model = Paciente
        fields = [
            'nome_completo', 'cartao_sus', 'cpf', 'data_nascimento',
            'cep', 'endereco', 'municipio', 'telefone', 'servico_atendimento'
        ]
        widgets = {
            'nome_completo': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'Digite seu nome completo'}),
            'cartao_sus': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'Digite o número do Cartão SUS'}),
            'cpf': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'Digite seu CPF'}),
            'data_nascimento': forms.DateInput(attrs={'class': 'form-input', 'type': 'date'}),
            'cep': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'Digite o CEP'}),
            'endereco': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'Digite seu endereço completo'}),
            'municipio': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'Digite seu município', 'value': 'Belém'}),
            'telefone': forms.TextInput(attrs={'class': 'form-input', 'placeholder': '(00) 00000-0000'}),
            'servico_atendimento': forms.Select(attrs={'class': 'form-select'}),
        }

    def clean_cpf(self):
        cpf = normalizar_documento(self.cleaned_data.get('cpf'))
        if len(cpf) != 11:
            raise forms.ValidationError("CPF deve conter 11 dígitos.")
        if Paciente.objects.filter(cpf=cpf).exists():
            raise forms.ValidationError("Este CPF já está cadastrado como paciente.")
        return cpf

    def clean_cep(self):
        return normalizar_documento(self.cleaned_data.get('cep'))

    def save(self, commit=True):
        paciente = super().save(commit=False)
        senha = self.cleaned_data['senha']
        paciente.senha_hash = make_password(senha)
        if commit:
            paciente.save()
        return paciente


class CadastroMedicoForm(forms.ModelForm):
    senha = forms.CharField(
        widget=forms.PasswordInput(attrs={'class': 'form-input', 'placeholder': 'Crie uma senha', 'id': 'senha'}),
        min_length=8
    )

    class Meta:
        model = Medico
        fields = [
            'nome_completo', 'cpf', 'email', 'data_nascimento',
            'crm', 'uf_crm', 'tipo_perfil', 'locais_atendimento'
        ]
        widgets = {
            'nome_completo': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'Digite seu nome completo'}),
            'cpf': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'Digite seu CPF'}),
            'email': forms.EmailInput(attrs={'class': 'form-input', 'placeholder': 'Digite seu e-mail'}),
            'data_nascimento': forms.DateInput(attrs={'class': 'form-input', 'type': 'date'}),
            'crm': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'Digite seu número do CRM'}),
            'uf_crm': forms.Select(attrs={'class': 'form-select'}, choices=[
                ('AC', 'AC'), ('AL', 'AL'), ('AP', 'AP'), ('AM', 'AM'), ('BA', 'BA'),
                ('CE', 'CE'), ('DF', 'DF'), ('ES', 'ES'), ('GO', 'GO'), ('MA', 'MA'),
                ('MT', 'MT'), ('MS', 'MS'), ('MG', 'MG'), ('PA', 'PA'), ('PB', 'PB'),
                ('PR', 'PR'), ('PE', 'PE'), ('PI', 'PI'), ('RJ', 'RJ'), ('RN', 'RN'),
                ('RS', 'RS'), ('RO', 'RO'), ('RR', 'RR'), ('SC', 'SC'), ('SP', 'SP'),
                ('SE', 'SE'), ('TO', 'TO'),
            ]),
            'tipo_perfil': forms.RadioSelect(attrs={'class': 'form-radio-group'}),
            'locais_atendimento': forms.CheckboxSelectMultiple(attrs={'class': 'form-checkbox-group'}),
        }

    def clean_cpf(self):
        cpf = normalizar_documento(self.cleaned_data.get('cpf'))
        if len(cpf) != 11:
            raise forms.ValidationError("CPF deve conter 11 dígitos.")
        if Medico.objects.filter(cpf=cpf).exists():
            raise forms.ValidationError("Este CPF já está cadastrado como médico.")
        return cpf

    def clean_senha(self):
        senha = self.cleaned_data.get('senha')
        if len(senha) < 8:
            raise forms.ValidationError("A senha deve ter no mínimo 8 caracteres.")
        return senha

    def save(self, commit=True):
        medico = super().save(commit=False)
        senha = self.cleaned_data['senha']
        medico.senha_hash = make_password(senha)
        if commit:
            medico.save()
            self.save_m2m()
        return medico


class EnvioEtapaForm(forms.ModelForm):
    foto = forms.ImageField(
        required=True,
        widget=forms.FileInput(attrs={'class': 'hidden-file-input', 'id': 'foto_input', 'accept': 'image/*'})
    )

    class Meta:
        model = Anamnese
        fields = [
            'intensidade_dor', 'ferida_sangrando', 'secrecao_pus',
            'inchaco', 'ponto_solto_ferida_abriu', 'febre_calafrios',
            'mensagem_opcional'
        ]
        widgets = {
            'intensidade_dor': forms.HiddenInput(attrs={'id': 'intensidade_dor_input', 'value': '0'}),
            'ferida_sangrando': forms.RadioSelect(choices=[(False, 'Não'), (True, 'Sim')]),
            'secrecao_pus': forms.RadioSelect(choices=[(False, 'Não'), (True, 'Sim')]),
            'inchaco': forms.RadioSelect(choices=[(False, 'Não'), (True, 'Sim')]),
            'ponto_solto_ferida_abriu': forms.RadioSelect(choices=[(False, 'Não'), (True, 'Sim')]),
            'febre_calafrios': forms.RadioSelect(choices=[(False, 'Não'), (True, 'Sim')]),
            'mensagem_opcional': forms.Textarea(attrs={
                'class': 'form-textarea',
                'rows': 3,
                'placeholder': 'Escreva uma mensagem curta...',
                'maxlength': '200',
                'id': 'mensagem_input'
            }),
        }


class NovaCirurgiaForm(forms.ModelForm):
    class Meta:
        model = Cirurgia
        fields = [
            'paciente', 'tipo_cirurgia', 'localizacao_lesao',
            'data_cirurgia', 'local_atendimento'
        ]
        widgets = {
            'paciente': forms.Select(attrs={'class': 'form-select'}),
            'tipo_cirurgia': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'Ex: Retirada de CBC + Retalho de Avanço'}),
            'localizacao_lesao': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'Ex: Região frontal / Nariz / Malar'}),
            'data_cirurgia': forms.DateInput(attrs={'class': 'form-input', 'type': 'date'}),
            'local_atendimento': forms.Select(attrs={'class': 'form-select'}),
        }
