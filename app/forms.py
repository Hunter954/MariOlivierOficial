from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField, TextAreaField, DateField, SelectField
from wtforms.validators import DataRequired, Email, EqualTo, Length, Optional


class LoginForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Senha', validators=[DataRequired(), Length(min=6)])
    submit = SubmitField('Entrar')


class RegisterForm(FlaskForm):
    name = StringField('Nome', validators=[DataRequired(), Length(min=2, max=120)])
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Senha', validators=[DataRequired(), Length(min=6)])
    confirm_password = PasswordField('Confirmar senha', validators=[DataRequired(), EqualTo('password')])
    submit = SubmitField('Criar conta')


class CommentForm(FlaskForm):
    content = TextAreaField('Comentário', validators=[DataRequired(), Length(min=2, max=500)])
    submit = SubmitField('Comentar')


class ProfileForm(FlaskForm):
    name = StringField('Nome', validators=[DataRequired(), Length(min=2, max=120)])
    username = StringField('Username', validators=[Optional(), Length(max=80)])
    phone = StringField('Telefone', validators=[Optional(), Length(max=30)])
    birth_date = DateField('Data de nascimento', validators=[Optional()])
    city = StringField('Cidade', validators=[Optional(), Length(max=120)])
    state = StringField('Estado', validators=[Optional(), Length(max=120)])
    submit = SubmitField('Salvar perfil')


class EpisodeForm(FlaskForm):
    title = StringField('Título', validators=[DataRequired(), Length(max=140)])
    description = TextAreaField('Descrição', validators=[Optional()])
    thumbnail_url = StringField('Thumb 9:16', validators=[Optional(), Length(max=255)])
    video_url = StringField('URL do vídeo', validators=[Optional(), Length(max=255)])
    duration_minutes = StringField('Duração (min)', validators=[Optional()])
    status = SelectField('Status', choices=[('published', 'Publicado'), ('scheduled', 'Agendado')])
    premiere_label = StringField('Texto de estreia', validators=[Optional(), Length(max=80)])
    submit = SubmitField('Salvar episódio')
