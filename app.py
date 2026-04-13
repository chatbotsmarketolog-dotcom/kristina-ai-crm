import os, json, uuid, hashlib, datetime, secrets, requests
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import text
from openai import OpenAI

app = Flask(__name__, static_folder='static', static_url_path='')
CORS(app, supports_credentials=True, origins=["*"])

app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.secret_key = os.environ.get('SECRET_KEY', secrets.token_hex(16))
db = SQLAlchemy(app)

# OpenAI клиент
client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

# === МОДЕЛИ БАЗЫ ДАННЫХ ===
class User(db.Model):
    __tablename__ = 'user'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)
    is_active = db.Column(db.Boolean, default=True)
    is_admin = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    api_token = db.Column(db.String(100), unique=True, default=lambda: secrets.token_urlsafe(32))
    telegram_chat_id = db.Column(db.String(100))

class Website(db.Model):
    __tablename__ = 'website'
    id = db.Column(db.Integer, primary_key=True)
    url = db.Column(db.String(200), unique=True, nullable=False)
    api_key = db.Column(db.String(50), unique=True, nullable=False)
    owner_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    status = db.Column(db.String(20), default='pending')
    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    is_deleted = db.Column(db.Boolean, default=False)
    deleted_at = db.Column(db.DateTime, nullable=True)

class Chat(db.Model):
    __tablename__ = 'chat'
    id = db.Column(db.Integer, primary_key=True)
    website_id = db.Column(db.Integer, db.ForeignKey('website.id'))
    visitor_id = db.Column(db.String(50))
    status = db.Column(db.String(20), default='waiting')
    operator_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)

class Message(db.Model):
    __tablename__ = 'message'
    id = db.Column(db.Integer, primary_key=True)
    chat_id = db.Column(db.Integer, db.ForeignKey('chat.id'))
    sender = db.Column(db.String(20))
    text = db.Column(db.Text)
    timestamp = db.Column(db.DateTime, default=datetime.datetime.utcnow)

class AIManager(db.Model):
    __tablename__ = 'aimanager'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    name = db.Column(db.String(100), default='AI Assistant')
    behavior = db.Column(db.Text, default='Ты полезный помощник')
    forbidden = db.Column(db.Text, default='')
    knowledge_base = db.Column(db.Text, default='')
    is_active_web = db.Column(db.Boolean, default=False)
    is_active_telegram = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)

class TelegramBot(db.Model):
    __tablename__ = 'telegrambot'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    bot_token = db.Column(db.String(200), unique=True)
    is_active = db.Column(db.Boolean, default=False)

class AdminMessage(db.Model):
    __tablename__ = 'adminmessage'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    text = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)

def send_telegram_notification(bot_token, chat_id, message):
    try:
        if not bot_token or not chat_id: return False
        url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
        data = {"chat_id": chat_id, "text": message, "parse_mode": "HTML"}
        response = requests.post(url, json=data, timeout=5)
        return response.status_code == 200
    except Exception as e:
        print(f"Telegram error: {e}")
        return False

def hash_pwd(p): 
    return hashlib.sha256((p + "kristina_salt_2026").encode()).hexdigest()

def get_token(): 
    return request.headers.get('Authorization', '').replace('Bearer ', '')

def token_required(f):
    def wrapper(*args, **kwargs):
        token = get_token()
        user = User.query.filter_by(api_token=token).first()
        if not user or not user.is_active: return jsonify({"error": "Unauthorized"}), 401
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

def add_missing_columns():
    with app.app_context():
        try:
            db.session.execute(text('ALTER TABLE "user" ADD COLUMN IF NOT EXISTS telegram_chat_id VARCHAR(100)'))
            db.session.execute(text('ALTER TABLE website ADD COLUMN IF NOT EXISTS is_deleted BOOLEAN DEFAULT FALSE'))
            db.session.execute(text('ALTER TABLE website ADD COLUMN IF NOT EXISTS deleted_at TIMESTAMP'))
            db.session.execute(text('ALTER TABLE aimanager ADD COLUMN IF NOT EXISTS is_active_web BOOLEAN DEFAULT FALSE'))
            db.session.execute(text('ALTER TABLE aimanager ADD COLUMN IF NOT EXISTS is_active_telegram BOOLEAN DEFAULT FALSE'))
            db.session.commit()
            print("✅ Миграции применены")
        except Exception as e:
            print(f"⚠️ Ошибка миграции: {e}")
            db.session.rollback()

