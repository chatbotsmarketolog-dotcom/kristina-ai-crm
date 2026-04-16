import os, json, uuid, hashlib, datetime, secrets, requests
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import text
from openai import OpenAI

app = Flask(__name__, static_folder='static', static_url_path='')
# ✅ ИСПРАВЛЕНО: добавлен X-API-Key в разрешённые заголовки
CORS(app, supports_credentials=True, origins=["*"], allow_headers=["Content-Type", "Authorization", "X-API-Key"])

app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.secret_key = os.environ.get('SECRET_KEY', secrets.token_hex(16))
db = SQLAlchemy(app)

client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

BOT_TOKEN = "8694190622:AAEVveNpF60fGx8wMl5ViJWawsdWAOqk9Yk"

def send_telegram_notification(chat_id, text):
    if not chat_id:
        return
    try:
        requests.post(
            f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
            json={"chat_id": chat_id, "text": text, "parse_mode": "HTML"}
        )
    except Exception as e:
        print(f"Telegram notification error: {e}")

def validate_contact_method(method):
    """Проверка разрешённых мессенджеров"""
    allowed = ['telegram', 'vk', 'одноклассники', 'instagram', 'tenchat', 'тентенчат', 'ок']
    blocked = ['max', 'макс', 'макс к', 'макс.к', 'max.k']
    method_lower = method.lower().strip()
    if method_lower in blocked:
        return False, "❌ Мессенджер MAX/МАКС запрещён. Пожалуйста, укажите один из разрешённых: Telegram, ВК, Одноклассники, Instagram, TenChat"
    if method_lower not in allowed:
        return False, f"❌ '{method}' не в списке разрешённых. Доступно: Telegram, ВК, Одноклассники, Instagram, TenChat"
    return True, None

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
    visitor_name = db.Column(db.String(100))
    form_requested = db.Column(db.Boolean, default=False)
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
    humanity_level = db.Column(db.Integer, default=3)
    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)

class TelegramBot(db.Model):
    __tablename__ = 'telegrambot'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    bot_token = db.Column(db.String(200), unique=True)
    is_active = db.Column(db.Boolean, default=False)

class AIPDF(db.Model):
    __tablename__ = 'aipdf'
    id = db.Column(db.Integer, primary_key=True)
    agent_id = db.Column(db.Integer, db.ForeignKey('aimanager.id'))
    filename = db.Column(db.String(200))
    file_path = db.Column(db.String(500))
    uploaded_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)

class AIWebsite(db.Model):
    __tablename__ = 'aiwebsite'
    id = db.Column(db.Integer, primary_key=True)
    agent_id = db.Column(db.Integer, db.ForeignKey('aimanager.id'))
    website_id = db.Column(db.Integer, db.ForeignKey('website.id'))
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)

class Deal(db.Model):
    __tablename__ = 'deal'
    id = db.Column(db.Integer, primary_key=True)
    chat_id = db.Column(db.Integer, db.ForeignKey('chat.id'))
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    client_name = db.Column(db.String(100))
    sphere = db.Column(db.String(200))
    request = db.Column(db.Text)
    budget = db.Column(db.String(100))
    contact_method = db.Column(db.String(50))
    contact_nickname = db.Column(db.String(100))
    status = db.Column(db.String(20), default='pending')
    decline_reason = db.Column(db.String(200))
    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)

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
            # Миграции для user
            db.session.execute(text('ALTER TABLE "user" ADD COLUMN IF NOT EXISTS telegram_chat_id VARCHAR(100)'))
            
            # Миграции для website
            db.session.execute(text('ALTER TABLE website ADD COLUMN IF NOT EXISTS is_deleted BOOLEAN DEFAULT FALSE'))
            db.session.execute(text('ALTER TABLE website ADD COLUMN IF NOT EXISTS deleted_at TIMESTAMP'))
            
            # Миграции для aimanager
            db.session.execute(text('ALTER TABLE aimanager ADD COLUMN IF NOT EXISTS is_active_web BOOLEAN DEFAULT FALSE'))
            db.session.execute(text('ALTER TABLE aimanager ADD COLUMN IF NOT EXISTS is_active_telegram BOOLEAN DEFAULT FALSE'))
            db.session.execute(text('ALTER TABLE aimanager ADD COLUMN IF NOT EXISTS created_at TIMESTAMP'))
            db.session.execute(text('ALTER TABLE aimanager ADD COLUMN IF NOT EXISTS forbidden TEXT'))
            db.session.execute(text('ALTER TABLE aimanager ADD COLUMN IF NOT EXISTS humanity_level INTEGER DEFAULT 3'))
            
            # Миграции для chat
            db.session.execute(text('ALTER TABLE chat ADD COLUMN IF NOT EXISTS visitor_name VARCHAR(100)'))
            db.session.execute(text('ALTER TABLE chat ADD COLUMN IF NOT EXISTS form_requested BOOLEAN DEFAULT FALSE'))
            
            try:
                db.session.execute(text('ALTER TABLE chat ADD COLUMN user_id INTEGER'))
                db.session.execute(text('CREATE TABLE IF NOT EXISTS aiwebsite (id SERIAL PRIMARY KEY, agent_id INTEGER REFERENCES aimanager(id), website_id INTEGER REFERENCES website(id), is_active BOOLEAN DEFAULT TRUE, created_at TIMESTAMP DEFAULT NOW())'))
                db.session.execute(text('''
                    CREATE TABLE IF NOT EXISTS deal (
                        id SERIAL PRIMARY KEY,
                        chat_id INTEGER REFERENCES chat(id),
                        user_id INTEGER REFERENCES "user"(id),
                        client_name VARCHAR(100),
                        sphere VARCHAR(200),
                        request TEXT,
                        budget VARCHAR(100),
                        contact_method VARCHAR(50),
                        contact_nickname VARCHAR(100),
                        status VARCHAR(20) DEFAULT 'pending',
                        decline_reason VARCHAR(200),
                        created_at TIMESTAMP DEFAULT NOW()
                    )
                '''))
                db.session.commit()
                print("✅ Все миграции выполнены")
            except Exception as e:
                db.session.rollback()
                print(f"ℹ️ Некоторые таблицы уже существуют: {e}")
            db.session.commit()
        except Exception as e:
            print(f"Migration error: {e}")
            db.session.rollback()

