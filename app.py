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

client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

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
        return False

def hash_pwd(p): return hashlib.sha256((p + "kristina_salt_2026").encode()).hexdigest()
def get_token(): return request.headers.get('Authorization', '').replace('Bearer ', '')

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

@app.route('/api/login', methods=['POST'])
def login():
    d = request.json
    user = User.query.filter_by(username=d.get('username'), password_hash=hash_pwd(d.get('password'))).first()
    if user and user.is_active:
        return jsonify({"ok": True, "token": user.api_token, "is_admin": user.is_admin, "username": user.username})
    return jsonify({"error": "Неверные данные"}), 401

@app.route('/api/register', methods=['POST'])
def register():
    d = request.json
    if User.query.filter_by(username=d.get('username')).first():
        return jsonify({"error": "Пользователь существует"}), 409
    u = User(username=d['username'], password_hash=hash_pwd(d['password']))
    db.session.add(u); db.session.commit()
    return jsonify({"ok": True, "token": u.api_token, "username": u.username})

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
    site = Website(url=url, api_key=key, owner_id=request.current_user.id)
    db.session.add(site); db.session.commit()
    return jsonify({"ok": True})

@app.route('/api/sites/<int:site_id>/approve', methods=['POST'])
@admin_required
def approve_site():
    site = Website.query.get(site_id)
    if site: site.status = 'active'; db.session.commit()
    return jsonify({"ok": True})

@app.route('/api/chats', methods=['GET'])
@token_required
def get_chats():
    u = request.current_user
    chats = Chat.query.join(Website).filter(Website.owner_id==u.id).order_by(Chat.created_at.desc()).all()
    return jsonify([{"id":c.id, "site":Website.query.get(c.website_id).url, "status":c.status, "time":c.created_at.isoformat()} for c in chats])

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
        ai = AIManager(user_id=request.current_user.id, name=d.get('name'), behavior=d.get('behavior'), forbidden=d.get('forbidden'), knowledge_base=d.get('knowledge_base'), is_active_web=d.get('is_active_web'), is_active_telegram=d.get('is_active_telegram'))
        db.session.add(ai)
    db.session.commit()
    return jsonify({"ok": True})

@app.route('/api/ai/get', methods=['GET'])
@token_required
def get_ai():
    ai = AIManager.query.filter_by(user_id=request.current_user.id).first()
    if ai: return jsonify({"name": ai.name, "behavior": ai.behavior, "forbidden": ai.forbidden, "knowledge_base": ai.knowledge_base, "is_active_web": ai.is_active_web, "is_active_telegram": ai.is_active_telegram})
    return jsonify({})

@app.route('/api/admin/users', methods=['GET'])
@admin_required
def admin_users():
    users = User.query.all()
    return jsonify([{"id":u.id, "username":u.username, "created_at":u.created_at.isoformat(), "is_active":u.is_active} for u in users])

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
    db.session.commit()
    return jsonify({"ok": True})

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
    if not p or len(p) < 4: return jsonify({"error": "Мин 4 символа"}), 400
    user.password_hash = hash_pwd(p); db.session.commit()
    return jsonify({"ok": True})

with app.app_context():
    db.create_all()
    if not User.query.filter_by(username='Kristina').first():
        db.session.add(User(username='Kristina', password_hash=hash_pwd('zaqqaz'), is_admin=True, is_active=True))
        db.session.commit()

@app.route('/', defaults={'path': 'index.html'})
@app.route('/<path:path>')
def serve_static(path): return send_from_directory(app.static_folder, path)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 10000)), debug=True)