# === AI ФУНКЦИЯ ===
def generate_ai_response(user_message, ai_settings, conversation_history=[]):
    try:
        system_prompt = f"""Ты {ai_settings.name} - AI помощник.

ХАРАКТЕР И ПОВЕДЕНИЕ:
{ai_settings.behavior}

БАЗА ЗНАНИЙ:
{ai_settings.knowledge_base}

ЗАПРЕЩЁННЫЕ ТЕМЫ:
{ai_settings.forbidden if ai_settings.forbidden else 'Нет запретов'}

Отвечай на русском языке. Будь полезен и дружелюбен."""

        messages = [{"role": "system", "content": system_prompt}]
        messages.extend(conversation_history[-10:])
        messages.append({"role": "user", "content": user_message})

        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=messages,
            max_tokens=500,
            temperature=0.7
        )
        
        return response.choices[0].message.content
    except Exception as e:
        print(f"OpenAI error: {e}")
        return "Извините, произошла ошибка (код AI_01). Попробуйте позже."

# === АВТОРИЗАЦИЯ ===
@app.route('/api/login', methods=['POST'])
def login():
    d = request.json
    username = d.get('username', '').strip()
    password = d.get('password', '')
    
    user = User.query.filter_by(username=username).first()
    if not user:
        return jsonify({"error": "Неверные данные"}), 401
    if not user.is_active:
        return jsonify({"error": "Аккаунт отключен"}), 401
    if user.password_hash != hash_pwd(password):
        return jsonify({"error": "Неверные данные"}), 401
        
    return jsonify({"ok": True, "token": user.api_token, "is_admin": user.is_admin, "username": user.username})

@app.route('/api/register', methods=['POST'])
def register():
    d = request.json
    username = d.get('username', '').strip()
    password = d.get('password', '')
    if not username or len(password) < 4:
        return jsonify({"error": "Логин мин. 2 символа, пароль мин. 4"}), 400
    if User.query.filter_by(username=username).first():
        return jsonify({"error": "Пользователь существует"}), 409
    u = User(username=username, password_hash=hash_pwd(password))
    db.session.add(u); db.session.commit()
    return jsonify({"ok": True, "token": u.api_token, "username": u.username})

# === САЙТЫ ===
@app.route('/api/sites', methods=['GET'])
@token_required
def get_sites():
    u = request.current_user
    sites = Website.query.filter_by(owner_id=u.id, is_deleted=False).all() if not u.is_admin else Website.query.filter_by(is_deleted=False).all()
    return jsonify([{"id":s.id, "url":s.url, "api_key":s.api_key, "status":s.status, "owner":s.owner_id} for s in sites])

@app.route('/api/sites', methods=['POST'])
@token_required
def add_site():
    url = request.json.get('url')
    key = f"site_{uuid.uuid4().hex[:8]}"
    site = Website(url=url, api_key=key, owner_id=request.current_user.id)
    db.session.add(site); db.session.commit()
    return jsonify({"ok": True})

@app.route('/api/sites/<int:site_id>/approve', methods=['POST'])
@admin_required
def approve_site():
    site = Website.query.get(site_id)
    if site and not site.is_deleted:
        site.status = 'active'; db.session.commit()
    return jsonify({"ok": True})

@app.route('/api/sites/<int:site_id>/delete', methods=['POST'])
@token_required
def delete_site():
    site = Website.query.get(site_id)
    if not site or site.owner_id != request.current_user.id: return jsonify({"error": "Не найдено"}), 404
    site.is_deleted = True; site.deleted_at = datetime.datetime.utcnow(); db.session.commit()
    return jsonify({"ok": True})

# === ЧАТЫ ===
@app.route('/api/chats', methods=['GET'])
@token_required
def get_chats():
    u = request.current_user
    chats = Chat.query.join(Website).filter(Website.owner_id==u.id, Website.is_deleted==False).order_by(Chat.created_at.desc()).all()
    return jsonify([{"id":c.id, "site":Website.query.get(c.website_id).url if Website.query.get(c.website_id) else "Unknown", "status":c.status, "time":c.created_at.isoformat()} for c in chats])

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

# === AI MANAGER ===
@app.route('/api/ai/setup', methods=['POST'])
@token_required
def setup_ai():
    d = request.json
    ai = AIManager.query.filter_by(user_id=request.current_user.id).first()
    if ai:
        ai.name = d.get('name', ai.name)
        ai.behavior = d.get('behavior', ai.behavior)
        ai.forbidden = d.get('forbidden', ai.forbidden)
        ai.knowledge_base = d.get('knowledge_base', ai.knowledge_base)
        ai.is_active_web = d.get('is_active_web', ai.is_active_web)
        ai.is_active_telegram = d.get('is_active_telegram', ai.is_active_telegram)
    else:
        ai = AIManager(
            user_id=request.current_user.id,
            name=d.get('name', 'AI Assistant'),
            behavior=d.get('behavior', ''),
            forbidden=d.get('forbidden', ''),
            knowledge_base=d.get('knowledge_base', ''),
            is_active_web=d.get('is_active_web', False),
            is_active_telegram=d.get('is_active_telegram', False)
        )
        db.session.add(ai)
    db.session.commit()
    return jsonify({"ok": True})

