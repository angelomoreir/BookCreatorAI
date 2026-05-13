from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, BooleanField, SubmitField
from wtforms.validators import DataRequired, Email, Length, EqualTo, ValidationError
from models.book import User

class LoginForm(FlaskForm):
    """Login form"""
    email = StringField('Email', validators=[
        DataRequired(message='Email é obrigatório'),
        Email(message='Email inválido')
    ])
    password = PasswordField('Password', validators=[
        DataRequired(message='Password é obrigatória')
    ])
    remember = BooleanField('Lembrar-me')
    submit = SubmitField('Entrar')

class RegisterForm(FlaskForm):
    """Registration form"""
    name = StringField('Nome', validators=[
        DataRequired(message='Nome é obrigatório'),
        Length(min=2, max=150, message='Nome deve ter entre 2 e 150 caracteres')
    ])
    email = StringField('Email', validators=[
        DataRequired(message='Email é obrigatório'),
        Email(message='Email inválido')
    ])
    password = PasswordField('Password', validators=[
        DataRequired(message='Password é obrigatória'),
        Length(min=6, message='Password deve ter pelo menos 6 caracteres')
    ])
    confirm_password = PasswordField('Confirmar Password', validators=[
        DataRequired(message='Confirmação é obrigatória'),
        EqualTo('password', message='Passwords não coincidem')
    ])
    submit = SubmitField('Criar Conta')
    
    def validate_email(self, email):
        """Check if email already exists"""
        user = User.query.filter_by(email=email.data.lower()).first()
        if user:
            raise ValidationError('Este email já está registado')
