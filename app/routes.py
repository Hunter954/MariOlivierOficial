from functools import wraps
import json
import os
from pathlib import Path
from flask import render_template, redirect, url_for, flash, request, jsonify, current_app, send_from_directory
from flask_login import current_user, login_user, logout_user, login_required
from werkzeug.security import check_password_hash
from werkzeug.utils import secure_filename
from . import db
from .forms import LoginForm, RegisterForm, CommentForm, ProfileForm, EpisodeForm
from .models import User, Season, Episode, VideoProgress, Comment, BonusItem, ExtraItem, Notification, Subscription
from .utils import format_seconds_to_progress


ALLOWED_IMAGE_EXTENSIONS = {'.png', '.jpg', '.jpeg', '.webp', '.svg'}
ALLOWED_VIDEO_EXTENSIONS = {'.mp4', '.mov', '.m4v', '.webm'}


def admin_required(view_func):
    @wraps(view_func)
    def wrapper(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_admin():
            flash('Acesso restrito ao admin.', 'error')
            return redirect(url_for('home'))
        return view_func(*args, **kwargs)
    return wrapper


def get_resume_data(user, episode):
    progress = None
    progress_percent = 0
    if user.is_authenticated:
        progress = VideoProgress.query.filter_by(user_id=user.id, episode_id=episode.id).first()
        if progress:
            progress_percent = format_seconds_to_progress(progress.seconds_watched, episode.duration_minutes)
    return progress, progress_percent


def slugify(value: str) -> str:
    base = secure_filename((value or '').strip().lower().replace(' ', '-'))
    return base or 'episodio'


def _settings_path() -> Path:
    return Path(current_app.config['UPLOAD_FOLDER']) / 'settings.json'


def load_app_settings() -> dict:
    path = _settings_path()
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding='utf-8'))
    except Exception:
        return {}


def save_app_settings(data: dict) -> None:
    path = _settings_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')


def save_uploaded_file(file_storage, subfolder: str, allowed_extensions: set[str], preferred_name: str | None = None):
    if not file_storage or not file_storage.filename:
        return None

    original_name = secure_filename(file_storage.filename)
    ext = Path(original_name).suffix.lower()
    if ext not in allowed_extensions:
        return None

    target_dir = Path(current_app.config['UPLOAD_FOLDER']) / subfolder
    target_dir.mkdir(parents=True, exist_ok=True)

    filename = f"{preferred_name}{ext}" if preferred_name else original_name
    file_path = target_dir / filename
    file_storage.save(file_path)

    relative_path = Path(subfolder) / filename
    return url_for('uploaded_file', path=str(relative_path).replace('\\', '/'))


