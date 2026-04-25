import os, json, uuid, hashlib, datetime, secrets, requests
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import text
from openai import OpenAI

app = Flask(__name__, static_folder='static', static_url_path='/static')
CORS(app, supports_credentials=True, origins=["*"], allow_headers=["Content-Type", "Authorization", "X-API-Key"])

app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['MAX_CONTENT_LENGTH'] = 25 * 1024 * 1024
app.secret_key = os.environ.get('SECRET_KEY', secrets.token_hex(16))
db = SQLAlchemy(app)

client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
BOT_TOKEN = "8694190622:AAEVveNpF60fGx8wMl5ViJWawsdWAOqk9Yk"

def send_telegram_notification(chat_id, text):
    if not chat_id: return
    try:
        requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", json={"chat_id": chat_id, "text": text, "parse_mode": "HTML"})
    except Exception as e: print(f"Telegram error: {e}")

def validate_contact_method(method):
    allowed = ['telegram', 'vk', 'одноклассники', 'instagram', 'tenchat', 'тентенчат', 'ок', 'whatsapp', 'вайбер']
    blocked = ['max', 'макс', 'макс к', 'макс.к', 'max.k']
    method_lower = method.lower().strip()
    if method_lower in blocked: return False, "❌ Мессенджер MAX/МАКС запрещён."
    if method_lower not in allowed: return False, f"❌ '{method}' не в списке разрешённых."
    return True, None

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
    show_client_chats = db.Column(db.Boolean, default=True)

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
    is_archived = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)

class Message(db.Model):
    __tablename__ = 'message'
    id = db.Column(db.Integer, primary_key=True)
    chat_id = db.Column(db.Integer, db.ForeignKey('chat.id', ondelete='CASCADE'))
    sender = db.Column(db.String(20))
    text = db.Column(db.Text)
    file_url = db.Column(db.String(500))
    is_read = db.Column(db.Boolean, default=False)
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
    chat_id = db.Column(db.Integer, db.ForeignKey('chat.id', ondelete='CASCADE'))
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

# === ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ===
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

# === АВТОРИЗАЦИЯ ===
@app.route('/api/login', methods=['POST'])
def login():
    try:
        d = request.json; username = d.get('username', '').strip(); password = d.get('password', '')
        user = User.query.filter_by(username=username).first()
        if not user: return jsonify({"error": "Неверные данные"}), 401
        if not user.is_active: return jsonify({"error": "Аккаунт отключен"}), 401
        if user.password_hash != hash_pwd(password): return jsonify({"error": "Неверные данные"}), 401
        return jsonify({"ok": True, "token": user.api_token, "is_admin": user.is_admin, "username": user.username})
    except Exception as e: return jsonify({"error": "Ошибка сервера"}), 500

@app.route('/api/register', methods=['POST'])
def register():
    try:
        d = request.json; username = d.get('username', '').strip(); password = d.get('password', '')
        if not username or len(password) < 4: return jsonify({"error": "Логин мин. 2 символа, пароль мин. 4"}), 400
        if User.query.filter_by(username=username).first(): return jsonify({"error": "Пользователь существует"}), 409
        u = User(username=username, password_hash=hash_pwd(password)); db.session.add(u); db.session.commit()
        return jsonify({"ok": True, "token": u.api_token, "username": u.username})
    except Exception as e: return jsonify({"error": "Ошибка сервера"}), 500