@app.route('/api/admin/clear_deleted_sites', methods=['POST'])
@admin_required
def clear_deleted_sites():
    try:
        deleted_count = Website.query.filter_by(is_deleted=True).delete()
        db.session.commit()
        return jsonify({"ok": True, "deleted": deleted_count})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/admin/migrate_ai_columns', methods=['POST'])
@admin_required
def migrate_ai_columns():
    try:
        with app.app_context():
            db.session.execute(text('ALTER TABLE aimanager ADD COLUMN IF NOT EXISTS forbidden TEXT'))
            db.session.execute(text('ALTER TABLE aimanager ADD COLUMN IF NOT EXISTS humanity_level INTEGER DEFAULT 3'))
            db.session.commit()
        return jsonify({"ok": True, "message": "Колонки добавлены"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/admin/migrate_deals_table', methods=['POST'])
@admin_required
def migrate_deals_table():
    """Добавить колонку visitor_name и таблицу deal"""
    try:
        with app.app_context():
            db.session.execute(text('ALTER TABLE chat ADD COLUMN IF NOT EXISTS visitor_name VARCHAR(100)'))
            db.session.execute(text('ALTER TABLE chat ADD COLUMN IF NOT EXISTS form_requested BOOLEAN DEFAULT FALSE'))
            db.session.execute(text('''
                CREATE TABLE IF NOT EXISTS deal (
                    id SERIAL PRIMARY KEY,
                    chat_id INTEGER REFERENCES chat(id),
                    user_id INTEGER REFERENCES "user"(id),
                    client_name VARCHAR(100),
                    sphere VARCHAR(200),
                    request TEXT,
                    budget VARCHAR(100),
                    contact_method VARCHAR(50),
                    contact_nickname VARCHAR(100),
                    status VARCHAR(20) DEFAULT 'pending',
                    decline_reason VARCHAR(200),
                    created_at TIMESTAMP DEFAULT NOW()
                )
            '''))
            db.session.commit()
        return jsonify({"ok": True, "message": "Миграция завершена"})
    except Exception as e:
        print(f"Migration error: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/admin/migrate_form_requested', methods=['POST'])
@admin_required
def migrate_form_requested():
    """Добавить колонку form_requested в таблицу chat"""
    try:
        with app.app_context():
            db.session.execute(text('ALTER TABLE chat ADD COLUMN IF NOT EXISTS form_requested BOOLEAN DEFAULT FALSE'))
            db.session.commit()
        return jsonify({"ok": True, "message": "Колонка form_requested добавлена"})
    except Exception as e:
        print(f"Migration error: {e}")
        return jsonify({"error": str(e)}), 500

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

# === САЙТЫ ===

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
        existing_site = Website.query.filter_by(url=url).first()
        if existing_site:
            if existing_site.owner_id == request.current_user.id:
                return jsonify({"error": "Этот сайт уже добавлен", "id": existing_site.id}), 400
            else:
                return jsonify({"error": "Этот сайт уже добавлен другим пользователем"}), 400
        key = f"site_{uuid.uuid4().hex[:8]}"
        site = Website(url=url, api_key=key, owner_id=request.current_user.id, status='pending')
        db.session.add(site)
        db.session.commit()
        admin = User.query.filter_by(is_admin=True).first()
        if admin and admin.telegram_chat_id:
            send_telegram_notification(admin.telegram_chat_id, f"🔔 <b>Новый сайт на модерации!</b>\n\n👤 Владелец: {request.current_user.username}\n🔗 Сайт: {url}\n\nЗайдите в админ-панель для одобрения.")
        return jsonify({"ok": True, "id": site.id})
    except Exception as e:
        print(f"Add site error: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

@app.route('/api/sites/pending', methods=['GET'])
@admin_required
def get_pending_sites():
    try:
        sites = Website.query.filter_by(status='pending', is_deleted=False).all()
        result = []
        for site in sites:
            owner = User.query.get(site.owner_id)
            result.append({"id": site.id, "url": site.url, "api_key": site.api_key, "owner": owner.username if owner else "Unknown", "owner_id": site.owner_id, "created_at": site.created_at.isoformat()})
        return jsonify(result)
    except Exception as e:
        print(f"Get pending sites error: {e}")
        return jsonify([]), 500

@app.route('/api/sites/<int:site_id>/approve', methods=['POST'])
@admin_required
def approve_site_endpoint(site_id):
    try:
        site = Website.query.get(site_id)
        if not site: return jsonify({"error": "Сайт не найден"}), 404
        site.status = 'active'
        db.session.commit()
        owner = User.query.get(site.owner_id)
        if owner and owner.telegram_chat_id:
            send_telegram_notification(owner.telegram_chat_id, f"✅ <b>Ваш сайт одобрен!</b>\n\n🔗 {site.url}\n\nТеперь вы можете использовать виджет КРИСТИНА.AI CRM")
        admin = User.query.filter_by(is_admin=True).first()
        if admin and admin.telegram_chat_id:
            send_telegram_notification(admin.telegram_chat_id, f"✅ Сайт одобрен: {site.url}\nВладелец: {owner.username if owner else 'Unknown'}")
        return jsonify({"ok": True})
    except Exception as e:
        print(f"Approve error: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/sites/<int:site_id>/reject', methods=['POST'])
@admin_required
def reject_site(site_id):
    try:
        site = Website.query.get(site_id)
        if not site: return jsonify({"error": "Сайт не найден"}), 404
        db.session.delete(site)
        db.session.commit()
        return jsonify({"ok": True})
    except Exception as e:
        print(f"Reject error: {e}")
        return jsonify({"error": str(e)}), 500

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

# === ЧАТЫ ===

@app.route('/api/chats', methods=['GET'])
@token_required
def get_chats():
    try:
        u = request.current_user
        if u.is_admin:
            chats = Chat.query.order_by(Chat.created_at.desc()).all()
            result = []
            for c in chats:
                chat_name = c.visitor_name
                if not chat_name and c.user_id:
                    user = User.query.get(c.user_id)
                    chat_name = user.username if user else "Пользователь"
                if not chat_name:
                    chat_name = "Пользователь"
                result.append({"id": c.id, "site": chat_name, "status": c.status, "time": c.created_at.isoformat()})
            return jsonify(result)
        else:
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
        if not chat: return jsonify({"error": "Чат не найден"}), 404
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
        chat = Chat.query.get(chat_id)
        msgs = Message.query.filter_by(chat_id=chat_id).order_by(Message.timestamp).all()
        # Возвращаем объект с сообщениями и флагом form_requested
        return jsonify({
            "messages": [{"sender":m.sender, "text":m.text, "time":m.timestamp.isoformat()} for m in msgs],
            "form_requested": bool(chat.form_requested) if chat and hasattr(chat, 'form_requested') else False
        })
    except Exception as e:
        print(f"Get messages error: {e}")
        return jsonify({"messages": [], "form_requested": False}), 500

@app.route('/api/send', methods=['POST'])
@token_required
def send_message():
    try:
        d = request.json
        sender = 'admin' if request.current_user.is_admin else 'user'
        text = d.get('text', '').lower()
        
        # Авто-триггер формы от агента: если пользователь написал и текст содержит согласие
        if sender == 'user' and not request.current_user.is_admin:
            consent_keywords = ['да', 'хочу', 'готов', 'согласен', 'ок', 'хорошо', 'давайте', 'пригласите', 'встреча', 'личная встреча', 'записаться']
            if any(kw in text for kw in consent_keywords):
                chat = Chat.query.get(d['chat_id'])
                if chat and not chat.form_requested:
                    chat.form_requested = True
                    db.session.commit()
                    user = User.query.get(chat.user_id)
                    if user and user.telegram_chat_id:
                        send_telegram_notification(
                            user.telegram_chat_id,
                            "🤖 Агент предлагает заполнить заявку на личную встречу!\n\nЗайдите в чат чтобы заполнить форму."
                        )
        
        db.session.add(Message(chat_id=d['chat_id'], sender=sender, text=d['text']))
        db.session.commit()
        
        chat = Chat.query.get(d['chat_id'])
        if chat and chat.user_id:
            if sender == 'admin':
                user = User.query.get(chat.user_id)
                if user and user.telegram_chat_id:
                    send_telegram_notification(user.telegram_chat_id, f"💬 <b>Новое сообщение от админа!</b>\n\n{d['text'][:100]}..." if len(d['text']) > 100 else d['text'])
            else:
                admin = User.query.filter_by(is_admin=True).first()
                if admin and admin.telegram_chat_id:
                    user = User.query.get(chat.user_id)
                    send_telegram_notification(admin.telegram_chat_id, f"💬 <b>Ответ от {user.username if user else 'Пользователя'}</b>\n\n{d['text'][:100]}..." if len(d['text']) > 100 else d['text'])
        
        # Возвращаем form_requested для фронтенда
        return jsonify({"ok": True, "form_requested": bool(chat.form_requested) if chat and hasattr(chat, 'form_requested') else False})
    except Exception as e:
        print(f"Send error: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

# === АГЕНТЫ ===

@app.route('/api/ai/agents', methods=['GET'])
@token_required
def get_user_agents():
    try:
        agents = AIManager.query.filter_by(user_id=request.current_user.id).all()
        result = []
        for a in agents:
            pdfs = AIPDF.query.filter_by(agent_id=a.id).all()
            link = AIWebsite.query.filter_by(agent_id=a.id).first()
            website = Website.query.get(link.website_id) if link else None
            result.append({
                "id": a.id,
                "name": a.name,
                "behavior": a.behavior,
                "forbidden": a.forbidden,
                "knowledge_base": a.knowledge_base,
                "is_active_web": a.is_active_web,
                "is_active_telegram": a.is_active_telegram,
                "humanity_level": a.humanity_level,
                "pdfs": [{"id": p.id, "filename": p.filename} for p in pdfs],
                "linked_website": {"id": website.id, "url": website.url} if website else None,
                "created_at": a.created_at.isoformat()
            })
        return jsonify(result)
    except Exception as e:
        print(f"Get agents error: {e}")
        return jsonify([]), 500

@app.route('/api/ai/setup', methods=['POST'])
@token_required
def setup_ai():
    try:
        d = request.json
        agent_count = AIManager.query.filter_by(user_id=request.current_user.id).count()
        if agent_count >= 10:
            return jsonify({"error": "Достигнут лимит: максимум 10 агентов"}), 400
        ai = AIManager(
            user_id=request.current_user.id,
            name=d.get('name','AI Assistant'),
            behavior=d.get('behavior',''),
            forbidden=d.get('forbidden',''),
            knowledge_base=d.get('knowledge_base',''),
            is_active_web=d.get('is_active_web',False),
            is_active_telegram=d.get('is_active_telegram',False),
            humanity_level=d.get('humanity_level', 3)
        )
        db.session.add(ai)
        db.session.commit()
        return jsonify({"ok": True, "agent_id": ai.id})
    except Exception as e:
        print(f"AI setup error: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/ai/agents/<int:agent_id>', methods=['PUT'])
@token_required
def update_agent(agent_id):
    try:
        agent = AIManager.query.filter_by(id=agent_id, user_id=request.current_user.id).first()
        if not agent: return jsonify({"error": "Агент не найден"}), 404
        d = request.json
        agent.name = d.get('name', agent.name)
        agent.behavior = d.get('behavior', agent.behavior)
        agent.forbidden = d.get('forbidden', agent.forbidden)
        agent.knowledge_base = d.get('knowledge_base', agent.knowledge_base)
        agent.humanity_level = d.get('humanity_level', agent.humanity_level)
        db.session.commit()
        return jsonify({"ok": True})
    except Exception as e:
        print(f"Update agent error: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/ai/agents/<int:agent_id>/toggle', methods=['POST'])
@token_required
def toggle_agent(agent_id):
    try:
        agent = AIManager.query.filter_by(id=agent_id, user_id=request.current_user.id).first()
        if not agent: return jsonify({"error": "Агент не найден"}), 404
        agent.is_active_web = not agent.is_active_web
        db.session.commit()
        return jsonify({"ok": True, "is_active": agent.is_active_web})
    except Exception as e:
        print(f"Toggle agent error: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/ai/agents/<int:agent_id>/toggle_telegram', methods=['POST'])
@token_required
def toggle_agent_telegram(agent_id):
    try:
        agent = AIManager.query.filter_by(id=agent_id, user_id=request.current_user.id).first()
        if not agent: return jsonify({"error": "Агент не найден"}), 404
        agent.is_active_telegram = not agent.is_active_telegram
        db.session.commit()
        return jsonify({"ok": True, "is_active": agent.is_active_telegram})
    except Exception as e:
        print(f"Toggle agent telegram error: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/ai/agents/<int:agent_id>/delete', methods=['DELETE'])
@token_required
def delete_agent(agent_id):
    try:
        agent = AIManager.query.filter_by(id=agent_id, user_id=request.current_user.id).first()
        if not agent: return jsonify({"error": "Агент не найден"}), 404
        AIPDF.query.filter_by(agent_id=agent_id).delete()
        AIWebsite.query.filter_by(agent_id=agent_id).delete()
        db.session.delete(agent)
        db.session.commit()
        return jsonify({"ok": True})
    except Exception as e:
        print(f"Delete agent error: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/ai/agents/<int:agent_id>/link_website', methods=['POST'])
@token_required
def link_agent_to_website(agent_id):
    try:
        d = request.json
        website_id = d.get('website_id')
        agent = AIManager.query.filter_by(id=agent_id, user_id=request.current_user.id).first()
        if not agent: return jsonify({"error": "Агент не найден"}), 404
        website = Website.query.filter_by(id=website_id, owner_id=request.current_user.id).first()
        if not website: return jsonify({"error": "Сайт не найден"}), 404
        existing = AIWebsite.query.filter_by(agent_id=agent_id).first()
        if existing:
            return jsonify({"error": "Агент уже привязан к сайту"}), 400
        link = AIWebsite(agent_id=agent_id, website_id=website_id)
        db.session.add(link)
        db.session.commit()
        return jsonify({"ok": True})
    except Exception as e:
        print(f"Link website error: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/ai/agents/<int:agent_id>/unlink_website', methods=['POST'])
@token_required
def unlink_agent_from_website(agent_id):
    try:
        agent = AIManager.query.filter_by(id=agent_id, user_id=request.current_user.id).first()
        if not agent: return jsonify({"error": "Агент не найден"}), 404
        AIWebsite.query.filter_by(agent_id=agent_id).delete()
        db.session.commit()
        return jsonify({"ok": True})
    except Exception as e:
        print(f"Unlink website error: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/ai/agents/<int:agent_id>/linked_website', methods=['GET'])
@token_required
def get_linked_website(agent_id):
    try:
        agent = AIManager.query.filter_by(id=agent_id, user_id=request.current_user.id).first()
        if not agent: return jsonify({"error": "Агент не найден"}), 404
        link = AIWebsite.query.filter_by(agent_id=agent_id).first()
        if not link: return jsonify({"website": None})
        website = Website.query.get(link.website_id)
        return jsonify({"website": {"id": website.id, "url": website.url, "status": website.status} if website else None})
    except Exception as e:
        print(f"Get linked website error: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/ai/get', methods=['GET'])
@token_required
def get_ai():
    try:
        ai = AIManager.query.filter_by(user_id=request.current_user.id).first()
        if ai:
            pdfs = AIPDF.query.filter_by(agent_id=ai.id).all()
            return jsonify({
                "name": ai.name,
                "behavior": ai.behavior,
                "forbidden": ai.forbidden,
                "knowledge_base": ai.knowledge_base,
                "is_active_web": ai.is_active_web,
                "is_active_telegram": ai.is_active_telegram,
                "humanity_level": ai.humanity_level,
                "pdfs": [{"id": p.id, "filename": p.filename} for p in pdfs]
            })
        return jsonify({})
    except Exception as e:
        print(f"AI get error: {e}")
        return jsonify({}), 500

@app.route('/api/ai/upload_pdf', methods=['POST'])
@token_required
def upload_pdf():
    try:
        if 'file' not in request.files: return jsonify({"error": "Нет файла"}), 400
        file = request.files['file']
        if file.filename == '' or not file.filename.endswith('.pdf'): return jsonify({"error": "Только PDF файлы"}), 400
        agent_id = request.form.get('agent_id')
        if not agent_id: return jsonify({"error": "Нет ID агента"}), 400
        agent = AIManager.query.filter_by(id=agent_id, user_id=request.current_user.id).first()
        if not agent: return jsonify({"error": "Агент не найден"}), 404
        uploads_dir = os.path.join(app.static_folder, 'uploads', 'ai_pdfs')
        os.makedirs(uploads_dir, exist_ok=True)
        filename = f"{uuid.uuid4().hex}_{file.filename}"
        filepath = os.path.join(uploads_dir, filename)
        file.save(filepath)
        pdf = AIPDF(agent_id=agent_id, filename=file.filename, file_path=filepath)
        db.session.add(pdf)
        db.session.commit()
        return jsonify({"ok": True, "pdf_id": pdf.id, "filename": file.filename})
    except Exception as e:
        print(f"Upload PDF error: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/ai/delete_pdf/<int:pdf_id>', methods=['DELETE'])
@token_required
def delete_pdf(pdf_id):
    try:
        pdf = AIPDF.query.get(pdf_id)
        if not pdf: return jsonify({"error": "Файл не найден"}), 404
        agent = AIManager.query.get(pdf.agent_id)
        if agent and agent.user_id != request.current_user.id: return jsonify({"error": "Нет прав"}), 403
        if os.path.exists(pdf.file_path): os.remove(pdf.file_path)
        db.session.delete(pdf)
        db.session.commit()
        return jsonify({"ok": True})
    except Exception as e:
        print(f"Delete PDF error: {e}")
        return jsonify({"error": str(e)}), 500

# === СДЕЛКИ ===

@app.route('/api/deals', methods=['POST'])
@token_required
def create_deal():
    try:
        d = request.json
        chat_id = d.get('chat_id')
        is_valid, error = validate_contact_method(d.get('contact_method', ''))
        if not is_valid:
            return jsonify({"error": error}), 400
        chat = Chat.query.get(chat_id)
        if not chat:
            return jsonify({"error": "Чат не найден"}), 404
        deal = Deal(
            chat_id=chat_id,
            user_id=chat.user_id or request.current_user.id,
            client_name=d.get('client_name'),
            sphere=d.get('sphere'),
            request=d.get('request'),
            budget=d.get('budget'),
            contact_method=d.get('contact_method'),
            contact_nickname=d.get('contact_nickname'),
            status='completed'
        )
        db.session.add(deal)
        db.session.commit()
        admin = User.query.filter_by(is_admin=True).first()
        if admin and admin.telegram_chat_id:
            send_telegram_notification(
                admin.telegram_chat_id,
                f"🎉 <b>Новая сделка!</b>\n\n👤 Клиент: {deal.client_name}\n💼 Сфера: {deal.sphere}\n💰 Бюджет: {deal.budget}\n📱 Контакт: {deal.contact_method} @{deal.contact_nickname}"
            )
        return jsonify({"ok": True, "deal_id": deal.id})
    except Exception as e:
        print(f"Create deal error: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/deals', methods=['GET'])
@token_required
def get_deals():
    try:
        status = request.args.get('status', 'completed')
        user = request.current_user
        if user.is_admin:
            deals = Deal.query.filter_by(status=status).order_by(Deal.created_at.desc()).all()
        else:
            deals = Deal.query.filter_by(user_id=user.id, status=status).order_by(Deal.created_at.desc()).all()
        result = []
        for deal in deals:
            result.append({
                "id": deal.id,
                "client_name": deal.client_name,
                "sphere": deal.sphere,
                "request": deal.request,
                "budget": deal.budget,
                "contact_method": deal.contact_method,
                "contact_nickname": deal.contact_nickname,
                "status": deal.status,
                "decline_reason": deal.decline_reason,
                "chat_id": deal.chat_id,
                "created_at": deal.created_at.isoformat()
            })
        return jsonify(result)
    except Exception as e:
        print(f"Get deals error: {e}")
        return jsonify([]), 500

@app.route('/api/deals/<int:deal_id>', methods=['PUT'])
@token_required
def update_deal(deal_id):
    try:
        deal = Deal.query.get(deal_id)
        if not deal:
            return jsonify({"error": "Сделка не найдена"}), 404
        d = request.json
        deal.status = d.get('status', deal.status)
        deal.decline_reason = d.get('decline_reason', deal.decline_reason)
        db.session.commit()
        return jsonify({"ok": True})
    except Exception as e:
        print(f"Update deal error: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/deals/<int:deal_id>', methods=['DELETE'])
@token_required
def delete_deal(deal_id):
    try:
        deal = Deal.query.get(deal_id)
        if not deal:
            return jsonify({"error": "Сделка не найдена"}), 404
        db.session.delete(deal)
        db.session.commit()
        return jsonify({"ok": True})
    except Exception as e:
        print(f"Delete deal error: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/chat/<int:chat_id>/set_client_name', methods=['POST'])
@token_required
def set_client_name(chat_id):
    try:
        chat = Chat.query.get(chat_id)
        if not chat:
            return jsonify({"error": "Чат не найден"}), 404
        name = request.json.get('name', '').strip()
        if not name:
            return jsonify({"error": "Имя обязательно"}), 400
        chat.visitor_name = name
        db.session.commit()
        return jsonify({"ok": True})
    except Exception as e:
        print(f"Set client name error: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/chat/<int:chat_id>/request_form', methods=['POST'])
@token_required
def request_deal_form(chat_id):
    """Пометить чат что форма заявки запрошена"""
    try:
        chat = Chat.query.get(chat_id)
        if not chat:
            return jsonify({"error": "Чат не найден"}), 404
        chat.form_requested = True
        db.session.commit()
        
        user = User.query.get(chat.user_id)
        if user and user.telegram_chat_id:
            send_telegram_notification(
                user.telegram_chat_id,
                "📋 Вам предложено заполнить заявку на личную встречу!\n\nЗайдите в чат чтобы заполнить форму."
            )
        
        return jsonify({"ok": True})
    except Exception as e:
        print(f"Request form error: {e}")
        return jsonify({"error": str(e)}), 500

# === TELEGRAM ===

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
        if not user_id or not text: return jsonify({"error": "user_id и text обязательны"}), 400
        chat = Chat(user_id=user_id, status='waiting')
        db.session.add(chat)
        db.session.commit()
        db.session.add(Message(chat_id=chat.id, sender='admin', text=text))
        db.session.commit()
        user = User.query.get(user_id)
        if user and user.telegram_chat_id:
            send_telegram_notification(user.telegram_chat_id, f"💬 <b>Новое сообщение от админа!</b>\n\n{text[:100]}..." if len(text) > 100 else text)
        return jsonify({"ok": True, "chat_id": chat.id})
    except Exception as e:
        print(f"Admin send error: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

# === ВИДЖЕТ (публичные эндпоинты с API ключом) ===

@app.route('/api/widget/chats', methods=['GET'])
def widget_get_chats():
    """Получение чатов для виджета (по API ключу сайта)"""
    try:
        api_key = request.headers.get('X-API-Key')
        print(f"🔍 Widget get_chats: api_key={api_key[:10] if api_key else None}")
        
        if not api_key:
            return jsonify({"error": "API key required"}), 401
        
        # Находим сайт по API ключу
        website = Website.query.filter_by(api_key=api_key, status='active', is_deleted=False).first()
        if not website:
            print(f"❌ Invalid API key: {api_key[:10] if api_key else None}")
            return jsonify({"error": "Invalid API key"}), 401
        
        # Получаем все чаты этого сайта
        chats = Chat.query.filter_by(website_id=website.id).order_by(Chat.created_at.desc()).all()
        
        result = []
        for c in chats:
            chat_name = c.visitor_name or f"Посетитель #{c.id}"
            result.append({
                "id": c.id,
                "site": chat_name,
                "status": c.status,
                "time": c.created_at.isoformat()
            })
        
        print(f"✅ Found {len(result)} chats")
        return jsonify(result)
    except Exception as e:
        print(f"❌ Widget get_chats error: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

@app.route('/api/widget/chats', methods=['POST'])
def widget_create_chat():
    """Создание нового чата для виджета"""
    try:
        api_key = request.headers.get('X-API-Key')
        print(f"🔍 Widget create_chat: api_key={api_key[:10] if api_key else None}")
        
        if not api_key:
            return jsonify({"error": "API key required"}), 401
        
        # Находим сайт по API ключу
        website = Website.query.filter_by(api_key=api_key, status='active', is_deleted=False).first()
        if not website:
            return jsonify({"error": "Invalid API key"}), 401
        
        # Создаём новый чат
        chat = Chat(website_id=website.id, status='waiting')
        db.session.add(chat)
        db.session.commit()
        
        # Уведомляем админа
        admin = User.query.filter_by(is_admin=True).first()
        if admin and admin.telegram_chat_id:
            send_telegram_notification(
                admin.telegram_chat_id,
                f"🔔 <b>Новый посетитель на сайте!</b>\n\n🔗 {website.url}\n\nЗайдите в CRM чтобы ответить."
            )
        
        print(f"✅ Created chat {chat.id}")
        return jsonify({"id": chat.id, "status": "waiting"})
    except Exception as e:
        print(f"❌ Widget create_chat error: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

@app.route('/api/widget/messages/<int:chat_id>', methods=['GET'])
def widget_get_messages(chat_id):
    """Получение сообщений для виджета"""
    try:
        api_key = request.headers.get('X-API-Key')
        
        if not api_key:
            return jsonify({"error": "API key required"}), 401
        
        # Проверяем что чат принадлежит сайту с этим API ключом
        chat = Chat.query.get(chat_id)
        if not chat:
            return jsonify({"error": "Chat not found"}), 404
        
        website = Website.query.filter_by(api_key=api_key, status='active', is_deleted=False).first()
        if not website or chat.website_id != website.id:
            return jsonify({"error": "Invalid API key"}), 401
        
        # Получаем сообщения
        msgs = Message.query.filter_by(chat_id=chat_id).order_by(Message.timestamp).all()
        
        return jsonify({
            "messages": [
                {
                    "sender": m.sender,
                    "text": m.text,
                    "time": m.timestamp.isoformat()
                } for m in msgs
            ],
            "form_requested": bool(chat.form_requested) if hasattr(chat, 'form_requested') else False
        })
    except Exception as e:
        print(f"❌ Widget get_messages error: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"messages": [], "form_requested": False}), 500

@app.route('/api/widget/send', methods=['POST', 'OPTIONS'])
def widget_send_message():
    """Отправка сообщения через виджет"""
    try:
        # Обработка preflight запроса
        if request.method == 'OPTIONS':
            return '', 204
        
        api_key = request.headers.get('X-API-Key')
        print(f"🔍 Widget send: api_key={api_key[:10] if api_key else None}")
        print(f"🔍 Request data: {request.data}")
        print(f"🔍 Request content-type: {request.content_type}")
        
        if not api_key:
            return jsonify({"error": "API key required"}), 401
        
        # Пробуем распарсить JSON
        try:
            data = request.get_json(force=True)
            print(f"🔍 Parsed data: {data}")
        except Exception as json_err:
            print(f"❌ JSON parse error: {json_err}")
            return jsonify({"error": f"Invalid JSON: {str(json_err)}"}), 400
        
        chat_id = data.get('chat_id')
        text = data.get('text', '')
        
        if not chat_id:
            return jsonify({"error": "chat_id required"}), 400
        
        # Проверяем чат
        chat = Chat.query.get(chat_id)
        if not chat:
            return jsonify({"error": "Chat not found"}), 404
        
        website = Website.query.filter_by(api_key=api_key, status='active', is_deleted=False).first()
        if not website or chat.website_id != website.id:
            return jsonify({"error": "Invalid API key"}), 401
        
        # Создаём сообщение
        msg = Message(chat_id=chat_id, sender='user', text=text)
        db.session.add(msg)
        db.session.commit()
        
        # Уведомляем админа
        admin = User.query.filter_by(is_admin=True).first()
        if admin and admin.telegram_chat_id:
            send_telegram_notification(
                admin.telegram_chat_id,
                f"💬 <b>Новое сообщение от посетителя!</b>\n\n{text[:100]}..." if len(text) > 100 else text
            )
        
        print(f"✅ Message sent in chat {chat_id}")
        return jsonify({"ok": True})
    except Exception as e:
        print(f"❌ Widget send_message error: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

@app.route('/api/widget/chat/<int:chat_id>/set_client_name', methods=['POST'])
def widget_set_client_name(chat_id):
    """Установка имени клиента из виджета"""
    try:
        api_key = request.headers.get('X-API-Key')
        print(f"🔍 Widget set_client_name: chat_id={chat_id}, api_key={api_key[:10] if api_key else None}")
        
        if not api_key:
            return jsonify({"error": "API key required"}), 401
        
        data = request.json
        name = data.get('name', '').strip()
        
        if not name:
            return jsonify({"error": "Name required"}), 400
        
        # Проверяем чат
        chat = Chat.query.get(chat_id)
        if not chat:
            print(f"❌ Chat {chat_id} not found")
            return jsonify({"error": "Chat not found"}), 404
        
        website = Website.query.filter_by(api_key=api_key, status='active', is_deleted=False).first()
        if not website or chat.website_id != website.id:
            print(f"❌ API key mismatch: chat.website_id={chat.website_id}, website.id={website.id if website else None}")
            return jsonify({"error": "Invalid API key"}), 401
        
        # Сохраняем имя
        chat.visitor_name = name
        db.session.commit()
        
        print(f"✅ Set name '{name}' for chat {chat_id}")
        return jsonify({"ok": True})
    except Exception as e:
        print(f"❌ Widget set_client_name error: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

@app.route('/api/widget/deals', methods=['POST'])
def widget_create_deal():
    """Создание заявки из виджета"""
    try:
        api_key = request.headers.get('X-API-Key')
        
        if not api_key:
            return jsonify({"error": "API key required"}), 401
        
        data = request.json
        chat_id = data.get('chat_id')
        
        if not chat_id:
            return jsonify({"error": "chat_id required"}), 400
        
        # Проверяем чат
        chat = Chat.query.get(chat_id)
        if not chat:
            return jsonify({"error": "Chat not found"}), 404
        
        website = Website.query.filter_by(api_key=api_key, status='active', is_deleted=False).first()
        if not website or chat.website_id != website.id:
            return jsonify({"error": "Invalid API key"}), 401
        
        # Валидация мессенджера
        is_valid, error = validate_contact_method(data.get('contact_method', ''))
        if not is_valid:
            return jsonify({"error": error}), 400
        
        # Создаём сделку
        deal = Deal(
            chat_id=chat_id,
            user_id=website.owner_id,
            client_name=data.get('client_name'),
            sphere=data.get('sphere'),
            request=data.get('request'),
            budget=data.get('budget'),
            contact_method=data.get('contact_method'),
            contact_nickname=data.get('contact_nickname'),
            status='completed'
        )
        db.session.add(deal)
        db.session.commit()
        
        # Уведомляем админа
        admin = User.query.filter_by(is_admin=True).first()
        if admin and admin.telegram_chat_id:
            send_telegram_notification(
                admin.telegram_chat_id,
                f"🎉 <b>Новая заявка с сайта!</b>\n\n"
                f"👤 Клиент: {deal.client_name}\n"
                f"💼 Сфера: {deal.sphere}\n"
                f"💰 Бюджет: {deal.budget}\n"
                f"📱 Контакт: {deal.contact_method} @{deal.contact_nickname}"
            )
        
        return jsonify({"ok": True, "deal_id": deal.id})
    except Exception as e:
        print(f"❌ Widget create_deal error: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

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