def register_routes(app):
    @app.context_processor
    def inject_shell_data():
        unread_count = 0
        latest_notifications = []
        brand_logo_url = load_app_settings().get('brand_logo_url')
        if current_user.is_authenticated:
            unread_count = Notification.query.filter_by(user_id=current_user.id, is_read=False).count()
            latest_notifications = Notification.query.filter_by(user_id=current_user.id).order_by(Notification.created_at.desc()).limit(5).all()
        return {
            'shell_notifications': latest_notifications,
            'unread_notifications_count': unread_count,
            'brand_logo_url': brand_logo_url,
        }

    @app.route('/uploads/<path:path>')
    def uploaded_file(path):
        return send_from_directory(current_app.config['UPLOAD_FOLDER'], path)

    @app.route('/')
    def home():
        current_season = Season.query.filter_by(status='current').order_by(Season.order_index.asc()).first()
        hero_episode = Episode.query.join(Season).filter(Season.id == current_season.id, Episode.status == 'published').order_by(Episode.order_index.asc()).first() if current_season else None
        upcoming_episodes = Episode.query.filter_by(status='scheduled').order_by(Episode.order_index.asc()).limit(5).all()
        upcoming_seasons = Season.query.filter(Season.status != 'current').order_by(Season.order_index.asc()).limit(5).all()
        bonus_items = BonusItem.query.order_by(BonusItem.featured.desc(), BonusItem.created_at.desc()).limit(4).all()
        extra_items = ExtraItem.query.order_by(ExtraItem.created_at.desc()).limit(4).all()

        progress, progress_percent = (None, 0)
        if hero_episode:
            progress, progress_percent = get_resume_data(current_user, hero_episode)

        return render_template(
            'home.html',
            current_season=current_season,
            hero_episode=hero_episode,
            progress=progress,
            progress_percent=progress_percent,
            upcoming_episodes=upcoming_episodes,
            upcoming_seasons=upcoming_seasons,
            bonus_items=bonus_items,
            extra_items=extra_items,
        )

    @app.route('/login', methods=['GET', 'POST'])
    def login():
        if current_user.is_authenticated:
            return redirect(url_for('home'))
        form = LoginForm()
        if form.validate_on_submit():
            user = User.query.filter_by(email=form.email.data.lower().strip()).first()
            if user and check_password_hash(user.password_hash, form.password.data):
                if user.is_blocked:
                    flash('Seu acesso está bloqueado.', 'error')
                    return redirect(url_for('login'))
                login_user(user, remember=True)
                flash('Login realizado com sucesso.', 'success')
                next_url = request.args.get('next') or url_for('home')
                return redirect(next_url)
            flash('Email ou senha inválidos.', 'error')
        return render_template('auth.html', mode='login', form=form)

    @app.route('/register', methods=['GET', 'POST'])
    def register():
        if current_user.is_authenticated:
            return redirect(url_for('home'))
        form = RegisterForm()
        if form.validate_on_submit():
            exists = User.query.filter_by(email=form.email.data.lower().strip()).first()
            if exists:
                flash('Já existe uma conta com esse email.', 'error')
                return render_template('auth.html', mode='register', form=form)
            user = User(name=form.name.data.strip(), email=form.email.data.lower().strip(), username=form.email.data.split('@')[0])
            user.set_password(form.password.data)
            db.session.add(user)
            db.session.flush()
            subscription = Subscription(user=user, plan_name='Assinatura Premium', status='trial')
            welcome = Notification(user=user, title='Bem-vindo(a)', body='Seu acesso foi criado. Complete seu perfil e aproveite a plataforma.')
            db.session.add_all([subscription, welcome])
            db.session.commit()
            login_user(user, remember=True)
            flash('Conta criada com sucesso.', 'success')
            return redirect(url_for('profile'))
        return render_template('auth.html', mode='register', form=form)

    @app.route('/logout')
    @login_required
    def logout():
        logout_user()
        flash('Você saiu da plataforma.', 'info')
        return redirect(url_for('login'))

    @app.route('/temporadas')
    def seasons_page():
        seasons = Season.query.order_by(Season.order_index.asc()).all()
        return render_template('seasons.html', seasons=seasons)

    @app.route('/temporadas/<slug>')
    def season_detail(slug):
        season = Season.query.filter_by(slug=slug).first_or_404()
        return render_template('season_detail.html', season=season)

    @app.route('/episodio/<slug>', methods=['GET', 'POST'])
    def episode_detail(slug):
        episode = Episode.query.filter_by(slug=slug).first_or_404()
        form = CommentForm()
        if form.validate_on_submit() and current_user.is_authenticated:
            comment = Comment(user=current_user, episode=episode, content=form.content.data.strip())
            db.session.add(comment)
            db.session.commit()
            flash('Comentário publicado.', 'success')
            return redirect(url_for('episode_detail', slug=slug))

        progress, progress_percent = get_resume_data(current_user, episode)
        comments = Comment.query.filter_by(episode_id=episode.id, is_hidden=False).order_by(Comment.created_at.desc()).all()
        next_episode = Episode.query.filter(Episode.season_id == episode.season_id, Episode.order_index > episode.order_index).order_by(Episode.order_index.asc()).first()
        return render_template('episode_detail.html', episode=episode, form=form, progress=progress, progress_percent=progress_percent, comments=comments, next_episode=next_episode)

    @app.route('/bonus')
    def bonus_page():
        items = BonusItem.query.order_by(BonusItem.featured.desc(), BonusItem.created_at.desc()).all()
        return render_template('bonus.html', items=items)

    @app.route('/extras')
    def extras_page():
        items = ExtraItem.query.order_by(ExtraItem.created_at.desc()).all()
        return render_template('extras.html', items=items)

    @app.route('/assinatura')
    @login_required
    def subscription_page():
        return render_template('subscription.html', subscription=current_user.subscription)

    @app.route('/perfil', methods=['GET', 'POST'])
    @login_required
    def profile():
        form = ProfileForm(obj=current_user)
        if form.validate_on_submit():
            current_user.name = form.name.data.strip()
            current_user.username = form.username.data.strip() if form.username.data else current_user.username
            current_user.phone = form.phone.data.strip() if form.phone.data else None
            current_user.birth_date = form.birth_date.data
            current_user.city = form.city.data.strip() if form.city.data else None
            current_user.state = form.state.data.strip() if form.state.data else None
            current_user.avatar_url = form.avatar_url.data.strip() if form.avatar_url.data else current_user.avatar_url
            db.session.commit()
            flash('Perfil atualizado.', 'success')
            return redirect(url_for('profile'))
        return render_template('profile.html', form=form)

    @app.route('/notificacoes')
    @login_required
    def notifications_page():
        notifications = Notification.query.filter_by(user_id=current_user.id).order_by(Notification.created_at.desc()).all()
        return render_template('notifications.html', notifications=notifications)

    @app.route('/notificacoes/<int:notification_id>/read', methods=['POST'])
    @login_required
    def notification_read(notification_id):
        notification = Notification.query.filter_by(id=notification_id, user_id=current_user.id).first_or_404()
        notification.is_read = True
        db.session.commit()
        return redirect(request.referrer or url_for('notifications_page'))

    @app.route('/comments/<int:comment_id>/delete', methods=['POST'])
    @login_required
    def delete_comment(comment_id):
        comment = Comment.query.get_or_404(comment_id)
        if comment.user_id != current_user.id and not current_user.is_admin():
            flash('Você não pode remover este comentário.', 'error')
            return redirect(request.referrer or url_for('home'))
        db.session.delete(comment)
        db.session.commit()
        flash('Comentário removido.', 'info')
        return redirect(request.referrer or url_for('home'))

    @app.route('/comments/<int:comment_id>/like', methods=['POST'])
    @login_required
    def like_comment(comment_id):
        comment = Comment.query.get_or_404(comment_id)
        if current_user in comment.liked_by:
            comment.liked_by.remove(current_user)
        else:
            comment.liked_by.append(current_user)
        db.session.commit()
        return redirect(request.referrer or url_for('home'))

    @app.route('/episodio/<int:episode_id>/like', methods=['POST'])
    @login_required
    def like_episode(episode_id):
        episode = Episode.query.get_or_404(episode_id)
        if current_user in episode.liked_by:
            episode.liked_by.remove(current_user)
        else:
            episode.liked_by.append(current_user)
        db.session.commit()
        return redirect(request.referrer or url_for('episode_detail', slug=episode.slug))

    @app.route('/api/progress/<int:episode_id>', methods=['POST'])
    @login_required
    def save_progress(episode_id):
        episode = Episode.query.get_or_404(episode_id)
        payload = request.get_json(silent=True) or {}
        seconds_watched = int(payload.get('seconds_watched', 0))
        completed = bool(payload.get('completed', False))
        progress = VideoProgress.query.filter_by(user_id=current_user.id, episode_id=episode.id).first()
        if not progress:
            progress = VideoProgress(user=current_user, episode=episode)
            db.session.add(progress)
        progress.seconds_watched = seconds_watched
        progress.completed = completed
        db.session.commit()
        return jsonify({'ok': True, 'progress_percent': format_seconds_to_progress(seconds_watched, episode.duration_minutes)})

    @app.route('/admin')
    @login_required
    @admin_required
    def admin_dashboard():
        metrics = {
            'users': User.query.count(),
            'episodes': Episode.query.count(),
            'comments': Comment.query.count(),
            'published_episodes': Episode.query.filter_by(status='published').count(),
            'active_trials': Subscription.query.filter(Subscription.status.in_(['trial', 'active'])).count(),
        }
        most_watched = (
            db.session.query(Episode, db.func.coalesce(db.func.sum(VideoProgress.seconds_watched), 0).label('watched'))
            .outerjoin(VideoProgress, VideoProgress.episode_id == Episode.id)
            .group_by(Episode.id)
            .order_by(db.text('watched DESC'))
            .limit(5)
            .all()
        )
        users = User.query.order_by(User.created_at.desc()).limit(8).all()
        episodes = Episode.query.order_by(Episode.created_at.desc()).limit(8).all()
        return render_template('admin.html', metrics=metrics, most_watched=most_watched, users=users, episodes=episodes, brand_logo_url=load_app_settings().get('brand_logo_url'))

    @app.route('/admin/logo', methods=['POST'])
    @login_required
    @admin_required
    def admin_logo_upload():
        logo_url = save_uploaded_file(request.files.get('brand_logo'), 'branding', ALLOWED_IMAGE_EXTENSIONS, preferred_name='brand-logo')
        if not logo_url:
            flash('Envie uma logomarca válida em PNG, JPG, WEBP ou SVG.', 'error')
            return redirect(url_for('admin_dashboard'))

        settings = load_app_settings()
        settings['brand_logo_url'] = logo_url
        save_app_settings(settings)
        flash('Logomarca atualizada com sucesso.', 'success')
        return redirect(url_for('admin_dashboard'))

    @app.route('/admin/users/<int:user_id>/toggle-block', methods=['POST'])
    @login_required
    @admin_required
    def toggle_user_block(user_id):
        user = User.query.get_or_404(user_id)
        if user.id == current_user.id:
            flash('Você não pode bloquear seu próprio usuário admin.', 'error')
            return redirect(url_for('admin_dashboard'))
        user.is_blocked = not user.is_blocked
        db.session.commit()
        flash('Status do usuário atualizado.', 'success')
        return redirect(url_for('admin_dashboard'))

    @app.route('/admin/episodes/new', methods=['GET', 'POST'])
    @login_required
    @admin_required
    def admin_episode_new():
        form = EpisodeForm()
        seasons = Season.query.order_by(Season.order_index.asc()).all()
        if request.method == 'POST' and form.validate_on_submit():
            season_id = int(request.form.get('season_id'))
            season = Season.query.get_or_404(season_id)

            thumbnail_url = form.thumbnail_url.data.strip() if form.thumbnail_url.data else None
            video_url = form.video_url.data.strip() if form.video_url.data else None

            uploaded_thumb = save_uploaded_file(request.files.get('thumbnail_file'), 'episodes/thumbnails', ALLOWED_IMAGE_EXTENSIONS)
            uploaded_video = save_uploaded_file(request.files.get('video_file'), 'episodes/videos', ALLOWED_VIDEO_EXTENSIONS)

            if uploaded_thumb:
                thumbnail_url = uploaded_thumb
            if uploaded_video:
                video_url = uploaded_video

            episode = Episode(
                season=season,
                title=form.title.data.strip(),
                slug=slugify(form.title.data),
                description=form.description.data,
                thumbnail_url=thumbnail_url,
                video_url=video_url,
                duration_minutes=int(form.duration_minutes.data or 0),
                status=form.status.data,
                premiere_label=form.premiere_label.data,
                order_index=(len(season.episodes) + 1),
            )
            db.session.add(episode)
            db.session.commit()
            flash('Episódio criado.', 'success')
            return redirect(url_for('admin_dashboard'))
        return render_template('admin_episode_form.html', form=form, seasons=seasons)