@app.route('/api/ai/get', methods=['GET'])
@token_required
def get_ai():
    ai = AIManager.query.filter_by(user_id=request.current_user.id).first()
    if ai:
        return jsonify({
            "name": ai.name, "behavior": ai.behavior, "forbidden": ai.forbidden,
            "knowledge_base": ai.knowledge_base, "is_active_web": ai.is_active_web, "is_active_telegram": ai.is_active_telegram
        })
    return jsonify({})

@app.route('/api/ai/respond', methods=['POST'])
@token_required
def ai_respond():
    d = request.json
    ai = AIManager.query.filter_by(user_id=request.current_user.id).first()
    if not ai: return jsonify({"error": "AI не настроен"}), 404
    channel = d.get('channel', 'web')
    if channel == 'web' and not ai.is_active_web: return jsonify({"answer": "AI сейчас неактивен."})
    if channel == 'telegram' and not ai.is_active_telegram: return jsonify({"answer": "AI сейчас неактивен."})
    history = d.get('history', [])
    answer = generate_ai_response(d.get('message', ''), ai, history)
    return jsonify({"answer": answer})

# === АДМИНКА ===
@app.route('/api/admin/users', methods=['GET'])
@admin_required
def admin_users():
    users = User.query.order_by(User.created_at.desc()).all()
    return jsonify([{"id":u.id, "username":u.username, "created_at":u.created_at.isoformat(), "is_active":u.is_active, "is_admin":u.is_admin} for u in users])

@app.route('/api/admin/toggle_user', methods=['POST'])
@admin_required
def toggle_user():
    u = User.query.get(request.json.get('user_id'))
    if u: u.is_active = not u.is_active; db.session.commit()
    return jsonify({"ok": True})

@app.route('/api/admin/message', methods=['POST'])
@admin_required
def admin_message():
    d = request.json
    db.session.add(AdminMessage(user_id=d['user_id'], text=d['text']))
    for site in Website.query.filter_by(owner_id=d['user_id'], is_deleted=False).all():
        for chat in Chat.query.filter_by(website_id=site.id).all():
            db.session.add(Message(chat_id=chat.id, sender='admin', text=f"📢 {d['text']}"))
    db.session.commit()
    return jsonify({"ok": True})

@app.route('/api/admin/trash', methods=['GET'])
@admin_required
def get_trash():
    sites = Website.query.filter_by(is_deleted=True).order_by(Website.deleted_at.desc()).all()
    return jsonify([{"id":s.id, "url":s.url, "deleted_at":s.deleted_at.isoformat()} for s in sites])

@app.route('/api/admin/trash/<int:site_id>/restore', methods=['POST'])
@admin_required
def restore_site():
    site = Website.query.get(site_id)
    if site: site.is_deleted = False; site.deleted_at = None; db.session.commit()
    return jsonify({"ok": True})

@app.route('/api/admin/trash/<int:site_id>', methods=['DELETE'])
@admin_required
def permanent_delete():
    site = Website.query.get(site_id)
    if site: db.session.delete(site); db.session.commit()
    return jsonify({"ok": True})

# === TELEGRAM ===
@app.route('/api/telegram/setup', methods=['POST'])
@token_required
def setup_tg():
    d = request.json
    tb = TelegramBot.query.filter_by(user_id=request.current_user.id).first()
    if tb: tb.bot_token = d.get('token'); tb.is_active = d.get('active', False)
    else: tb = TelegramBot(user_id=request.current_user.id, bot_token=d.get('token'), is_active=d.get('active', False)); db.session.add(tb)
    db.session.commit()
    return jsonify({"ok": True})

@app.route('/api/admin/save_chat_id', methods=['POST'])
@token_required
def save_chat_id():
    user = request.current_user
    user.telegram_chat_id = request.json.get('chat_id')
    db.session.commit()
    return jsonify({"ok": True})

@app.route('/api/change_password', methods=['POST'])
@token_required
def change_password():
    user = request.current_user
    p = request.json.get('password')
    if not p or len(p) < 4: return jsonify({"error": "Минимум 4 символа"}), 400
    user.password_hash = hash_pwd(p); db.session.commit()
    return jsonify({"ok": True})

# === ИНИЦИАЛИЗАЦИЯ (АКТИВАЦИЯ + ПАРОЛЬ ZAQQAZ) ===
with app.app_context():
    db.create_all()
    add_missing_columns()
    
    admin = User.query.filter_by(username='Kristina').first()
    if not admin:
        admin = User(username='Kristina', is_admin=True)
        db.session.add(admin)
        
    # Жёстко ставим пароль и активируем аккаунт
    admin.password_hash = hash_pwd('zaqqaz')
    admin.is_active = True
    db.session.commit()
    print("✅ Админ Kristina готов. Пароль: zaqqaz | Статус: Активен")

@app.route('/', defaults={'path': 'index.html'})
@app.route('/<path:path>')
def serve_static(path):
    return send_from_directory(app.static_folder, path)

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port, debug=True)
