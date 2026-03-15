from __future__ import annotations

import os
from datetime import datetime, date
from werkzeug.security import generate_password_hash
from flask_login import UserMixin
from sqlalchemy import func
from . import db


episode_likes = db.Table(
    'episode_likes',
    db.Column('user_id', db.Integer, db.ForeignKey('user.id'), primary_key=True),
    db.Column('episode_id', db.Integer, db.ForeignKey('episode.id'), primary_key=True),
)

comment_likes = db.Table(
    'comment_likes',
    db.Column('user_id', db.Integer, db.ForeignKey('user.id'), primary_key=True),
    db.Column('comment_id', db.Integer, db.ForeignKey('comment.id'), primary_key=True),
)


class TimestampMixin:
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class User(UserMixin, TimestampMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    username = db.Column(db.String(80), unique=True)
    email = db.Column(db.String(255), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), default='viewer')
    avatar_url = db.Column(db.String(255), default='https://placehold.co/160x160/png')
    phone = db.Column(db.String(30))
    birth_date = db.Column(db.Date)
    city = db.Column(db.String(120))
    state = db.Column(db.String(120))
    is_blocked = db.Column(db.Boolean, default=False)

    comments = db.relationship('Comment', back_populates='user', cascade='all, delete-orphan')
    progresses = db.relationship('VideoProgress', back_populates='user', cascade='all, delete-orphan')
    notifications = db.relationship('Notification', back_populates='user', cascade='all, delete-orphan')
    subscription = db.relationship('Subscription', back_populates='user', uselist=False, cascade='all, delete-orphan')

    def set_password(self, password: str):
        self.password_hash = generate_password_hash(password)

    def is_admin(self):
        return self.role == 'admin'


class Season(TimestampMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(120), nullable=False)
    slug = db.Column(db.String(120), unique=True, nullable=False)
    description = db.Column(db.Text)
    teaser = db.Column(db.Text)
    poster_url = db.Column(db.String(255))
    status = db.Column(db.String(30), default='current')
    release_label = db.Column(db.String(80))
    order_index = db.Column(db.Integer, default=0)

    episodes = db.relationship('Episode', back_populates='season', cascade='all, delete-orphan', order_by='Episode.order_index')