# === ЗАГРУЗКА ФАЙЛОВ ===
@app.route('/api/upload', methods=['POST'])
@token_required
def upload_file():
    try:
        if 'file' not in request.files: return jsonify({"error": "Нет файла"}), 400
        file = request.files['file']
        if file.filename == '': return jsonify({"error": "Файл не выбран"}), 400
        allowed_ext = {'.jpg', '.jpeg', '.png', '.gif', '.webp', '.mp4', '.mov', '.avi', '.pdf'}
        _, ext = os.path.splitext(file.filename.lower())
        if ext not in allowed_ext: return jsonify({"error": "Неподдерживаемый формат"}), 400
        filename = f"{uuid.uuid4().hex}{ext}"
        upload_folder = os.path.join(app.static_folder, 'uploads')
        os.makedirs(upload_folder, exist_ok=True)
        file_path = os.path.join(upload_folder, filename)
        file.save(file_path)
        return jsonify({"url": f"/static/uploads/{filename}"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# === САЙТЫ ===
@app.route('/api/sites', methods=['GET'])
@token_required
def get_sites():
    try:
        u = request.current_user; show_deleted = request.args.get('show_deleted', 'false').lower() == 'true'
        if u.is_admin:
            query = Website.query
            if not show_deleted: query = query.filter_by(is_deleted=False)
            sites = query.all()
        else: sites = Website.query.filter_by(owner_id=u.id, is_deleted=False).all()
        return jsonify([{"id": s.id, "url": s.url, "api_key": s.api_key, "status": s.status, "owner": User.query.get(s.owner_id).username if s.owner_id else "Unknown", "owner_id": s.owner_id, "is_deleted": s.is_deleted, "deleted_at": s.deleted_at.isoformat() if s.deleted_at else None} for s in sites])
    except Exception as e: return jsonify([]), 500

@app.route('/api/sites', methods=['POST'])
@token_required
def add_site():
    try:
        url = request.json.get('url')
        if not url: return jsonify({"error": "URL обязателен"}), 400
        existing_site = Website.query.filter_by(url=url, is_deleted=False).first()
        if existing_site:
            if existing_site.owner_id == request.current_user.id: return jsonify({"error": "Этот сайт уже добавлен", "id": existing_site.id}), 400
            else: return jsonify({"error": "Этот сайт уже добавлен другим пользователем"}), 400
        key = f"site_{uuid.uuid4().hex[:8]}"; site = Website(url=url, api_key=key, owner_id=request.current_user.id, status='pending')
        db.session.add(site); db.session.commit()
        admin = User.query.filter_by(is_admin=True).first()
        if admin and admin.telegram_chat_id: send_telegram_notification(admin.telegram_chat_id, f"🔔 <b>Новый сайт на модерации!</b>\n\n👤 Владелец: {request.current_user.username}\n🔗 Сайт: {url}")
        return jsonify({"ok": True, "id": site.id})
    except Exception as e: return jsonify({"error": str(e)}), 500

@app.route('/api/sites/pending', methods=['GET'])
@admin_required
def get_pending_sites():
    try:
        sites = Website.query.filter_by(status='pending', is_deleted=False).all()
        return jsonify([{"id": s.id, "url": s.url, "api_key": s.api_key, "owner": User.query.get(s.owner_id).username if s.owner_id else "Unknown", "owner_id": s.owner_id, "created_at": s.created_at.isoformat()} for s in sites])
    except Exception as e: return jsonify([]), 500

@app.route('/api/sites/<int:site_id>/approve', methods=['POST'])
@admin_required
def approve_site_endpoint(site_id):
    try:
        site = Website.query.get(site_id)
        if not site: return jsonify({"error": "Сайт не найден"}), 404
        site.status = 'active'; db.session.commit()
        owner = User.query.get(site.owner_id)
        if owner and owner.telegram_chat_id: send_telegram_notification(owner.telegram_chat_id, f"✅ <b>Ваш сайт одобрен!</b>\n\n🔗 {site.url}")
        return jsonify({"ok": True})
    except Exception as e: return jsonify({"error": str(e)}), 500

@app.route('/api/sites/<int:site_id>/reject', methods=['POST'])
@admin_required
def reject_site(site_id):
    try:
        site = Website.query.get(site_id)
        if not site: return jsonify({"error": "Сайт не найден"}), 404
        db.session.delete(site); db.session.commit()
        return jsonify({"ok": True})
    except Exception as e: return jsonify({"error": str(e)}), 500

@app.route('/api/sites/<int:site_id>/delete', methods=['POST'])
@token_required
def delete_site(site_id):
    try:
        site = Website.query.get(site_id)
        if not site or (site.owner_id != request.current_user.id and not request.current_user.is_admin): return jsonify({"error": "Не найдено или нет прав"}), 404
        site.is_deleted = True; site.deleted_at = datetime.datetime.utcnow(); db.session.commit()
        return jsonify({"ok": True})
    except Exception as e: return jsonify({"error": str(e)}), 500

# === ЧАТЫ И СООБЩЕНИЯ (CRM) ===
@app.route('/api/chats', methods=['GET'])
@token_required
def get_chats():
    try:
        u = request.current_user
        query = Chat.query.filter_by(is_archived=False)
        if u.is_admin:
            if not u.show_client_chats:
                query = query.filter((Chat.user_id == None) | (Chat.user_id == u.id))
        else:
            query = query.filter_by(user_id=u.id)
        chats = query.order_by(Chat.created_at.desc()).all()
        result = []
        for c in chats:
            # ✅ ИСПРАВЛЕНО: Показываем имя пользователя (если есть) или "Пользователь ID"
            display_name = c.visitor_name or f"Пользователь #{c.id}"
            
            deal_status = ''
            deal = Deal.query.filter_by(chat_id=c.id).first()
            if deal:
                if deal.status == 'completed': deal_status = '✅ Сделка'
                elif deal.status == 'declined': deal_status = '❌ Отказ'
            
            result.append({
                "id": c.id, 
                "site": display_name, 
                "status": c.status, 
                "time": c.created_at.isoformat(), 
                "deal_status": deal_status
            })
        return jsonify(result)
    except Exception as e: 
        print(f"Get chats error: {e}")
        return jsonify([]), 500

@app.route('/api/chats/archived', methods=['GET'])
@token_required
def get_archived_chats():
    try:
        u = request.current_user
        if u.is_admin: chats = Chat.query.filter_by(is_archived=True).order_by(Chat.created_at.desc()).all()
        else: chats = Chat.query.filter_by(user_id=u.id, is_archived=True).order_by(Chat.created_at.desc()).all()
        result = []
        for c in chats:
            deal_status = ''
            deal = Deal.query.filter_by(chat_id=c.id).first()
            if deal:
                if deal.status == 'completed': deal_status = '✅ Сделка'
                elif deal.status == 'declined': deal_status = '❌ Отказ'
            result.append({"id": c.id, "site": c.visitor_name or "Клиент", "status": c.status, "time": c.created_at.isoformat(), "deal_status": deal_status})
        return jsonify(result)
    except Exception as e: return jsonify([]), 500

@app.route('/api/chats/<int:chat_id>/archive', methods=['POST'])
@token_required
def archive_chat(chat_id):
    try:
        chat = Chat.query.get(chat_id)
        if not chat: return jsonify({"error": "Чат не найден"}), 404
        if not request.current_user.is_admin and chat.user_id != request.current_user.id: return jsonify({"error": "Доступ запрещен"}), 403
        chat.is_archived = True; db.session.commit()
        return jsonify({"ok": True})
    except Exception as e: return jsonify({"error": str(e)}), 500

@app.route('/api/chats/<int:chat_id>/delete', methods=['POST'])
@token_required
def delete_chat(chat_id):
    try:
        chat = Chat.query.get(chat_id)
        if not chat: return jsonify({"error": "Чат не найден"}), 404
        if not request.current_user.is_admin and chat.user_id != request.current_user.id: return jsonify({"error": "Доступ запрещен"}), 403
        Deal.query.filter_by(chat_id=chat_id).delete()
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
        if not chat: return jsonify({"error": "Чат не найден"}), 404
        if not request.current_user.is_admin and chat.user_id != request.current_user.id: return jsonify({"error": "Доступ запрещен"}), 403
        Message.query.filter_by(chat_id=chat_id).update({Message.is_read: True}) 
        db.session.commit()
        msgs = Message.query.filter_by(chat_id=chat_id).order_by(Message.timestamp).all()
        return jsonify({
            "messages": [{"id": m.id, "sender":m.sender, "text":m.text, "file_url":m.file_url, "is_read":m.is_read, "time":m.timestamp.isoformat()} for m in msgs], 
            "form_requested": bool(chat.form_requested)
        })
    except Exception as e: 
        print(f"Get messages error: {e}")
        return jsonify({"messages": [], "form_requested": False}), 500

@app.route('/api/send', methods=['POST'])
@token_required
def send_message():
    try:
        d = request.json; sender = 'admin' if request.current_user.is_admin else 'user'
        text = d.get('text', ''); file_url = d.get('file_url', '')
        chat_id = d.get('chat_id')
        chat = Chat.query.get(chat_id)
        if not chat: return jsonify({"error": "Чат не найден"}), 404
        if not request.current_user.is_admin and chat.user_id != request.current_user.id: return jsonify({"error": "Доступ запрещен"}), 403
        msg = Message(chat_id=chat_id, sender=sender, text=text, file_url=file_url, is_read=False)
        db.session.add(msg); db.session.commit()
        if sender == 'admin' and chat.user_id:
            user = User.query.get(chat.user_id)
            if user and user.telegram_chat_id: send_telegram_notification(user.telegram_chat_id, f"💬 <b>Новое сообщение!</b>\n\n{text[:100]}")
        return jsonify({"ok": True})
    except Exception as e: return jsonify({"error": str(e)}), 500

# === AI АГЕНТЫ ===
@app.route('/api/ai/agents', methods=['GET'])
@token_required
def get_user_agents():
    try:
        agents = AIManager.query.filter_by(user_id=request.current_user.id).all()
        result = []
        for a in agents:
            pdfs = AIPDF.query.filter_by(agent_id=a.id).all(); link = AIWebsite.query.filter_by(agent_id=a.id).first(); website = Website.query.get(link.website_id) if link else None
            result.append({"id": a.id, "name": a.name, "behavior": a.behavior, "forbidden": a.forbidden, "knowledge_base": a.knowledge_base, "is_active_web": a.is_active_web, "is_active_telegram": a.is_active_telegram, "humanity_level": a.humanity_level, "pdfs": [{"id": p.id, "filename": p.filename} for p in pdfs], "linked_website": {"id": website.id, "url": website.url} if website else None, "created_at": a.created_at.isoformat()})
        return jsonify(result)
    except Exception as e: return jsonify([]), 500

@app.route('/api/ai/setup', methods=['POST'])
@token_required
def setup_ai():
    try:
        d = request.json; agent_count = AIManager.query.filter_by(user_id=request.current_user.id).count()
        if agent_count >= 10: return jsonify({"error": "Достигнут лимит: максимум 10 агентов"}), 400
        ai = AIManager(user_id=request.current_user.id, name=d.get('name','AI Assistant'), behavior=d.get('behavior',''), forbidden=d.get('forbidden',''), knowledge_base=d.get('knowledge_base',''), is_active_web=d.get('is_active_web',False), is_active_telegram=d.get('is_active_telegram',False), humanity_level=d.get('humanity_level', 3))
        db.session.add(ai); db.session.commit()
        return jsonify({"ok": True, "agent_id": ai.id})
    except Exception as e: return jsonify({"error": str(e)}), 500

@app.route('/api/ai/agents/<int:agent_id>', methods=['PUT'])
@token_required
def update_agent(agent_id):
    try:
        agent = AIManager.query.filter_by(id=agent_id, user_id=request.current_user.id).first()
        if not agent: return jsonify({"error": "Агент не найден"}), 404
        d = request.json; agent.name = d.get('name', agent.name); agent.behavior = d.get('behavior', agent.behavior); agent.forbidden = d.get('forbidden', agent.forbidden); agent.knowledge_base = d.get('knowledge_base', agent.knowledge_base); agent.humanity_level = d.get('humanity_level', agent.humanity_level)
        db.session.commit(); return jsonify({"ok": True})
    except Exception as e: return jsonify({"error": str(e)}), 500

@app.route('/api/ai/agents/<int:agent_id>/toggle', methods=['POST'])
@token_required
def toggle_agent(agent_id):
    try:
        agent = AIManager.query.filter_by(id=agent_id, user_id=request.current_user.id).first()
        if not agent: return jsonify({"error": "Агент не найден"}), 404
        agent.is_active_web = not agent.is_active_web; db.session.commit()
        return jsonify({"ok": True, "is_active": agent.is_active_web})
    except Exception as e: return jsonify({"error": str(e)}), 500

@app.route('/api/ai/agents/<int:agent_id>/delete', methods=['DELETE'])
@token_required
def delete_agent(agent_id):
    try:
        agent = AIManager.query.filter_by(id=agent_id, user_id=request.current_user.id).first()
        if not agent: return jsonify({"error": "Агент не найден"}), 404
        AIPDF.query.filter_by(agent_id=agent_id).delete(); AIWebsite.query.filter_by(agent_id=agent_id).delete(); db.session.delete(agent); db.session.commit()
        return jsonify({"ok": True})
    except Exception as e: return jsonify({"error": str(e)}), 500

@app.route('/api/ai/agents/<int:agent_id>/link_website', methods=['POST'])
@token_required
def link_agent_to_website(agent_id):
    try:
        d = request.json; website_id = d.get('website_id')
        agent = AIManager.query.filter_by(id=agent_id, user_id=request.current_user.id).first()
        if not agent: return jsonify({"error": "Агент не найден"}), 404
        website = Website.query.filter_by(id=website_id, owner_id=request.current_user.id).first()
        if not website: return jsonify({"error": "Сайт не найден"}), 404
        existing = AIWebsite.query.filter_by(agent_id=agent_id).first()
        if existing: return jsonify({"error": "Агент уже привязан к сайту"}), 400
        link = AIWebsite(agent_id=agent_id, website_id=website_id); db.session.add(link); db.session.commit()
        return jsonify({"ok": True})
    except Exception as e: return jsonify({"error": str(e)}), 500

@app.route('/api/ai/get', methods=['GET'])
@token_required
def get_ai():
    try:
        ai = AIManager.query.filter_by(user_id=request.current_user.id).first()
        if ai:
            pdfs = AIPDF.query.filter_by(agent_id=ai.id).all()
            return jsonify({"name": ai.name, "behavior": ai.behavior, "forbidden": ai.forbidden, "knowledge_base": ai.knowledge_base, "is_active_web": ai.is_active_web, "is_active_telegram": ai.is_active_telegram, "humanity_level": ai.humanity_level, "pdfs": [{"id": p.id, "filename": p.filename} for p in pdfs]})
        return jsonify({})
    except Exception as e: return jsonify({}), 500

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
        uploads_dir = os.path.join(app.static_folder, 'uploads', 'ai_pdfs'); os.makedirs(uploads_dir, exist_ok=True)
        filename = f"{uuid.uuid4().hex}_{file.filename}"; filepath = os.path.join(uploads_dir, filename)
        file.save(filepath); pdf = AIPDF(agent_id=agent_id, filename=file.filename, file_path=filepath)
        db.session.add(pdf); db.session.commit()
        return jsonify({"ok": True, "pdf_id": pdf.id, "filename": file.filename})
    except Exception as e: return jsonify({"error": str(e)}), 500

@app.route('/api/ai/delete_pdf/<int:pdf_id>', methods=['DELETE'])
@token_required
def delete_pdf(pdf_id):
    try:
        pdf = AIPDF.query.get(pdf_id)
        if not pdf: return jsonify({"error": "Файл не найден"}), 404
        agent = AIManager.query.get(pdf.agent_id)
        if agent and agent.user_id != request.current_user.id: return jsonify({"error": "Нет прав"}), 403
        if os.path.exists(pdf.file_path): os.remove(pdf.file_path)
        db.session.delete(pdf); db.session.commit()
        return jsonify({"ok": True})
    except Exception as e: return jsonify({"error": str(e)}), 500

# === СДЕЛКИ ===
@app.route('/api/deals', methods=['POST'])
@token_required
def create_deal():
    try:
        d = request.json; chat_id = d.get('chat_id')
        is_valid, error = validate_contact_method(d.get('contact_method', ''))
        if not is_valid: return jsonify({"error": error}), 400
        chat = Chat.query.get(chat_id)
        if not chat or chat.user_id != request.current_user.id: return jsonify({"error": "Чат не найден"}), 404
        deal = Deal(chat_id=chat_id, user_id=chat.user_id, client_name=d.get('client_name'), sphere=d.get('sphere'), request=d.get('request'), budget=d.get('budget'), contact_method=d.get('contact_method'), contact_nickname=d.get('contact_nickname'), status='completed')
        db.session.add(deal); db.session.commit()
        owner = User.query.get(chat.user_id)
        if owner and owner.telegram_chat_id: send_telegram_notification(owner.telegram_chat_id, f"🎉 <b>Новая сделка!</b>\n\n👤 {deal.client_name}\n💼 {deal.sphere}\n💰 {deal.budget}")
        return jsonify({"ok": True, "deal_id": deal.id})
    except Exception as e: return jsonify({"error": str(e)}), 500

@app.route('/api/deals', methods=['GET'])
@token_required
def get_deals():
    try:
        status = request.args.get('status', 'completed'); user = request.current_user
        deals = Deal.query.filter_by(user_id=user.id, status=status).order_by(Deal.created_at.desc()).all()
        return jsonify([{"id": d.id, "client_name": d.client_name, "sphere": d.sphere, "request": d.request, "budget": d.budget, "contact_method": d.contact_method, "contact_nickname": d.contact_nickname, "status": d.status, "decline_reason": d.decline_reason, "chat_id": d.chat_id, "created_at": d.created_at.isoformat()} for d in deals])
    except Exception as e: return jsonify([]), 500

@app.route('/api/deals/<int:deal_id>', methods=['DELETE'])
@token_required
def delete_deal(deal_id):
    try:
        deal = Deal.query.get(deal_id)
        if not deal or deal.user_id != request.current_user.id: return jsonify({"error": "Сделка не найдена"}), 404
        db.session.delete(deal); db.session.commit()
        return jsonify({"ok": True})
    except Exception as e: return jsonify({"error": str(e)}), 500

# === TELEGRAM И НАСТРОЙКИ ===
@app.route('/api/telegram/setup', methods=['POST'])
@token_required
def setup_tg():
    try:
        d = request.json; tb = TelegramBot.query.filter_by(user_id=request.current_user.id).first()
        if tb: tb.bot_token = d.get('token'); tb.is_active = d.get('active', False)
        else: tb = TelegramBot(user_id=request.current_user.id, bot_token=d.get('token'), is_active=d.get('active', False)); db.session.add(tb)
        db.session.commit(); return jsonify({"ok": True})
    except Exception as e: return jsonify({"error": str(e)}), 500

@app.route('/api/telegram/save_chat_id', methods=['POST'])
@token_required
def save_user_chat_id():
    try:
        request.current_user.telegram_chat_id = request.json.get('chat_id')
        db.session.commit()
        return jsonify({"ok": True, "message": "Chat ID сохранён"})
    except Exception as e: return jsonify({"error": str(e)}), 500

@app.route('/api/admin/get_settings', methods=['GET'])
@admin_required
def get_admin_settings():
    try:
        return jsonify({"show_client_chats": request.current_user.show_client_chats})
    except Exception as e: return jsonify({"error": str(e)}), 500

@app.route('/api/admin/update_settings', methods=['POST'])
@admin_required
def update_admin_settings():
    try:
        data = request.json
        if 'show_client_chats' in 
            request.current_user.show_client_chats = data['show_client_chats']
            db.session.commit()
        return jsonify({"ok": True})
    except Exception as e: return jsonify({"error": str(e)}), 500

@app.route('/api/change_password', methods=['POST'])
@token_required
def change_password():
    try:
        p = request.json.get('password')
        if not p or len(p) < 4: return jsonify({"error": "Минимум 4 символа"}), 400
        request.current_user.password_hash = hash_pwd(p); db.session.commit()
        return jsonify({"ok": True})
    except Exception as e: return jsonify({"error": "Ошибка"}), 500

@app.route('/api/admin/users', methods=['GET'])
@admin_required
def admin_users():
    try:
        users = User.query.order_by(User.created_at.desc()).all()
        return jsonify([{"id":u.id, "username":u.username, "created_at":u.created_at.isoformat(), "is_active":u.is_active, "is_admin":u.is_admin} for u in users])
    except Exception as e: return jsonify([]), 500

@app.route('/api/admin/toggle_user', methods=['POST'])
@admin_required
def toggle_user():
    try:
        u = User.query.get(request.json.get('user_id'))
        if u and u.username != request.current_user.username: u.is_active = not u.is_active; db.session.commit()
        return jsonify({"ok": True})
    except Exception as e: return jsonify({"error": "Ошибка"}), 500

# ✅ ИСПРАВЛЕННАЯ ФУНКЦИЯ ОТПРАВКИ СООБЩЕНИЯ АДМИНОМ (УБРАНЫ ДУБЛИ)
@app.route('/api/admin/send_to_user', methods=['POST'])
@admin_required
def admin_send_to_user():
    try:
        d = request.json; user_id = d.get('user_id'); text = d.get('text')
        if not user_id or not text: return jsonify({"error": "user_id и text обязательны"}), 400
        
        # ✅ ПРОВЕРКА: Есть ли уже активный чат с этим юзером?
        chat = Chat.query.filter_by(user_id=user_id, is_archived=False).first()
        
        # Если чата нет, создаем новый
        if not chat:
            chat = Chat(user_id=user_id, status='waiting')
            db.session.add(chat)
            db.session.commit()
        
        # Отправляем сообщение в существующий или новый чат
        db.session.add(Message(chat_id=chat.id, sender='admin', text=text))
        db.session.commit()
        
        user = User.query.get(user_id)
        if user and user.telegram_chat_id: send_telegram_notification(user.telegram_chat_id, f"💬 <b>Новое сообщение от админа!</b>\n\n{text[:100]}")
        return jsonify({"ok": True, "chat_id": chat.id})
    except Exception as e: return jsonify({"error": str(e)}), 500

@app.route('/api/admin/clear_deleted_sites', methods=['POST'])
@admin_required
def clear_deleted_sites():
    try:
        deleted_count = Website.query.filter_by(is_deleted=True).delete(synchronize_session=False)
        db.session.commit()
        return jsonify({"ok": True, "deleted": deleted_count})
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500

@app.route('/api/admin/restore_site', methods=['POST'])
@admin_required
def restore_site():
    try:
        site = Website.query.get(request.json.get('site_id'))
        if not site: return jsonify({"error": "Сайт не найден"}), 404
        if not site.is_deleted: return jsonify({"error": "Сайт не был удалён"}), 400
        site.is_deleted = False; site.deleted_at = None; site.status = 'active'; db.session.commit()
        return jsonify({"ok": True, "api_key": site.api_key, "message": "Сайт восстановлен"})
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500

# === ВИДЖЕТ (ПУБЛИЧНЫЕ ЭНДПОИНТЫ) ===
@app.route('/api/widget/chats', methods=['GET'])
def widget_get_chats():
    try:
        api_key = request.headers.get('X-API-Key')
        if not api_key: return jsonify({"error": "API key required"}), 401
        website = Website.query.filter_by(api_key=api_key, status='active', is_deleted=False).first()
        if not website: return jsonify({"error": "Invalid API key"}), 401
        chats = Chat.query.filter_by(website_id=website.id).order_by(Chat.created_at.desc()).all()
        return jsonify([{"id": c.id, "site": c.visitor_name or f"Посетитель #{c.id}", "status": c.status, "time": c.created_at.isoformat()} for c in chats])
    except Exception as e: return jsonify([]), 500

@app.route('/api/widget/chats', methods=['POST'])
def widget_create_chat():
    try:
        api_key = request.headers.get('X-API-Key')
        if not api_key: return jsonify({"error": "API key required"}), 401
        website = Website.query.filter_by(api_key=api_key, status='active', is_deleted=False).first()
        if not website: return jsonify({"error": "Invalid API key"}), 401
        chat = Chat(website_id=website.id, user_id=website.owner_id, status='waiting')
        db.session.add(chat); db.session.commit()
        owner = User.query.get(website.owner_id)
        if owner and owner.telegram_chat_id: send_telegram_notification(owner.telegram_chat_id, f"🔔 <b>Новый посетитель на {website.url}!</b>")
        return jsonify({"id": chat.id, "status": "waiting"})
    except Exception as e: return jsonify({"error": str(e)}), 500

@app.route('/api/widget/messages/<int:chat_id>', methods=['GET'])
def widget_get_messages(chat_id):
    try:
        api_key = request.headers.get('X-API-Key')
        if not api_key: return jsonify({"error": "API key required"}), 401
        chat = Chat.query.get(chat_id)
        if not chat: return jsonify({"error": "Chat not found"}), 404
        website = Website.query.filter_by(api_key=api_key, status='active', is_deleted=False).first()
        if not website or chat.website_id != website.id: return jsonify({"error": "Invalid API key"}), 401
        msgs = Message.query.filter_by(chat_id=chat_id).order_by(Message.timestamp).all()
        return jsonify({"messages": [{"sender": m.sender, "text": m.text, "file_url": m.file_url, "time": m.timestamp.isoformat()} for m in msgs], "form_requested": bool(chat.form_requested)})
    except Exception as e: return jsonify({"messages": [], "form_requested": False}), 500

@app.route('/api/widget/send', methods=['POST', 'OPTIONS'])
def widget_send_message():
    try:
        if request.method == 'OPTIONS': return '', 204
        api_key = request.headers.get('X-API-Key')
        if not api_key: return jsonify({"error": "API key required"}), 401
        try: data = request.get_json(force=True)
        except Exception as e: return jsonify({"error": f"Invalid JSON: {str(e)}"}), 400
        chat_id = data.get('chat_id'); text = data.get('text', '')
        if not chat_id: return jsonify({"error": "chat_id required"}), 400
        chat = Chat.query.get(chat_id)
        if not chat: return jsonify({"error": "Chat not found"}), 404
        website = Website.query.filter_by(api_key=api_key, status='active', is_deleted=False).first()
        if not website or chat.website_id != website.id: return jsonify({"error": "Invalid API key"}), 401
        msg = Message(chat_id=chat_id, sender='user', text=text); db.session.add(msg); db.session.commit()
        owner = User.query.get(website.owner_id)
        if owner and owner.telegram_chat_id: send_telegram_notification(owner.telegram_chat_id, f"💬 <b>Новое сообщение на {website.url}!</b>\n\n{text[:100]}")
        return jsonify({"ok": True})
    except Exception as e: return jsonify({"error": str(e)}), 500

@app.route('/api/widget/send_with_files', methods=['POST', 'OPTIONS'])
def widget_send_with_files():
    try:
        if request.method == 'OPTIONS': return '', 204
        api_key = request.headers.get('X-API-Key')
        if not api_key: return jsonify({"error": "API key required"}), 401
        chat_id = request.form.get('chat_id'); text = request.form.get('text', ''); files = request.files.getlist('files')
        chat = Chat.query.get(chat_id)
        if not chat: return jsonify({"error": "Chat not found"}), 404
        website = Website.query.filter_by(api_key=api_key, status='active', is_deleted=False).first()
        if not website or chat.website_id != website.id: return jsonify({"error": "Invalid API key"}), 401
        uploads_dir = os.path.join(app.static_folder, 'uploads'); os.makedirs(uploads_dir, exist_ok=True)
        for file in files:
            if file.filename:
                filename = f"{uuid.uuid4().hex}_{file.filename}"; filepath = os.path.join(uploads_dir, filename); file.save(filepath)
                msg = Message(chat_id=chat_id, sender='user', text=text, file_url=f"/static/uploads/{filename}"); db.session.add(msg)
        db.session.commit()
        owner = User.query.get(website.owner_id)
        if owner and owner.telegram_chat_id: send_telegram_notification(owner.telegram_chat_id, f"📎 <b>Новый файл на {website.url}!</b>")
        return jsonify({"ok": True})
    except Exception as e: return jsonify({"error": str(e)}), 500

@app.route('/api/widget/chat/<int:chat_id>/set_client_name', methods=['POST'])
def widget_set_client_name(chat_id):
    try:
        api_key = request.headers.get('X-API-Key')
        if not api_key: return jsonify({"error": "API key required"}), 401
        name = request.json.get('name', '').strip()
        if not name: return jsonify({"error": "Name required"}), 400
        chat = Chat.query.get(chat_id)
        if not chat: return jsonify({"error": "Chat not found"}), 404
        website = Website.query.filter_by(api_key=api_key, status='active', is_deleted=False).first()
        if not website or chat.website_id != website.id: return jsonify({"error": "Invalid API key"}), 401
        chat.visitor_name = name; db.session.commit()
        return jsonify({"ok": True})
    except Exception as e: return jsonify({"error": str(e)}), 500

@app.route('/api/widget/deals', methods=['POST'])
def widget_create_deal():
    try:
        api_key = request.headers.get('X-API-Key')
        if not api_key: return jsonify({"error": "API key required"}), 401
        data = request.json; chat_id = data.get('chat_id')
        if not chat_id: return jsonify({"error": "chat_id required"}), 400
        chat = Chat.query.get(chat_id)
        if not chat: return jsonify({"error": "Chat not found"}), 404
        website = Website.query.filter_by(api_key=api_key, status='active', is_deleted=False).first()
        if not website or chat.website_id != website.id: return jsonify({"error": "Invalid API key"}), 401
        is_valid, error = validate_contact_method(data.get('contact_method', ''))
        if not is_valid: return jsonify({"error": error}), 400
        deal = Deal(chat_id=chat_id, user_id=website.owner_id, client_name=data.get('client_name'), sphere=data.get('sphere'), request=data.get('request'), budget=data.get('budget'), contact_method=data.get('contact_method'), contact_nickname=data.get('contact_nickname'), status='completed')
        db.session.add(deal); db.session.commit()
        owner = User.query.get(website.owner_id)
        if owner and owner.telegram_chat_id: send_telegram_notification(owner.telegram_chat_id, f"🎉 <b>Новая заявка с {website.url}!</b>\n👤 {deal.client_name}\n💰 {deal.budget}")
        return jsonify({"ok": True, "deal_id": deal.id})
    except Exception as e: return jsonify({"error": str(e)}), 500

@app.route('/api/widget/capture_late_contact', methods=['POST'])
def widget_capture_late_contact():
    try:
        api_key = request.headers.get('X-API-Key')
        if not api_key: return jsonify({"error": "API key required"}), 401
        data = request.json; chat_id = data.get('chat_id')
        if not chat_id: return jsonify({"error": "chat_id required"}), 400
        chat = Chat.query.get(chat_id)
        if not chat: return jsonify({"error": "Chat not found"}), 404
        website = Website.query.filter_by(api_key=api_key, status='active', is_deleted=False).first()
        if not website or chat.website_id != website.id: return jsonify({"error": "Invalid API key"}), 401
        deal = Deal(chat_id=chat_id, user_id=website.owner_id, client_name=chat.visitor_name or 'Аноним', sphere='Запрос на подарок/позже', request='Клиент проявил интерес, но попросил связаться позже', budget='0', contact_method=data.get('contact_method', ''), contact_nickname=data.get('contact_nickname', ''), status='declined', decline_reason='Интерес есть, но позже (подарок)')
        db.session.add(deal); db.session.commit()
        owner = User.query.get(website.owner_id)
        if owner and owner.telegram_chat_id: send_telegram_notification(owner.telegram_chat_id, f"🎁 <b>Новый контакт (подарок)!</b>\n📱 {data.get('contact_method')} @{data.get('contact_nickname')}")
        return jsonify({"ok": True})
    except Exception as e: return jsonify({"error": str(e)}), 500

# === ДОПОЛНИТЕЛЬНЫЕ ЭНДПОИНТЫ (ДЛЯ CRM ИНТЕРФЕЙСА) ===

# ✅ Эндпоинт для индикатора "печатает" (CRM)
@app.route('/api/typing', methods=['POST'])
@token_required
def crm_typing():
    try:
        return jsonify({"ok": True})
    except Exception as e: 
        return jsonify({"error": str(e)}), 500

# ✅ Эндпоинт для отправки формы заявки (CRM)
@app.route('/api/chat/<int:chat_id>/request_form', methods=['POST'])
@token_required
def request_form(chat_id):
    try:
        chat = Chat.query.get(chat_id)
        if not chat: return jsonify({"error": "Чат не найден"}), 404
        if not request.current_user.is_admin and chat.user_id != request.current_user.id:
            return jsonify({"error": "Доступ запрещен"}), 403
        
        chat.form_requested = True
        db.session.commit()
        return jsonify({"ok": True})
    except Exception as e: 
        return jsonify({"error": str(e)}), 500

# === ЗАПУСК ===
with app.app_context():
    db.create_all()
    admin = User.query.filter_by(username='Kristina').first()
    if not admin: admin = User(username='Kristina', is_admin=True); db.session.add(admin)
    admin.is_active = True; admin.password_hash = hash_pwd('zaqqaz'); db.session.commit()
    print("✅ Admin Kristina: ACTIVE | Password: zaqqaz")

@app.route('/', defaults={'path': 'index.html'})
@app.route('/<path:path>')
def serve_static(path):
    return send_from_directory(app.static_folder, path)

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port, debug=True)
