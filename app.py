import os, json, uuid, hashlib, datetime, secrets, requests
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy
import google.generativeai as genai

app = Flask(__name__, static_folder='static', static_url_path='')
CORS(app, supports_credentials=True, origins=["*"])

# Настройки БД и секретов
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.secret_key = os.environ.get('SECRET_KEY', secrets.token_hex(16))
db = SQLAlchemy(app)

# === МОДЕЛИ БАЗЫ ДАННЫХ ===
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)
    is_active = db.Column(db.Boolean, default=True)
    is_admin = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    api_token = db.Column(db.String(100), unique=True, default=lambda: secrets.token_urlsafe(32))

class Website(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    url = db.Column(db.String(200), unique=True, nullable=False)
    api_key = db.Column(db.String(50), unique=True, nullable=False)
    owner_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    status = db.Column(db.String(20), default='pending')
    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)

class Chat(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    website_id = db.Column(db.Integer, db.ForeignKey('website.id'))
    visitor_id = db.Column(db.String(50))
    status = db.Column(db.String(20), default='waiting')
    operator_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)

class Message(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    chat_id = db.Column(db.Integer, db.ForeignKey('chat.id'))
    sender = db.Column(db.String(20)) # visitor, operator, admin, ai
    text = db.Column(db.Text)
    timestamp = db.Column(db.DateTime, default=datetime.datetime.utcnow)

class AIManager(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    name = db.Column(db.String(100))
    behavior = db.Column(db.Text)
    forbidden = db.Column(db.Text)
    knowledge_base = db.Column(db.Text) # ссылки на файлы или текст
    is_active = db.Column(db.Boolean, default=False)

class TelegramBot(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    bot_token = db.Column(db.String(200), unique=True)
    is_active = db.Column(db.Boolean, default=False)

class AdminMessage(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    text = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)

# === ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ===
def hash_pwd(p): return hashlib.sha256((p + "kristina_salt_2026").encode()).hexdigest()
def get_token(): return request.headers.get('Authorization', '').replace('Bearer ', '')

def token_required(f):
    def wrapper(*args, **kwargs):
        token = get_token()
        user = User.query.filter_by(api_token=token).first()
        if not user or not user.is_active:
            return jsonify({"error": "Unauthorized"}), 401
        request.current_user = user
        return f(*args, **kwargs)
    wrapper.__name__ = f.__name__
    return wrapper

def admin_required(f):
    def wrapper(*args, **kwargs):
        token = get_token()
        user = User.query.filter_by(api_token=token, is_admin=True).first()
        if not user: return jsonify({"error": "Admin only"}), 403
        request.current_user = user
        return f(*args, **kwargs)
    wrapper.__name__ = f.__name__
    return wrapper

# === АВТОРИЗАЦИЯ ===
@app.route('/api/login', methods=['POST'])
def login():
    d = request.json
    user = User.query.filter_by(username=d.get('username'), password_hash=hash_pwd(d.get('password'))).first()
    if user and user.is_active:
        return jsonify({"ok": True, "token": user.api_token, "is_admin": user.is_admin})
    return jsonify({"error": "Неверные данные или аккаунт отключен"}), 401

@app.route('/api/register', methods=['POST'])
def register():
    d = request.json
    if User.query.filter_by(username=d.get('username')).first():
        return jsonify({"error": "Пользователь существует"}), 409
    u = User(username=d['username'], password_hash=hash_pwd(d['password']))
    db.session.add(u)
    db.session.commit()
    return jsonify({"ok": True, "token": u.api_token})

# === САЙТЫ И ЧАТЫ ===
@app.route('/api/sites', methods=['GET'])
@token_required
def get_sites():
    u = request.current_user
    sites = Website.query.filter_by(owner_id=u.id).all() if not u.is_admin else Website.query.all()
    return jsonify([{"id":s.id, "url":s.url, "api_key":s.api_key, "status":s.status, "owner":s.owner_id} for s in sites])

@app.route('/api/sites', methods=['POST'])
@token_required
def add_site():
    url = request.json.get('url')
    key = f"site_{uuid.uuid4().hex[:8]}"
    db.session.add(Website(url=url, api_key=key, owner_id=request.current_user.id))
    db.session.commit()
    return jsonify({"ok": True})

@app.route('/api/sites/<int:site_id>/approve', methods=['POST'])
@admin_required
def approve_site():
    site = Website.query.get(site_id)
    if site:
        site.status = 'active'
        db.session.commit()
    return jsonify({"ok": True})

@app.route('/api/chats', methods=['GET'])
@token_required
def get_chats():
    u = request.current_user
    if u.is_admin:
        chats = Chat.query.order_by(Chat.created_at.desc()).all()
    else:
        chats = Chat.query.join(Website).filter(Website.owner_id==u.id).order_by(Chat.created_at.desc()).all()
    res = []
    for c in chats:
        w = Website.query.get(c.website_id)
        res.append({"id":c.id, "site":w.url if w else "Unknown", "status":c.status, "time":c.created_at.isoformat()})
    return jsonify(res)

@app.route('/api/messages/<int:chat_id>', methods=['GET'])
@token_required
def get_messages(chat_id):
    msgs = Message.query.filter_by(chat_id=chat_id).order_by(Message.timestamp).all()
    return jsonify([{"sender":m.sender, "text":m.text, "time":m.timestamp.isoformat()} for m in msgs])

@app.route('/api/send', methods=['POST'])
@token_required
def send_message():
    d = request.json
    db.session.add(Message(chat_id=d['chat_id'], sender=d.get('sender','operator'), text=d['text']))
    db.session.commit()
    return jsonify({"ok": True})

# === АДМИН-ПАНЕЛЬ: ПОЛЬЗОВАТЕЛИ ===
@app.route('/api/admin/users', methods=['GET'])
@admin_required
def admin_users():
    users = User.query.order_by(User.created_at.desc()).all()
    return jsonify([{"id":u.id, "username":u.username, "created_at":u.created_at.isoformat(), "is_active":u.is_active, "is_admin":u.is_admin} for u in users])

@app.route('/api/admin/toggle_user', methods=['POST'])
@admin_required
def toggle_user():
    u = User.query.get(request.json.get('user_id'))
    if u:
        u.is_active = not u.is_active
        db.session.commit()
    return jsonify({"ok": True})

@app.route('/api/admin/message', methods=['POST'])
@admin_required
def admin_message():
    d = request.json
    db.session.add(AdminMessage(user_id=d['user_id'], text=d['text']))
    # Добавляем как системное сообщение во все активные чаты пользователя
    user_sites = Website.query.filter_by(owner_id=d['user_id']).all()
    for site in user_sites:
        chats = Chat.query.filter_by(website_id=site.id).all()
        for chat in chats:
            db.session.add(Message(chat_id=chat.id, sender='admin', text=f"📢 Сообщение от админа: {d['text']}"))
    db.session.commit()
    return jsonify({"ok": True})

# === AI МЕНЕДЖЕР ===
@app.route('/api/ai/setup', methods=['POST'])
@token_required
def setup_ai():
    d = request.json
    ai = AIManager.query.filter_by(user_id=request.current_user.id).first()
    if ai:
        ai.name, ai.behavior, ai.forbidden, ai.knowledge_base, ai.is_active = d['name'], d['behavior'], d['forbidden'], d.get('kb',''), d.get('active', False)
    else:
        ai = AIManager(user_id=request.current_user.id, **d)
        db.session.add(ai)
    db.session.commit()
    return jsonify({"ok": True})

@app.route('/api/ai/respond', methods=['POST'])
@token_required
def ai_respond():
    # Заглушка для Gemini. Подставь свой API ключ в переменную окружения GEMINI_KEY
    d = request.json
    ai = AIManager.query.filter_by(user_id=request.current_user.id, is_active=True).first()
    if not ai: return jsonify({"error": "AI не активен"}), 400
    
    # Здесь будет реальный вызов Gemini
    response_text = f"[AI Ответ на: {d['question']}]" 
    return jsonify({"answer": response_text})

# === TELEGRAM БОТ ===
@app.route('/api/telegram/setup', methods=['POST'])
@token_required
def setup_tg():
    d = request.json
    tb = TelegramBot.query.filter_by(user_id=request.current_user.id).first()
    if tb:
        tb.bot_token, tb.is_active = d['token'], d.get('active', False)
    else:
        tb = TelegramBot(user_id=request.current_user.id, **d)
        db.session.add(tb)
    db.session.commit()
    return jsonify({"ok": True})

# === ИНИЦИАЛИЗАЦИЯ БД ===
with app.app_context():
    db.create_all()
    if not User.query.filter_by(username='Kristina').first():
        admin = User(username='Kristina', password_hash=hash_pwd('1234'), is_admin=True)
        db.session.add(admin)
        db.session.commit()

# Раздача статики (веб-версия)
@app.route('/', defaults={'path': 'index.html'})
@app.route('/<path:path>')
def serve_static(path):
    return send_from_directory(app.static_folder, path)

# === ЗАПУСК ПРИЛОЖЕНИЯ (ВАЖНО ДЛЯ RENDER) ===
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port, debug=True)