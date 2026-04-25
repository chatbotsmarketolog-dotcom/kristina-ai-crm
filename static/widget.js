// КРИСТИНА.AI CRM Widget v3.2
(function() {
    'use strict';
    
    const API_URL = window.KRISTINA_API_URL || 'https://kristina-crm-api.onrender.com';
    const API_KEY = window.KRISTINA_API_KEY;
    
    if (!API_KEY) { console.error('❌ KRISTINA_API_KEY не указан!'); return; }

    let chatId = localStorage.getItem('kristina_chat_id') || null;
    let messages = [], formRequested = false, userName = localStorage.getItem('kristina_user_name') || '';
    let selectedFiles = [], isOpen = false;

    const styles = `
        <style>
            @keyframes kFadeIn { from { opacity: 0; transform: translateY(10px); } to { opacity: 1; transform: translateY(0); } }
            #kristinaWidgetBtn {
                position: fixed !important; bottom: 24px !important; right: 24px !important;
                background: linear-gradient(135deg, #3b82f6 0%, #2563eb 100%) !important;
                color: white !important; padding: 14px 20px !important; border-radius: 50px !important;
                box-shadow: 0 4px 14px rgba(59, 130, 246, 0.4) !important; cursor: pointer !important;
                font-family: system-ui, -apple-system, sans-serif !important; font-weight: 600 !important;
                font-size: 14px !important; z-index: 2147483647 !important; transition: all 0.2s ease !important;
                border: none !important; display: flex !important; align-items: center !important; gap: 8px !important;
            }
            #kristinaWidgetBtn:hover { transform: translateY(-2px) !important; box-shadow: 0 6px 20px rgba(59, 130, 246, 0.6) !important; }
            #kristinaWidgetBtn::before { content: '💬' !important; font-size: 18px !important; }
            
            #kristinaChatWindow {
                position: fixed !important; bottom: 84px !important; right: 24px !important;
                width: 380px !important; max-width: calc(100vw - 48px) !important; height: 560px !important;
                max-height: calc(100vh - 108px) !important; background: #1e293b !important;
                border-radius: 16px !important; box-shadow: 0 20px 40px rgba(0, 0, 0, 0.4) !important;
                z-index: 2147483647 !important; display: none !important; flex-direction: column !important;
                overflow: hidden !important; border: 1px solid rgba(255, 255, 255, 0.1) !important;
                font-family: system-ui, -apple-system, sans-serif !important;
            }
            #kristinaChatWindow.active { display: flex !important; animation: kFadeIn 0.3s ease !important; }
            
            #kristinaChatHeader {
                background: linear-gradient(135deg, #3b82f6 0%, #2563eb 100%) !important;
                padding: 16px !important; color: white !important; display: flex !important;
                justify-content: space-between !important; align-items: center !important; flex-shrink: 0 !important;
            }
            #kristinaChatHeader h3 { margin: 0 !important; font-size: 16px !important; font-weight: 600 !important; }
            #kristinaChatClose {
                background: rgba(255, 255, 255, 0.2) !important; border: none !important; color: white !important;
                width: 28px !important; height: 28px !important; border-radius: 50% !important;
                cursor: pointer !important; font-size: 16px !important; display: flex !important;
                align-items: center !important; justify-content: center !important; transition: background 0.2s !important;
            }
            #kristinaChatClose:hover { background: rgba(255, 255, 255, 0.3) !important; }
            
            #kristinaChatMessages {
                flex: 1 !important; overflow-y: auto !important; padding: 16px !important;
                display: flex !important; flex-direction: column !important; gap: 12px !important;
                background: #1e293b !important; scroll-behavior: smooth !important;
            }
            #kristinaChatMessages::-webkit-scrollbar { width: 6px !important; }
            #kristinaChatMessages::-webkit-scrollbar-thumb { background: rgba(255, 255, 255, 0.2) !important; border-radius: 3px !important; }
            
            .k-msg {
                max-width: 85% !important; padding: 12px 16px !important; border-radius: 16px !important;
                font-size: 14px !important; line-height: 1.4 !important; animation: kFadeIn 0.2s ease !important;
                word-wrap: break-word !important; position: relative !important;
            }
            .k-msg-user {
                background: linear-gradient(135deg, #10b981 0%, #059669 100%) !important;
                color: white !important; align-self: flex-end !important;
                border-bottom-right-radius: 4px !important;
            }
            .k-msg-admin {
                background: rgba(255, 255, 255, 0.1) !important; color: #e2e8f0 !important;
                align-self: flex-start !important; border-bottom-left-radius: 4px !important;
            }
            .k-msg-file {
                background: rgba(255, 255, 255, 0.1) !important; border: 1px solid rgba(255, 255, 255, 0.2) !important;
                padding: 8px 12px !important; border-radius: 12px !important; margin-top: 8px !important;
            }
            .k-msg-file img, .k-msg-file video {
                max-width: 100% !important; border-radius: 8px !important; margin-top: 4px !important;
            }
            .k-file-link {
                color: #60a5fa !important; text-decoration: none !important; display: inline-flex !important;
                align-items: center !important; gap: 6px !important; font-size: 13px !important;
            }
            
            #kristinaChatInputWrapper {
                padding: 12px 16px !important; background: rgba(30, 41, 59, 0.95) !important;
                border-top: 1px solid rgba(255, 255, 255, 0.1) !important; flex-shrink: 0 !important;
            }
            #kristinaAttachedFiles {
                display: flex !important; gap: 6px !important; margin-bottom: 8px !important; flex-wrap: wrap !important;
            }
            .k-file-tag {
                background: rgba(59, 130, 246, 0.2) !important; color: #93c5fd !important;
                padding: 4px 10px !important; border-radius: 16px !important; font-size: 11px !important;
                display: flex !important; align-items: center !important; gap: 6px !important;
            }
            .k-file-tag .k-remove { cursor: pointer !important; opacity: 0.7 !important; font-weight: bold !important; }
            .k-file-tag .k-remove:hover { opacity: 1 !important; }
            
            #kristinaChatInputRow { display: flex !important; gap: 8px !important; align-items: center !important; }
            #kristinaChatInput {
                flex: 1 !important; padding: 12px 16px !important; border-radius: 24px !important;
                border: 1px solid rgba(255, 255, 255, 0.2) !important; background: rgba(255, 255, 255, 0.1) !important;
                color: #e2e8f0 !important; font-family: inherit !important; font-size: 14px !important;
                outline: none !important; transition: border-color 0.2s !important;
            }
            #kristinaChatInput:focus { border-color: #3b82f6 !important; }
            #kristinaChatInput::placeholder { color: rgba(226, 232, 240, 0.5) !important; }
            
            #kristinaFileBtn {
                background: rgba(59, 130, 246, 0.2) !important; color: #60a5fa !important;
                border: 1px solid rgba(59, 130, 246, 0.3) !important; width: 40px !important;
                height: 40px !important; border-radius: 50% !important; cursor: pointer !important;
                display: flex !important; align-items: center !important; justify-content: center !important;
                font-size: 18px !important; transition: all 0.2s !important; flex-shrink: 0 !important;
            }
            #kristinaFileBtn:hover { background: rgba(59, 130, 246, 0.3) !important; transform: scale(1.05) !important; }
            
            #kristinaSendBtn {
                background: linear-gradient(135deg, #3b82f6 0%, #2563eb 100%) !important; color: white !important;
                border: none !important; padding: 12px 20px !important; border-radius: 24px !important;
                cursor: pointer !important; font-weight: 600 !important; transition: all 0.2s !important;
                flex-shrink: 0 !important; font-size: 14px !important;
            }
            #kristinaSendBtn:hover { transform: scale(1.05) !important; }
            #kristinaSendBtn:disabled { opacity: 0.5 !important; cursor: not-allowed !important; transform: none !important; }
            
            .k-form {
                position: fixed !important; bottom: 84px !important; right: 24px !important;
                width: 380px !important; max-width: calc(100vw - 48px) !important;
                background: #1e293b !important; border-radius: 16px !important;
                box-shadow: 0 20px 40px rgba(0, 0, 0, 0.4) !important; z-index: 2147483647 !important;
                display: none !important; flex-direction: column !important; overflow: hidden !important;
                border: 1px solid rgba(255, 255, 255, 0.1) !important; font-family: inherit !important;
                animation: kFadeIn 0.3s ease !important;
            }
            .k-form.active { display: flex !important; }
            
            .k-form-header {
                background: linear-gradient(135deg, #10b981 0%, #059669 100%) !important;
                padding: 16px !important; color: white !important; display: flex !important;
                justify-content: space-between !important; align-items: center !important; flex-shrink: 0 !important;
            }
            .k-form-header h3 { margin: 0 !important; font-size: 16px !important; font-weight: 600 !important; }
            .k-form-content { padding: 16px !important; overflow-y: auto !important; flex: 1 !important; }
            .k-form-group { margin-bottom: 14px !important; }
            .k-form-group label {
                display: block !important; color: #94a3b8 !important; margin-bottom: 6px !important;
                font-size: 12px !important; font-weight: 500 !important; text-transform: uppercase !important; letter-spacing: 0.5px !important;
            }
            .k-form-group input, .k-form-group textarea, .k-form-group select {
                width: 100% !important; padding: 10px 14px !important; border-radius: 10px !important;
                border: 1px solid rgba(255, 255, 255, 0.2) !important; background: rgba(255, 255, 255, 0.1) !important;
                color: #e2e8f0 !important; font-family: inherit !important; font-size: 14px !important;
                box-sizing: border-box !important; transition: border-color 0.2s !important;
            }
            .k-form-group input:focus, .k-form-group textarea:focus, .k-form-group select:focus {
                border-color: #10b981 !important; outline: none !important;
            }
            .k-form-group textarea { resize: vertical !important; min-height: 70px !important; }
            .k-form-buttons { display: flex !important; gap: 8px !important; margin-top: 20px !important; }
            .k-btn {
                flex: 1 !important; padding: 12px !important; border: none !important; border-radius: 10px !important;
                cursor: pointer !important; font-weight: 600 !important; font-size: 13px !important;
                transition: transform 0.2s !important;
            }
            .k-btn:hover { transform: translateY(-1px) !important; }
            .k-btn-cancel { background: rgba(239, 68, 68, 0.2) !important; color: #f87171 !important; }
            .k-btn-submit { background: linear-gradient(135deg, #10b981 0%, #059669 100%) !important; color: white !important; }
            
            /* ✅ ИСПРАВЛЕНО: АДАПТИВНОСТЬ ПОД МОБИЛЬНЫЕ */
            @media (max-width: 480px) {
                #kristinaWidgetBtn { bottom: 16px !important; right: 16px !important; padding: 12px 18px !important; font-size: 13px !important; }
                #kristinaChatWindow, .k-form {
                    bottom: 72px !important; right: 16px !important; left: 16px !important;
                    width: calc(100% - 32px) !important; max-width: none !important;
                    height: calc(100vh - 96px) !important; max-height: none !important;
                    border-radius: 14px !important;
                }
                #kristinaChatMessages { padding: 12px !important; }
                .k-msg { max-width: 90% !important; font-size: 13px !important; padding: 10px 14px !important; }
                #kristinaChatInputWrapper { padding: 10px 14px !important; }
                #kristinaChatInputRow { flex-wrap: wrap !important; }
                #kristinaFileBtn { width: 36px !important; height: 36px !important; order: 1 !important; }
                #kristinaChatInput { flex: 1 1 calc(100% - 90px) !important; order: 2 !important; min-width: 0 !important; }
                #kristinaSendBtn { order: 3 !important; padding: 10px 18px !important; font-size: 13px !important; }
            }
        </style>
    `;

    const widgetHTML = `
        <button id="kristinaWidgetBtn">Онлайн менеджер</button>
        
        <div id="kristinaChatWindow">
            <div id="kristinaChatHeader">
                <h3>💬 КРИСТИНА.AI CRM</h3>
                <button id="kristinaChatClose">×</button>
            </div>
            <div id="kristinaChatMessages"><div style="text-align:center;padding:40px;opacity:0.6;color:#94a3b8">💬 Начните общение...</div></div>
            <div id="kristinaChatInputWrapper">
                <div id="kristinaAttachedFiles"></div>
                <div id="kristinaChatInputRow">
                    <input type="file" id="kristinaFileInput" multiple accept=".pdf,.jpg,.jpeg,.png,.gif,.webp,.mp4,.mov">
                    <button id="kristinaFileBtn" title="Прикрепить файл">📎</button>
                    <input type="text" id="kristinaChatInput" placeholder="Введите сообщение...">
                    <button id="kristinaSendBtn">Отправить</button>
                </div>
            </div>
        </div>
        
        <div class="k-form" id="kristinaDealForm">
            <div class="k-form-header"><h3>📋 Заявка на встречу</h3><button id="kristinaFormClose">×</button></div>
            <div class="k-form-content">
                <div class="k-form-group"><label>Имя *</label><input type="text" id="dealClientName" required></div>
                <div class="k-form-group"><label>Сфера *</label><input type="text" id="dealSphere" placeholder="Например: маркетинг" required></div>
                <div class="k-form-group"><label>Запрос *</label><textarea id="dealRequest" placeholder="Что хотите обсудить?" required></textarea></div>
                <div class="k-form-group"><label>Бюджет *</label><input type="text" id="dealBudget" placeholder="15 000 ₽" required></div>
                <div class="k-form-group"><label>Контакт *</label>
                    <select id="dealContactMethod" required>
                        <option value="">Выберите</option>
                        <option value="Telegram">Telegram</option><option value="VK">ВКонтакте</option>
                        <option value="Одноклассники">Одноклассники</option><option value="Instagram">Instagram</option>
                        <option value="TenChat">TenChat</option>
                    </select>
                </div>
                <div class="k-form-group"><label>Никнейм *</label><input type="text" id="dealContactNickname" placeholder="@username" required></div>
                <div class="k-form-buttons">
                    <button class="k-btn k-btn-cancel" id="kristinaFormCancel">Отмена</button>
                    <button class="k-btn k-btn-submit" id="kristinaFormSubmit">✅ Подтвердить</button>
                </div>
            </div>
        </div>
        
        <div class="k-form" id="kristinaNameForm">
            <div class="k-form-header"><h3>👋 Привет!</h3></div>
            <div class="k-form-content">
                <div class="k-form-group"><label>Как к вам обращаться? *</label><input type="text" id="userNameInput" placeholder="Ваше имя" required></div>
                <div class="k-form-buttons"><button class="k-btn k-btn-submit" id="kristinaNameSubmit">✅ Начать</button></div>
            </div>
        </div>
        
        <div class="k-form" id="kristinaLateForm">
            <div class="k-form-header"><h3>🎁 Подарок ждёт!</h3></div>
            <div class="k-form-content">
                <p style="color:#94a3b8;font-size:13px;margin-bottom:16px;line-height:1.4">Укажите контакт, чтобы мы отправили вам подарок:</p>
                <div class="k-form-group"><label>Мессенджер *</label>
                    <select id="lateContactMethod" required>
                        <option value="">Выберите</option>
                        <option value="Telegram">Telegram</option><option value="VK">ВКонтакте</option>
                        <option value="Instagram">Instagram</option><option value="WhatsApp">WhatsApp</option>
                    </select>
                </div>
                <div class="k-form-group"><label>Никнейм *</label><input type="text" id="lateContactNickname" placeholder="@username" required></div>
                <div class="k-form-buttons">
                    <button class="k-btn k-btn-cancel" id="kristinaLateCancel">Позже</button>
                    <button class="k-btn k-btn-submit" id="kristinaLateSubmit">🎁 Получить</button>
                </div>
            </div>
        </div>
    `;

    try {
        document.head.insertAdjacentHTML('beforeend', styles);
        document.body.insertAdjacentHTML('beforeend', widgetHTML);

        const els = {
            btn: document.getElementById('kristinaWidgetBtn'),
            win: document.getElementById('kristinaChatWindow'),
            close: document.getElementById('kristinaChatClose'),
            msgs: document.getElementById('kristinaChatMessages'),
            input: document.getElementById('kristinaChatInput'),
            send: document.getElementById('kristinaSendBtn'),
            fileBtn: document.getElementById('kristinaFileBtn'),
            fileInput: document.getElementById('kristinaFileInput'),
            attached: document.getElementById('kristinaAttachedFiles'),
            dealForm: document.getElementById('kristinaDealForm'),
            formClose: document.getElementById('kristinaFormClose'),
            formCancel: document.getElementById('kristinaFormCancel'),
            formSubmit: document.getElementById('kristinaFormSubmit'),
            nameForm: document.getElementById('kristinaNameForm'),
            nameSubmit: document.getElementById('kristinaNameSubmit'),
            nameInput: document.getElementById('userNameInput'),
            lateForm: document.getElementById('kristinaLateForm'),
            lateCancel: document.getElementById('kristinaLateCancel'),
            lateSubmit: document.getElementById('kristinaLateSubmit'),
            lateMethod: document.getElementById('lateContactMethod'),
            lateNickname: document.getElementById('lateContactNickname')
        };

        if (!els.btn || !els.win) { console.error('❌ Widget init failed'); return; }

        async function api(url, method = 'GET', body = null, formData = false) {
            const opts = { method, headers: { 'X-API-Key': API_KEY } };
            if (!formData) opts.headers['Content-Type'] = 'application/json';
            if (body) opts.body = formData ? body : JSON.stringify(body);
            const res = await fetch(API_URL + url, opts);
            if (!res.ok) throw new Error(`HTTP ${res.status}: ${await res.text()}`);
            return res.status === 204 ? null : res.json();
        }

        async function checkTriggers(text) {
            const t = text.toLowerCase();
            // ✅ ИСПРАВЛЕНО: кнопка "Отмена" → сделка в "Отклонённые"
            if (['нет','подумаю','позже','не сейчас','отмена','не хочу','не интересно'].some(k => t.includes(k))) {
                try {
                    await api('/api/widget/deals', 'POST', {
                        chat_id: chatId, client_name: userName || 'Аноним', sphere: 'Не указано',
                        request: `Клиент: "${text}"`, budget: '0', contact_method: 'Отказ',
                        contact_nickname: '-', status: 'declined', decline_reason: `Клиент: "${text}"`
                    });
                    console.log('✅ Сделка отправлена в "Отклонённые"');
                } catch(e) { console.error('Ошибка создания отклонённой сделки:', e); }
                return;
            }
            if (['подумаю','напишите позднее','позже','не сейчас'].some(k => t.includes(k))) {
                setTimeout(() => {
                    [els.nameForm, els.win, els.dealForm].forEach(el => el?.classList.remove('active'));
                    els.lateForm?.classList.add('active');
                }, 300);
                return;
            }
            if (['да','хочу','интересно','заполню','готова','давайте','пришлите','где заполнить'].some(k => t.includes(k))) {
                setTimeout(() => {
                    els.nameForm?.classList.remove('active');
                    els.dealForm?.classList.add('active');
                    if (userName && document.getElementById('dealClientName')) document.getElementById('dealClientName').value = userName;
                }, 300);
            }
        }

        function parseAI(text) {
            if (!text.includes('[ДА ПОДАТЬ]') || !text.includes('[ОТМЕНА]')) return text;
            return text
                .replace('[ДА ПОДАТЬ]', '<button class="k-btn k-btn-submit" style="margin:4px 4px 4px 0;padding:6px 12px;font-size:12px" onclick="window.kHandleDeal(true)">✅ Да, подать</button>')
                .replace('[ОТМЕНА]', '<button class="k-btn k-btn-cancel" style="margin:4px 0;padding:6px 12px;font-size:12px" onclick="window.kHandleDeal(false)">❌ Отмена</button>');
        }

        window.kHandleDeal = async function(ok) {
            if (!chatId) return;
            try {
                if (ok) {
                    els.nameForm?.classList.remove('active');
                    els.dealForm?.classList.add('active');
                    if (userName && document.getElementById('dealClientName')) document.getElementById('dealClientName').value = userName;
                } else {
                    // ✅ ИСПРАВЛЕНО: кнопка "Отмена" → сделка в "Отклонённые"
                    await api('/api/widget/deals', 'POST', {
                        chat_id: chatId, client_name: userName || 'Аноним', sphere: 'Не указано',
                        request: 'Отказ через AI', budget: '0', contact_method: 'Отказ',
                        contact_nickname: '-', status: 'declined', decline_reason: 'Кнопка [ОТМЕНА]'
                    });
                    await api('/api/widget/send', 'POST', { chat_id: chatId, text: '❌ Заявка отменена.' });
                    renderMessages();
                }
            } catch(e) { alert('❌ Ошибка: ' + e.message); }
        };

        els.btn.onclick = () => {
            isOpen = !isOpen;
            if (isOpen) { els.win.classList.add('active'); els.btn.style.display = 'none'; if (!chatId) initChat(); }
            else { els.win.classList.remove('active'); els.btn.style.display = 'flex'; }
        };
        els.close.onclick = () => { isOpen = false; els.win.classList.remove('active'); els.btn.style.display = 'flex'; };
        els.fileBtn.onclick = () => els.fileInput.click();

        els.fileInput.onchange = e => {
            [...e.target.files].forEach(f => {
                if (!['application/pdf','image/jpeg','image/png','image/gif','image/webp','video/mp4','video/quicktime'].includes(f.type)) { alert('❌ Неверный формат'); return; }
                if (f.size > 20*1024*1024) { alert('❌ Файл > 20МБ'); return; }
                selectedFiles.push(f);
            });
            els.attached.innerHTML = selectedFiles.map((f,i) => `<div class="k-file-tag">📎 ${f.name}<span class="k-remove" onclick="window.kRemoveFile(${i})">×</span></div>`).join('');
            els.fileInput.value = '';
        };
        window.kRemoveFile = i => { selectedFiles.splice(i,1); els.attached.innerHTML = selectedFiles.map((f,j) => `<div class="k-file-tag">📎 ${f.name}<span class="k-remove" onclick="window.kRemoveFile(${j})">×</span></div>`).join(''); };

        async function send() {
            const text = els.input.value.trim();
            if (!text && !selectedFiles.length) return;
            if (!chatId) { alert('❌ Ошибка подключения'); return; }
            try {
                if (selectedFiles.length) {
                    const fd = new FormData(); fd.append('chat_id', chatId); fd.append('text', text);
                    selectedFiles.forEach(f => fd.append('files', f));
                    await api('/api/widget/send_with_files', 'POST', fd, true);
                } else {
                    await api('/api/widget/send', 'POST', { chat_id: chatId, text: text });
                }
                els.input.value = ''; selectedFiles = []; els.attached.innerHTML = '';
                renderMessages();
                await checkTriggers(text);
            } catch(e) { alert('❌ Ошибка: ' + e.message); }
        }
        els.send.onclick = send;
        els.input.onkeypress = e => { if (e.key === 'Enter') send(); };

        async function initChat() {
            try {
                console.log('🔄 Initializing chat...');
                
                if (chatId) {
                    const chats = await api('/api/widget/chats');
                    const existingChat = chats.find(c => c.id == chatId);
                    if (!existingChat) {
                        chatId = null;
                        localStorage.removeItem('kristina_chat_id');
                    }
                }
                
                if (!chatId) {
                    const c = await api('/api/widget/chats', 'POST', {});
                    chatId = c.id;
                    localStorage.setItem('kristina_chat_id', chatId);
                    console.log('✅ Created new chat:', chatId);
                }
                
                renderMessages();
                if (!userName) showNameForm();
            } catch(e) { 
                console.error('❌ Init chat error:', e); 
                alert('❌ Ошибка подключения: ' + e.message);
            }
        }

        function showNameForm() {
            els.nameForm?.classList.add('active');
            els.win.classList.remove('active');
            setTimeout(() => els.nameInput?.focus(), 100);
        }

        if (els.nameSubmit) {
            els.nameSubmit.onclick = async () => {
                const name = els.nameInput?.value.trim();
                if (!name) { alert('❌ Введите имя'); return; }
                try {
                    userName = name; localStorage.setItem('kristina_user_name', userName);
                    if (chatId) await api(`/api/widget/chat/${chatId}/set_client_name`, 'POST', { name });
                    els.nameForm?.classList.remove('active'); els.win?.classList.add('active');
                } catch(e) { alert('❌ ' + e.message); }
            };
        }
        if (els.nameInput) els.nameInput.onkeypress = e => { if (e.key === 'Enter') els.nameSubmit?.click(); };

        async function renderMessages() {
            if (!chatId) return;
            try {
                const res = await api(`/api/widget/messages/${chatId}`);
                messages = res.messages || []; formRequested = res.form_requested || false;
                
                if (!messages.length) {
                    els.msgs.innerHTML = '<div style="text-align:center;padding:40px;opacity:0.6;color:#94a3b8">💬 Начните общение...</div>';
                    return;
                }
                
                els.msgs.innerHTML = messages.map(m => {
                    const isUser = m.sender === 'user';
                    let content = m.text || '';
                    if (m.file_url) {
                        const img = m.file_url.match(/\.(jpg|jpeg|png|gif|webp)$/i);
                        const vid = m.file_url.match(/\.(mp4|mov|avi)$/i);
                        if (img) content += `<div class="k-msg-file"><img src="${m.file_url}" alt=""></div>`;
                        else if (vid) content += `<div class="k-msg-file"><video controls src="${m.file_url}"></video></div>`;
                        else content += `<div class="k-msg-file"><a href="${m.file_url}" target="_blank" class="k-file-link">📄 Файл</a></div>`;
                    }
                    const txt = m.sender === 'admin' ? parseAI(content) : content;
                    return `<div class="k-msg ${isUser ? 'k-msg-user' : 'k-msg-admin'}">${txt}</div>`;
                }).join('');
                els.msgs.scrollTop = els.msgs.scrollHeight;
                
                // ✅ ИСПРАВЛЕНО: Автопоявление анкеты
                if (formRequested && !els.dealForm.classList.contains('active') && !els.win.classList.contains('active') && (!els.nameForm || !els.nameForm.classList.contains('active'))) {
                    els.nameForm?.classList.remove('active'); els.dealForm?.classList.add('active');
                }
            } catch(e) {}
        }
        setInterval(renderMessages, 3000);

        function showDealForm() {
            els.win.classList.remove('active'); els.dealForm?.classList.add('active');
            if (userName && document.getElementById('dealClientName')) document.getElementById('dealClientName').value = userName;
        }
        if (els.formClose) els.formClose.onclick = () => { els.dealForm?.classList.remove('active'); els.win?.classList.add('active'); };
        if (els.formCancel) els.formCancel.onclick = () => { els.dealForm?.classList.remove('active'); els.win?.classList.add('active'); };
        if (els.formSubmit) {
            els.formSubmit.onclick = async () => {
                const d = {
                    chat_id: chatId,
                    client_name: document.getElementById('dealClientName')?.value.trim(),
                    sphere: document.getElementById('dealSphere')?.value.trim(),
                    request: document.getElementById('dealRequest')?.value.trim(),
                    budget: document.getElementById('dealBudget')?.value.trim(),
                    contact_method: document.getElementById('dealContactMethod')?.value,
                    contact_nickname: document.getElementById('dealContactNickname')?.value.trim()
                };
                if (!d.client_name || !d.sphere || !d.request || !d.budget || !d.contact_method || !d.contact_nickname) { alert('❌ Заполните все поля'); return; }
                if (['max','макс','макс к','макс.к','max.k'].includes(d.contact_method.toLowerCase())) { alert('❌ Укажите разрешённый мессенджер'); return; }
                try {
                    await api('/api/widget/deals', 'POST', d);
                    alert('✅ Заявка отправлена!');
                    els.dealForm?.classList.remove('active');
                    if (els.btn) els.btn.style.display = 'flex';
                    isOpen = false;
                } catch(e) { alert('❌ ' + e.message); }
            };
        }

        if (els.lateCancel) els.lateCancel.onclick = () => { els.lateForm?.classList.remove('active'); els.win?.classList.add('active'); };
        if (els.lateSubmit) {
            els.lateSubmit.onclick = async () => {
                const method = els.lateMethod?.value, nick = els.lateNickname?.value.trim();
                if (!method || !nick) { alert('❌ Укажите мессенджер и никнейм'); return; }
                try {
                    await api('/api/widget/capture_late_contact', 'POST', { chat_id: chatId, contact_method: method, contact_nickname: nick });
                    alert('🎁 Отлично! Мы свяжемся с вами.');
                    els.lateForm?.classList.remove('active');
                    if (els.btn) els.btn.style.display = 'flex';
                    isOpen = false;
                } catch(e) { alert('❌ ' + e.message); }
            };
        }

        initChat();
        console.log('✅ Widget v3.2 loaded');
        
    } catch(e) { console.error('❌ Widget error:', e); }
})();
