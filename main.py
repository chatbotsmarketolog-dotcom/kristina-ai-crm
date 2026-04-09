import os, json, sqlite3, uuid, time, requests
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request, HTTPException, Depends
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
import jwt, hashlib, secrets

app = FastAPI(title="КРИСТИНА.AI CRM")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

SECRET_KEY = secrets.token_urlsafe(32)
DB = "crm.db"
APP_URL = os.getenv("APP_URL", "https://kristina-ai-crm.onrender.com")

# 🔔 TELEGRAM УВЕДОМЛЕНИЯ
TELEGRAM_BOT_TOKEN = "8694190622:AAEVveNpF60fGx8wMl5ViJWawsdWAOqk9Yk"
TELEGRAM_CHAT_ID = "6300678737"

def db():
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn

def init_db():
    conn = db()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY, username TEXT UNIQUE, password_hash TEXT, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP);
        CREATE TABLE IF NOT EXISTS websites (id INTEGER PRIMARY KEY, url TEXT UNIQUE, api_key TEXT UNIQUE, owner_id TEXT, status TEXT DEFAULT 'pending', created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, FOREIGN KEY(owner_id) REFERENCES users(username));
        CREATE TABLE IF NOT EXISTS chats (id INTEGER PRIMARY KEY, website_id INTEGER, visitor_id TEXT, status TEXT DEFAULT 'waiting', operator_id TEXT, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, FOREIGN KEY(website_id) REFERENCES websites(id));
        CREATE TABLE IF NOT EXISTS messages (id INTEGER PRIMARY KEY, chat_id INTEGER, sender TEXT, text TEXT, timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP, FOREIGN KEY(chat_id) REFERENCES chats(id));
    """)
    conn.commit(); conn.close()
init_db()

def hash_pwd(p): return hashlib.sha256((p + "crm_salt_2026").encode()).hexdigest()
def create_token(username: str):
    return jwt.encode({"sub": username, "exp": time.time() + 86400*30}, SECRET_KEY, algorithm="HS256")
def verify_token(token: str):
    try: return jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
    except: return None

def get_owner_id(req: Request):
    t = req.headers.get("Authorization","").replace("Bearer ","")
    d = verify_token(t)
    if not d: raise HTTPException(401, "Не авторизован")
    return d["sub"]

def send_telegram(domain, api_key):
    try:
        text = f"🔔 *Новый сайт в КРИСТИНА.AI CRM*\n\n🌐 {domain}\n🔑 `{api_key}`\n\n✅ Подтверди: {APP_URL}/admin/pending-sites"
        requests.post(f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage", json={"chat_id": TELEGRAM_CHAT_ID, "text": text, "parse_mode": "Markdown"}, timeout=5)
    except Exception as e: print(f"Telegram error: {e}")

class ConnManager:
    def __init__(self): self.visitors, self.operators = {}, {}
    async def add_vis(self, ws, cid): await ws.accept(); self.visitors[cid] = ws
    async def add_op(self, ws, oid): await ws.accept(); self.operators[oid] = ws
    def rem_vis(self, cid): self.visitors.pop(cid, None)
    def rem_op(self, oid): self.operators.pop(oid, None)
    async def notify_ops(self, owner_id, data):
        dead = []
        for o, w in self.operators.items():
            if o == owner_id:
                try: await w.send_json(data)
                except: dead.append(o)
        for o in dead: self.operators.pop(o)
    async def to_vis(self, cid, data):
        if cid in self.visitors: await self.visitors[cid].send_json(data)

mgr = ConnManager()

# === HTML ROUTES ===
@app.get("/", response_class=HTMLResponse)
async def root(): return open("login.html", "r", encoding="utf-8").read()
@app.get("/login", response_class=HTMLResponse)
async def login_page(): return open("login.html", "r", encoding="utf-8").read()
@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard_page(): return open("dashboard.html", "r", encoding="utf-8").read()
@app.get("/settings", response_class=HTMLResponse)
async def settings_page(): return open("settings.html", "r", encoding="utf-8").read()
@app.get("/widget/{site_key}", response_class=HTMLResponse)
async def widget_page(site_key: str): return open("widget.html", "r", encoding="utf-8").read()

@app.get("/admin/pending-sites", response_class=HTMLResponse)
async def pending_sites_page():
    conn = db()
    sites = conn.execute("SELECT id, url, api_key, created_at FROM websites WHERE status='pending' ORDER BY created_at DESC").fetchall()
    conn.close()
    rows = "".join([f"<tr><td>{s['url']}</td><td><code>{s['api_key']}</code></td><td><button onclick=\"approve('{s['api_key']}')\" style=\"background:#22c55e;color:#fff;border:none;padding:6px 12px;border-radius:6px;cursor:pointer\">✅ Подтвердить</button></td></tr>" for s in sites])
    return HTMLResponse(f"""<!DOCTYPE html><html><head><meta charset="UTF-8"><title>Подтверждение | КРИСТИНА.AI CRM</title>
    <style>body{{font-family:system-ui;padding:40px;background:#0b132b;color:#e2e8f0}}table{{width:100%;border-collapse:collapse;margin-top:20px}}th,td{{padding:12px;text-align:left;border-bottom:1px solid rgba(255,255,255,0.1)}}code{{background:rgba(0,0,0,0.3);padding:4px 8px;border-radius:4px}}</style>
    <script>function approve(key){{fetch('/api/approve-site',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({api_key:key})}}).then(()=>location.reload())}}</script></head><body>
    <h1>🔔 Новые сайты в КРИСТИНА.AI CRM</h1><table><thead><tr><th>Сайт</th><th>API-ключ</th><th>Действие</th></tr></thead><tbody>{rows or '<tr><td colspan="3">Нет новых сайтов</td></tr>'}</tbody></table>
    <p style="margin-top:20px"><a href="/dashboard" style="color:#93c5fd">← В панель</a></p></body></html>""")

# === AUTH ===
@app.post("/auth/register")
async def register(req: Request):
    d = await req.json()
    u, p = d.get("username","").strip(), d.get("password","")
    if len(u)<2 or len(p)<4: return {"error":"Мин. 2 символа логин, 4 пароль"}, 400
    conn = db()
    try:
        conn.execute("INSERT INTO users (username, password_hash) VALUES (?,?)", (u, hash_pwd(p)))
        conn.commit(); return {"token": create_token(u)}
    except: return {"error":"Логин занят"}, 409
    finally: conn.close()

@app.post("/auth/login")
async def login(req: Request):
    d = await req.json()
    u, p = d.get("username","").strip(), d.get("password","")
    conn = db()
    row = conn.execute("SELECT id FROM users WHERE username=? AND password_hash=?", (u, hash_pwd(p))).fetchone()
    conn.close()
    if not row: return {"error":"Неверные данные"}, 401
    return {"token": create_token(u)}

# === SITES & AUTO-REG ===
@app.post("/api/websites")
async def add_site(req: Request, owner: str = Depends(get_owner_id)):
    d = await req.json(); url = d.get("url","").strip()
    if not url: return {"error":"Укажите URL"}, 400
    key = f"site_{uuid.uuid4().hex[:8]}"
    conn = db(); conn.execute("INSERT INTO websites (url, api_key, owner_id) VALUES (?,?,?)", (url, key, owner)); conn.commit(); conn.close()
    return {"url": url, "api_key": key}

@app.get("/api/websites")
async def get_sites(req: Request, owner: str = Depends(get_owner_id)):
    conn = db(); rows = conn.execute("SELECT * FROM websites WHERE owner_id=? ORDER BY created_at DESC", (owner,)).fetchall(); conn.close()
    return [dict(r) for r in rows]

@app.post("/api/auto-register")
async def auto_register(req: Request):
    d = await req.json()
    domain = d.get("domain", "").lower()
    url = d.get("url", f"https://{domain}")
    if not domain: return {"error": "Domain required"}, 400
    conn = db()
    existing = conn.execute("SELECT id, api_key, status FROM websites WHERE url LIKE ?", (f"%{domain}%",)).fetchone()
    if existing:
        status = "active" if existing["status"] != "pending" else "pending"
        conn.close()
        return {"status": status, "api_key": existing["api_key"]}
    api_key = f"site_{uuid.uuid4().hex[:8]}"
    conn.execute("INSERT INTO websites (url, api_key, owner_id, status) VALUES (?, ?, 'auto-owner', 'pending')", (url, api_key))
    conn.commit(); conn.close()
    send_telegram(domain, api_key)
    return {"status": "pending", "message": "Отправлено на подтверждение"}

@app.get("/api/widget-status")
async def widget_status(domain: str):
    conn = db()
    site = conn.execute("SELECT api_key, status FROM websites WHERE url LIKE ? ORDER BY created_at DESC LIMIT 1", (f"%{domain}%",)).fetchone()
    conn.close()
    if not site or site["status"] != "active": return {"active": False}
    return {"active": True, "embed_url": f"{APP_URL}/widget/{site['api_key']}"}

@app.post("/api/approve-site")
async def approve_site(req: Request):
    d = await req.json()
    api_key = d.get("api_key")
    if not api_key: return {"error": "api_key required"}, 400
    conn = db(); conn.execute("UPDATE websites SET status='active', owner_id='approved' WHERE api_key=?", (api_key,))
    conn.commit(); conn.close()
    return {"ok": True}

# === CHATS ===
@app.post("/api/chat/{site_key}")
async def new_chat(site_key: str):
    conn = db()
    site = conn.execute("SELECT id, owner_id FROM websites WHERE api_key=?", (site_key,)).fetchone()
    if not site: conn.close(); return {"error":"Сайт не найден"}, 404
    vid = f"v_{uuid.uuid4().hex[:6]}"
    cur = conn.execute("INSERT INTO chats (website_id, visitor_id) VALUES (?,?)", (site["id"], vid))
    conn.commit(); cid = cur.lastrowid; conn.close()
    await mgr.notify_ops(site["owner_id"], {"type":"new", "chat_id":cid, "visitor":vid, "site_key":site_key})
    return {"chat_id": cid, "visitor_id": vid}

@app.get("/api/chats")
async def get_chats(req: Request, owner: str = Depends(get_owner_id)):
    conn = db()
    rows = conn.execute("SELECT c.*, w.url as site_url FROM chats c LEFT JOIN websites w ON c.website_id=w.id WHERE w.owner_id=? ORDER BY c.created_at DESC", (owner,)).fetchall()
    conn.close(); return [dict(r) for r in rows]

@app.get("/api/messages/{chat_id}")
async def get_msgs(chat_id: int, req: Request, owner: str = Depends(get_owner_id)):
    conn = db()
    chat = conn.execute("SELECT id FROM chats c JOIN websites w ON c.website_id=w.id WHERE c.id=? AND w.owner_id=?", (chat_id, owner)).fetchone()
    if not chat: conn.close(); raise HTTPException(403, "Доступ запрещён")
    rows = conn.execute("SELECT * FROM messages WHERE chat_id=? ORDER BY timestamp ASC", (chat_id,)).fetchall()
    conn.close(); return [dict(r) for r in rows]

@app.post("/api/accept/{chat_id}")
async def accept(chat_id: int, req: Request, owner: str = Depends(get_owner_id)):
    conn = db(); conn.execute("UPDATE chats SET status='active', operator_id=? WHERE id=?", (owner, chat_id)); conn.commit(); conn.close()
    await mgr.to_vis(chat_id, {"type":"system", "text":"Менеджер подключился"})
    return {"ok": True}

# === WEBSOCKETS ===
@app.websocket("/ws/visitor/{chat_id}")
async def ws_vis(ws: WebSocket, chat_id: int):
    await mgr.add_vis(ws, chat_id)
    try:
        while True:
            raw = await ws.receive_text(); d = json.loads(raw)
            conn = db()
            owner_row = conn.execute("SELECT w.owner_id FROM chats c JOIN websites w ON c.website_id=w.id WHERE c.id=?", (chat_id,)).fetchone()
            conn.execute("INSERT INTO messages (chat_id, sender, text) VALUES (?,?,?)", (chat_id, "visitor", d["text"])); conn.commit(); conn.close()
            if owner_row: await mgr.notify_ops(owner_row["owner_id"], {"type":"msg", "chat_id":chat_id, "sender":"visitor", "text":d["text"]})
    except WebSocketDisconnect: 
        mgr.rem_vis(chat_id)
        conn = db()
        owner_row = conn.execute("SELECT w.owner_id FROM chats c JOIN websites w ON c.website_id=w.id WHERE c.id=?", (chat_id,)).fetchone()
        conn.close()
        if owner_row: await mgr.notify_ops(owner_row["owner_id"], {"type":"system", "chat_id":chat_id, "text":"Посетитель покинул чат"})

@app.websocket("/ws/operator")
async def ws_op(ws: WebSocket, token: str = None):
    if not token or not verify_token(token): await ws.close(1008); return
    d = verify_token(token)
    await mgr.add_op(ws, d["sub"])
    try:
        while True:
            raw = await ws.receive_text(); d_msg = json.loads(raw)
            conn = db()
            conn.execute("INSERT INTO messages (chat_id, sender, text) VALUES (?,?,?)", (d_msg["chat_id"], "operator", d_msg["text"])); conn.commit(); conn.close()
            await mgr.to_vis(d_msg["chat_id"], {"type":"msg", "chat_id":d_msg["chat_id"], "sender":"operator", "text":d_msg["text"]})
    except WebSocketDisconnect: mgr.rem_op(d["sub"])