class Episode(TimestampMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    season_id = db.Column(db.Integer, db.ForeignKey('season.id'), nullable=False)
    title = db.Column(db.String(140), nullable=False)
    slug = db.Column(db.String(140), unique=True, nullable=False)
    description = db.Column(db.Text)
    thumbnail_url = db.Column(db.String(255))
    video_url = db.Column(db.String(255))
    duration_minutes = db.Column(db.Integer, default=0)
    status = db.Column(db.String(30), default='published')
    premiere_label = db.Column(db.String(80))
    order_index = db.Column(db.Integer, default=0)

    season = db.relationship('Season', back_populates='episodes')
    comments = db.relationship('Comment', back_populates='episode', cascade='all, delete-orphan')
    progresses = db.relationship('VideoProgress', back_populates='episode', cascade='all, delete-orphan')
    liked_by = db.relationship('User', secondary=episode_likes, backref=db.backref('liked_episodes', lazy='dynamic'))

    def like_count(self):
        return len(self.liked_by)


class VideoProgress(TimestampMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    episode_id = db.Column(db.Integer, db.ForeignKey('episode.id'), nullable=False)
    seconds_watched = db.Column(db.Integer, default=0)
    completed = db.Column(db.Boolean, default=False)

    user = db.relationship('User', back_populates='progresses')
    episode = db.relationship('Episode', back_populates='progresses')


class Comment(TimestampMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    episode_id = db.Column(db.Integer, db.ForeignKey('episode.id'), nullable=False)
    content = db.Column(db.Text, nullable=False)
    is_hidden = db.Column(db.Boolean, default=False)

    user = db.relationship('User', back_populates='comments')
    episode = db.relationship('Episode', back_populates='comments')
    liked_by = db.relationship('User', secondary=comment_likes, backref=db.backref('liked_comments', lazy='dynamic'))

    def like_count(self):
        return len(self.liked_by)


class BonusItem(TimestampMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(140), nullable=False)
    description = db.Column(db.Text)
    image_url = db.Column(db.String(255))
    cta_label = db.Column(db.String(40), default='Saiba mais')
    cta_url = db.Column(db.String(255), default='#')
    featured = db.Column(db.Boolean, default=False)


class ExtraItem(TimestampMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(140), nullable=False)
    description = db.Column(db.Text)
    image_url = db.Column(db.String(255))
    category = db.Column(db.String(60), default='Bastidores')


class Notification(TimestampMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    title = db.Column(db.String(140), nullable=False)
    body = db.Column(db.Text)
    is_read = db.Column(db.Boolean, default=False)

    user = db.relationship('User', back_populates='notifications')


class Subscription(TimestampMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False, unique=True)
    plan_name = db.Column(db.String(80), default='Premium')
    status = db.Column(db.String(30), default='trial')
    renews_on = db.Column(db.Date)
    checkout_url = db.Column(db.String(255), default='#')

    user = db.relationship('User', back_populates='subscription')


def seed_demo_data():
    if User.query.first():
        return

    admin_email = os.getenv('ADMIN_EMAIL', 'admin@mariolivier.com')
    admin_password = os.getenv('ADMIN_PASSWORD', '12345678')

    admin = User(
        name='Mari Olivier Admin',
        username='mariadmin',
        email=admin_email,
        role='admin',
        avatar_url='https://placehold.co/160x160/png?text=MO',
        city='São Paulo',
        state='SP',
    )
    admin.set_password(admin_password)

    viewer = User(
        name='Fã Premium',
        username='fapremium',
        email='fan@example.com',
        role='viewer',
        avatar_url='https://placehold.co/160x160/png?text=Fan',
        city='Curitiba',
        state='PR',
    )
    viewer.set_password('12345678')

    current_season = Season(
        title='Temporada 1',
        slug='temporada-1',
        description='O começo do reality com rotina, bastidores, emoção e encontros especiais.',
        teaser='Conteúdo cinematográfico com narrativa íntima e episódios verticais premium.',
        poster_url='https://placehold.co/640x960/5a0008/f2b24f?text=Temporada+1',
        status='current',
        release_label='No ar agora',
        order_index=1,
    )
    upcoming_one = Season(
        title='Temporada 2',
        slug='temporada-2',
        description='Nova fase com viagens, surpresas e convidados.',
        teaser='Teasers e prévias exclusivas para assinantes.',
        poster_url='https://placehold.co/640x960/430007/f2b24f?text=Temporada+2',
        status='upcoming',
        release_label='Em breve',
        order_index=2,
    )
    upcoming_two = Season(
        title='Temporada 3',
        slug='temporada-3',
        description='Bastidores ainda mais próximos e experiências inéditas.',
        teaser='Produção expandida, colaborações e ativações especiais.',
        poster_url='https://placehold.co/640x960/3d0007/f2b24f?text=Temporada+3',
        status='upcoming',
        release_label='Planejada',
        order_index=3,
    )

    db.session.add_all([admin, viewer, current_season, upcoming_one, upcoming_two])
    db.session.flush()

    episodes = [
        Episode(
            season=current_season,
            title='O Presente',
            slug='o-presente',
            description='Abertura oficial do reality com clima premium, tensão e apresentação do universo da temporada.',
            thumbnail_url='https://placehold.co/540x960/6e000a/f2b24f?text=Ep+1',
            video_url='https://www.w3schools.com/html/mov_bbb.mp4',
            duration_minutes=43,
            status='published',
            premiere_label='Disponível agora',
            order_index=1,
        ),
        Episode(
            season=current_season,
            title='Bastidores do Caos',
            slug='bastidores-do-caos',
            description='A pressão dos bastidores aparece mais do que nunca.',
            thumbnail_url='https://placehold.co/540x960/650008/f2b24f?text=Ep+2',
            video_url='https://www.w3schools.com/html/movie.mp4',
            duration_minutes=38,
            status='scheduled',
            premiere_label='Estreia sexta, 20h',
            order_index=2,
        ),
        Episode(
            season=current_season,
            title='A Reviravolta',
            slug='a-reviravolta',
            description='Um episódio para mudar o ritmo da história.',
            thumbnail_url='https://placehold.co/540x960/5b0008/f2b24f?text=Ep+3',
            video_url='https://www.w3schools.com/html/mov_bbb.mp4',
            duration_minutes=41,
            status='scheduled',
            premiere_label='Semana que vem',
            order_index=3,
        ),
        Episode(
            season=current_season,
            title='Noite de Lançamento',
            slug='noite-de-lancamento',
            description='Expectativas, convidados e clima de estreia.',
            thumbnail_url='https://placehold.co/540x960/540007/f2b24f?text=Ep+4',
            video_url='https://www.w3schools.com/html/movie.mp4',
            duration_minutes=36,
            status='scheduled',
            premiere_label='Em produção',
            order_index=4,
        ),
    ]
    db.session.add_all(episodes)

    progress = VideoProgress(user=viewer, episode=episodes[0], seconds_watched=1800, completed=False)

    comments = [
        Comment(user=viewer, episode=episodes[0], content='A estética ficou surreal. Quero o próximo episódio logo.'),
        Comment(user=admin, episode=episodes[0], content='Obrigada por acompanhar. Vem muita surpresa por aí.'),
    ]

    notifications = [
        Notification(user=viewer, title='Novo episódio liberado', body='Temporada 1 • Episódio 1 já está disponível.'),
        Notification(user=viewer, title='Novo bônus publicado', body='Uma nova experiência exclusiva foi adicionada à área de bônus.'),
        Notification(user=viewer, title='Resposta em comentário', body='Mari respondeu um comentário seu.'),
    ]

    bonus_items = [
        BonusItem(
            title='Visita especial na sua loja',
            description='Ativação presencial com presença da influencer para ações, gravações e conteúdo.',
            image_url='https://placehold.co/800x1200/6b0009/f2b24f?text=Visita+Especial',
            cta_label='Tenho interesse',
            cta_url='#',
            featured=True,
        ),
        BonusItem(
            title='Publi exclusiva',
            description='Campanha com storytelling no universo do reality.',
            image_url='https://placehold.co/800x1200/5b0008/f2b24f?text=Publi',
            cta_label='Saiba mais',
            cta_url='#',
        ),
        BonusItem(
            title='Produto digital premium',
            description='Pack com conteúdos e materiais inéditos para fãs e marcas.',
            image_url='https://placehold.co/800x1200/4c0007/f2b24f?text=Produto+Digital',
            cta_label='Comprar',
            cta_url='#',
        ),
    ]

    extra_items = [
        ExtraItem(
            title='Making of da abertura',
            description='Captação, direção e preparação dos takes principais.',
            image_url='https://placehold.co/800x1200/650008/f2b24f?text=Making+Of',
            category='Making of',
        ),
        ExtraItem(
            title='Cenas exclusivas',
            description='Momentos que não entraram no corte final.',
            image_url='https://placehold.co/800x1200/530007/f2b24f?text=Cenas',
            category='Cena exclusiva',
        ),
        ExtraItem(
            title='Teaser vertical',
            description='Versão pensada para social e notificações in-app.',
            image_url='https://placehold.co/800x1200/410006/f2b24f?text=Teaser',
            category='Teaser',
        ),
    ]

    subscription = Subscription(user=viewer, plan_name='Assinatura Premium', status='trial', renews_on=date(2026, 4, 15), checkout_url='#')

    db.session.add(progress)
    db.session.add_all(comments + notifications + bonus_items + extra_items + [subscription])
    db.session.commit()
