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
    is_deleted = db.Column(db.Boolean, default=False)
    deleted_at = db.Column(db.DateTime, nullable=True)

class Chat(db.Model):
    __tablename__ = 'chat'
    id = db.Column(db.Integer, primary_key=True)
    website_id = db.Column(db.Integer, db.ForeignKey('website.id'), nullable=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    status = db.Column(db.String(20), default='waiting')
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
            db.session.execute(text('ALTER TABLE aimanager ADD COLUMN IF NOT EXISTS created_at TIMESTAMP'))
            try:
                db.session.execute(text('ALTER TABLE chat ADD COLUMN user_id INTEGER'))
                db.session.commit()
                print("✅ Добавлена колонка user_id в таблицу chat")
            except:
                db.session.rollback()
                print("ℹ️ Колонка user_id уже существует")
            db.session.commit()
        except Exception as e:
            print(f"Migration error: {e}")
            db.session.rollback()

@app.route('/api/login', methods=['POST'])
def login():
    try:
        d = request.json
        username = d.get('username', '').strip()
        password = d.get('password', '')
        user = User.query.filter_by(username=username).first()
        if not user: return jsonify({"error": "Неверные данные"}), 401
        if not user.is_active: return jsonify({"error": "Аккаунт отключен"}), 401
        if user.password_hash != hash_pwd(password): return jsonify({"error": "Неверные данные"}), 401
        return jsonify({"ok": True, "token": user.api_token, "is_admin": user.is_admin, "username": user.username})
    except Exception as e:
        print(f"Login error: {e}")
        return jsonify({"error": "Ошибка сервера"}), 500

@app.route('/api/register', methods=['POST'])
def register():
    try:
        d = request.json
        username = d.get('username', '').strip()
        password = d.get('password', '')
        if not username or len(password) < 4: return jsonify({"error": "Логин мин. 2 символа, пароль мин. 4"}), 400
        if User.query.filter_by(username=username).first(): return jsonify({"error": "Пользователь существует"}), 409
        u = User(username=username, password_hash=hash_pwd(password))
        db.session.add(u)
        db.session.commit()
        return jsonify({"ok": True, "token": u.api_token, "username": u.username})
    except Exception as e:
        print(f"Register error: {e}")
        return jsonify({"error": "Ошибка сервера"}), 500

@app.route('/api/sites', methods=['GET'])
@token_required
def get_sites():
    try:
        u = request.current_user
        sites = Website.query.filter_by(owner_id=u.id, is_deleted=False).all() if not u.is_admin else Website.query.filter_by(is_deleted=False).all()
        return jsonify([{"id":s.id, "url":s.url, "api_key":s.api_key, "status":s.status, "owner":s.owner_id} for s in sites])
    except Exception as e:
        print(f"Get sites error: {e}")
        return jsonify([]), 500

@app.route('/api/sites', methods=['POST'])
@token_required
def add_site():
    try:
        url = request.json.get('url')
        if not url: return jsonify({"error": "URL обязателен"}), 400
        key = f"site_{uuid.uuid4().hex[:8]}"
        site = Website(url=url, api_key=key, owner_id=request.current_user.id, status='pending')
        db.session.add(site)
        db.session.commit()
        return jsonify({"ok": True, "id": site.id})
    except Exception as e:
        print(f"Add site error: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/sites/<int:site_id>/approve', methods=['POST'])
@admin_required
def approve_site():
    try:
        site = Website.query.get(site_id)
        if site and not site.is_deleted:
            site.status = 'active'
            db.session.commit()
        return jsonify({"ok": True})
    except Exception as e:
        print(f"Approve error: {e}")
        return jsonify({"error": "Ошибка"}), 500

@app.route('/api/sites/<int:site_id>/delete', methods=['POST'])
@token_required
def delete_site(site_id):
    try:
        site = Website.query.get(site_id)
        if not site or (site.owner_id != request.current_user.id and not request.current_user.is_admin):
            return jsonify({"error": "Не найдено или нет прав"}), 404
        site.is_deleted = True
        site.deleted_at = datetime.datetime.utcnow()
        db.session.commit()
        return jsonify({"ok": True})
    except Exception as e:
        print(f"Delete error: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

@app.route('/api/chats', methods=['GET'])
@token_required
def get_chats():
    try:
        u = request.current_user
        
        if u.is_admin:
            # Админ видит все чаты
            chats = Chat.query.order_by(Chat.created_at.desc()).all()
            result = []
            for c in chats:
                # Безопасно получаем имя пользователя
                if hasattr(c, 'user_id') and c.user_id:
                    target = User.query.get(c.user_id)
                    chat_name = target.username if target else "Пользователь"
                else:
                    chat_name = "Пользователь"
                result.append({"id": c.id, "site": chat_name, "status": c.status, "time": c.created_at.isoformat()})
            return jsonify(result)
        else:
            # Пользователь видит только свои чаты
            chats = Chat.query.filter_by(user_id=u.id).order_by(Chat.created_at.desc()).all() if hasattr(Chat, 'user_id') else []
            return jsonify([{"id": c.id, "site": "Админ", "status": c.status, "time": c.created_at.isoformat()} for c in chats])
            
    except Exception as e:
        print(f"Get chats error: {e}")
        import traceback
        traceback.print_exc()
        return jsonify([]), 500

@app.route('/api/chats/<int:chat_id>/delete', methods=['POST'])
@admin_required
def delete_chat(chat_id):
    try:
        chat = Chat.query.get(chat_id)
        if not chat:
            return jsonify({"error": "Чат не найден"}), 404
        Message.query.filter_by(chat_id=chat_id).delete()
        db.session.delete(chat)
        db.session.commit()
        return jsonify({"ok": True})
    except Exception as e:
        print(f"Delete chat error: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/messages/<int:chat_id>', methods=['GET'])
@token_required
def get_messages(chat_id):
    try:
        msgs = Message.query.filter_by(chat_id=chat_id).order_by(Message.timestamp).all()
        return jsonify([{"sender":m.sender, "text":m.text, "time":m.timestamp.isoformat()} for m in msgs])
    except Exception as e:
        print(f"Get messages error: {e}")
        return jsonify([]), 500

@app.route('/api/send', methods=['POST'])
@token_required
def send_message():
    try:
        d = request.json
        sender = 'admin' if request.current_user.is_admin else 'user'
        db.session.add(Message(chat_id=d['chat_id'], sender=sender, text=d['text']))
        db.session.commit()
        return jsonify({"ok": True})
    except Exception as e:
        print(f"Send error: {e}")
        return jsonify({"error": "Ошибка"}), 500

@app.route('/api/ai/setup', methods=['POST'])
@token_required
def setup_ai():
    try:
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
            ai = AIManager(user_id=request.current_user.id, name=d.get('name','AI'), behavior=d.get('behavior',''), forbidden=d.get('forbidden',''), knowledge_base=d.get('knowledge_base',''), is_active_web=d.get('is_active_web',False), is_active_telegram=d.get('is_active_telegram',False))
            db.session.add(ai)
        db.session.commit()
        return jsonify({"ok": True})
    except Exception as e:
        print(f"AI setup error: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/ai/get', methods=['GET'])
@token_required
def get_ai():
    try:
        ai = AIManager.query.filter_by(user_id=request.current_user.id).first()
        if ai:
            return jsonify({"name": ai.name, "behavior": ai.behavior, "forbidden": ai.forbidden, "knowledge_base": ai.knowledge_base, "is_active_web": ai.is_active_web, "is_active_telegram": ai.is_active_telegram})
        return jsonify({})
    except Exception as e:
        print(f"AI get error: {e}")
        return jsonify({}), 500

@app.route('/api/admin/users', methods=['GET'])
@admin_required
def admin_users():
    try:
        users = User.query.order_by(User.created_at.desc()).all()
        return jsonify([{"id":u.id, "username":u.username, "created_at":u.created_at.isoformat(), "is_active":u.is_active, "is_admin":u.is_admin} for u in users])
    except Exception as e:
        print(f"Admin users error: {e}")
        import traceback
        traceback.print_exc()
        return jsonify([]), 500

@app.route('/api/admin/toggle_user', methods=['POST'])
@admin_required
def toggle_user():
    try:
        user_id = request.json.get('user_id')
        u = User.query.get(user_id)
        if u and u.username != request.current_user.username:
            u.is_active = not u.is_active
            db.session.commit()
        return jsonify({"ok": True})
    except Exception as e:
        print(f"Toggle error: {e}")
        return jsonify({"error": "Ошибка"}), 500

@app.route('/api/admin/send_to_user', methods=['POST'])
@admin_required
def admin_send_to_user():
    try:
        d = request.json
        user_id = d.get('user_id')
        text = d.get('text')
        if not user_id or not text:
            return jsonify({"error": "user_id и text обязательны"}), 400
        chat = Chat(user_id=user_id, status='waiting')
        db.session.add(chat)
        db.session.commit()
        db.session.add(Message(chat_id=chat.id, sender='admin', text=text))
        db.session.commit()
        return jsonify({"ok": True, "chat_id": chat.id})
    except Exception as e:
        print(f"Admin send error: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

@app.route('/api/telegram/setup', methods=['POST'])
@token_required
def setup_tg():
    try:
        d = request.json
        tb = TelegramBot.query.filter_by(user_id=request.current_user.id).first()
        if tb: 
            tb.bot_token = d.get('token')
            tb.is_active = d.get('active', False)
        else: 
            tb = TelegramBot(user_id=request.current_user.id, bot_token=d.get('token'), is_active=d.get('active', False))
            db.session.add(tb)
        db.session.commit()
        return jsonify({"ok": True})
    except Exception as e:
        print(f"Telegram error: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/admin/save_chat_id', methods=['POST'])
@admin_required
def save_chat_id():
    try:
        user = request.current_user
        user.telegram_chat_id = request.json.get('chat_id')
        db.session.commit()
        return jsonify({"ok": True})
    except Exception as e:
        print(f"Save chat ID error: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/change_password', methods=['POST'])
@token_required
def change_password():
    try:
        user = request.current_user
        p = request.json.get('password')
        if not p or len(p) < 4: return jsonify({"error": "Минимум 4 символа"}), 400
        user.password_hash = hash_pwd(p)
        db.session.commit()
        return jsonify({"ok": True})
    except Exception as e:
        print(f"Password error: {e}")
        return jsonify({"error": "Ошибка"}), 500

with app.app_context():
    db.create_all()
    add_missing_columns()
    admin = User.query.filter_by(username='Kristina').first()
    if not admin:
        admin = User(username='Kristina', is_admin=True)
        db.session.add(admin)
    admin.is_active = True
    admin.password_hash = hash_pwd('zaqqaz')
    db.session.commit()
    print("✅ Admin Kristina: ACTIVE | Password: zaqqaz")

@app.route('/', defaults={'path': 'index.html'})
@app.route('/<path:path>')
def serve_static(path):
    return send_from_directory(app.static_folder, path)

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port, debug=True)
