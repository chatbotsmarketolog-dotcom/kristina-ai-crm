// КРИСТИНА.AI CRM Widget
(function() {
    // Конфигурация
    const API_URL = window.KRISTINA_API_URL || window.location.origin + '/api';
    const API_KEY = window.KRISTINA_API_KEY;
    
    if (!API_KEY) {
        console.error('KRISTINA_API_KEY не указан!');
        return;
    }

    // Состояние
    let chatId = null;
    let messages = [];
    let formRequested = false;
    let userName = localStorage.getItem('kristina_user_name') || '';
    let pollInterval = null;

    // Стили
    const styles = `
        <style>
            /* Плавающая кнопка */
            .kristina-widget-btn {
                position: fixed;
                bottom: 30px;
                right: 30px;
                background: linear-gradient(135deg, #3b82f6 0%, #2563eb 100%);
                color: white;
                padding: 16px 24px;
                border-radius: 50px;
                box-shadow: 0 10px 30px rgba(59, 130, 246, 0.4);
                cursor: pointer;
                font-family: system-ui, -apple-system, sans-serif;
                font-weight: 600;
                font-size: 15px;
                z-index: 999999;
                transition: all 0.3s ease;
                border: none;
                display: flex;
                align-items: center;
                gap: 10px;
            }
            
            .kristina-widget-btn:hover {
                transform: translateY(-3px);
                box-shadow: 0 15px 40px rgba(59, 130, 246, 0.5);
            }
            
            .kristina-widget-btn::before {
                content: '💬';
                font-size: 20px;
            }
            
            /* Окно чата */
            .kristina-chat-window {
                position: fixed;
                bottom: 100px;
                right: 30px;
                width: 450px;
                height: 650px;
                background: #0b132b;
                border-radius: 20px;
                box-shadow: 0 20px 60px rgba(0, 0, 0, 0.4);
                z-index: 999999;
                display: none;
                flex-direction: column;
                overflow: hidden;
                border: 1px solid rgba(59, 130, 246, 0.3);
            }
            
            .kristina-chat-window.active {
                display: flex;
            }
            
            /* Шапка */
            .kristina-chat-header {
                background: linear-gradient(135deg, rgba(59, 130, 246, 0.9) 0%, rgba(37, 99, 235, 0.9) 100%);
                padding: 20px;
                color: white;
                display: flex;
                justify-content: space-between;
                align-items: center;
            }
            
            .kristina-chat-header h3 {
                margin: 0;
                font-size: 18px;
                font-weight: 600;
            }
            
            .kristina-chat-close {
                background: rgba(255, 255, 255, 0.2);
                border: none;
                color: white;
                width: 32px;
                height: 32px;
                border-radius: 50%;
                cursor: pointer;
                font-size: 18px;
                display: flex;
                align-items: center;
                justify-content: center;
            }
            
            /* Сообщения */
            .kristina-chat-messages {
                flex: 1;
                overflow-y: auto;
                padding: 20px;
                display: flex;
                flex-direction: column;
                gap: 12px;
                background: #0b132b;
            }
            
            .kristina-message {
                max-width: 80%;
                padding: 12px 16px;
                border-radius: 16px;
                font-size: 14px;
                line-height: 1.5;
                animation: fadeIn 0.3s ease;
            }
            
            @keyframes fadeIn {
                from { opacity: 0; transform: translateY(10px); }
                to { opacity: 1; transform: translateY(0); }
            }
            
            .kristina-message-user {
                background: rgba(16, 185, 129, 0.2);
                color: #10b981;
                align-self: flex-end;
                border-bottom-right-radius: 4px;
            }
            
            .kristina-message-admin {
                background: rgba(59, 130, 246, 0.15);
                color: #93c5fd;
                align-self: flex-start;
                border-bottom-left-radius: 4px;
            }
            
            /* Поле ввода */
            .kristina-chat-input {
                padding: 20px;
                background: rgba(15, 23, 42, 0.9);
                border-top: 1px solid rgba(59, 130, 246, 0.2);
                display: flex;
                gap: 10px;
            }
            
            .kristina-chat-input input {
                flex: 1;
                padding: 14px 18px;
                border-radius: 25px;
                border: 1px solid rgba(59, 130, 246, 0.3);
                background: rgba(0, 0, 0, 0.3);
                color: #e2e8f0;
                font-family: system-ui, -apple-system, sans-serif;
                font-size: 14px;
                outline: none;
            }
            
            .kristina-chat-input input::placeholder {
                color: rgba(226, 232, 240, 0.5);
            }
            
            .kristina-chat-input button {
                background: linear-gradient(135deg, #3b82f6 0%, #2563eb 100%);
                color: white;
                border: none;
                padding: 14px 24px;
                border-radius: 25px;
                cursor: pointer;
                font-weight: 600;
                transition: all 0.3s ease;
            }
            
            .kristina-chat-input button:hover {
                transform: scale(1.05);
            }
            
            /* Форма заявки */
            .kristina-deal-form {
                position: fixed;
                bottom: 100px;
                right: 30px;
                width: 450px;
                max-height: 650px;
                background: #0b132b;
                border-radius: 20px;
                box-shadow: 0 20px 60px rgba(0, 0, 0, 0.4);
                z-index: 999999;
                display: none;
                flex-direction: column;
                overflow: hidden;
                border: 1px solid rgba(59, 130, 246, 0.3);
            }
            
            .kristina-deal-form.active {
                display: flex;
            }
            
            .kristina-form-header {
                background: linear-gradient(135deg, rgba(16, 185, 129, 0.9) 0%, rgba(5, 150, 105, 0.9) 100%);
                padding: 20px;
                color: white;
                display: flex;
                justify-content: space-between;
                align-items: center;
            }
            
            .kristina-form-header h3 {
                margin: 0;
                font-size: 18px;
            }
            
            .kristina-form-content {
                padding: 20px;
                overflow-y: auto;
                max-height: 500px;
            }
            
            .kristina-form-group {
                margin-bottom: 16px;
            }
            
            .kristina-form-group label {
                display: block;
                color: #94a3b8;
                margin-bottom: 6px;
                font-size: 13px;
            }
            
            .kristina-form-group input,
            .kristina-form-group textarea,
            .kristina-form-group select {
                width: 100%;
                padding: 12px;
                border-radius: 8px;
                border: 1px solid rgba(59, 130, 246, 0.3);
                background: rgba(0, 0, 0, 0.3);
                color: #e2e8f0;
                font-family: system-ui, -apple-system, sans-serif;
                font-size: 14px;
                box-sizing: border-box;
            }
            
            .kristina-form-group textarea {
                resize: vertical;
                min-height: 80px;
            }
            
            .kristina-form-buttons {
                display: flex;
                gap: 10px;
                margin-top: 20px;
            }
            
            .kristina-btn {
                flex: 1;
                padding: 14px;
                border: none;
                border-radius: 8px;
                cursor: pointer;
                font-weight: 600;
                font-size: 14px;
            }
            
            .kristina-btn-cancel {
                background: rgba(239, 68, 68, 0.2);
                color: #ef4444;
            }
            
            .kristina-btn-submit {
                background: linear-gradient(135deg, #10b981 0%, #059669 100%);
                color: white;
            }
            
            /* Скроллбар */
            .kristina-chat-messages::-webkit-scrollbar,
            .kristina-form-content::-webkit-scrollbar {
                width: 6px;
            }
            
            .kristina-chat-messages::-webkit-scrollbar-thumb,
            .kristina-form-content::-webkit-scrollbar-thumb {
                background: rgba(59, 130, 246, 0.3);
                border-radius: 3px;
            }
        </style>
    `;

    // HTML виджета
    const widgetHTML = `
        <button class="kristina-widget-btn" id="kristinaWidgetBtn">
            Онлайн менеджер
        </button>
        
        <div class="kristina-chat-window" id="kristinaChatWindow">
            <div class="kristina-chat-header">
                <h3>💬 КРИСТИНА.AI CRM</h3>
                <button class="kristina-chat-close" id="kristinaChatClose">×</button>
            </div>
            <div class="kristina-chat-messages" id="kristinaChatMessages">
                <div class="empty-state" style="text-align: center; padding: 40px; opacity: 0.6; color: #94a3b8;">
                    💬 Начните общение...
                </div>
            </div>
            <div class="kristina-chat-input">
                <input type="text" id="kristinaChatInput" placeholder="Введите сообщение...">
                <button id="kristinaSendBtn">Отправить</button>
            </div>
        </div>
        
        <div class="kristina-deal-form" id="kristinaDealForm">
            <div class="kristina-form-header">
                <h3>📋 Заявка на личную встречу</h3>
                <button class="kristina-chat-close" id="kristinaFormClose">×</button>
            </div>
            <div class="kristina-form-content">
                <div class="kristina-form-group">
                    <label>1. Имя *</label>
                    <input type="text" id="dealClientName" required>
                </div>
                <div class="kristina-form-group">
                    <label>2. Сфера деятельности *</label>
                    <input type="text" id="dealSphere" placeholder="Например: маркетинг, дизайн" required>
                </div>
                <div class="kristina-form-group">
                    <label>3. Какой запрос хочется разобрать? *</label>
                    <textarea id="dealRequest" placeholder="Опишите, что хотите обсудить..." required></textarea>
                </div>
                <div class="kristina-form-group">
                    <label>4. Бюджет *</label>
                    <input type="text" id="dealBudget" placeholder="Например: 15 000 ₽, 50 000 ₽" required>
                </div>
                <div class="kristina-form-group">
                    <label>5. Способ связи *</label>
                    <select id="dealContactMethod" required>
                        <option value="">Выберите мессенджер</option>
                        <option value="Telegram">Telegram</option>
                        <option value="VK">ВКонтакте</option>
                        <option value="Одноклассники">Одноклассники</option>
                        <option value="Instagram">Instagram</option>
                        <option value="TenChat">TenChat</option>
                    </select>
                </div>
                <div class="kristina-form-group">
                    <label>6. Никнейм для связи *</label>
                    <input type="text" id="dealContactNickname" placeholder="@username или ссылка" required>
                </div>
                <div class="kristina-form-buttons">
                    <button class="kristina-btn kristina-btn-cancel" id="kristinaFormCancel">Отмена</button>
                    <button class="kristina-btn kristina-btn-submit" id="kristinaFormSubmit">✅ Подтвердить заявку</button>
                </div>
            </div>
        </div>
    `;

    // Добавляем стили и HTML
    document.head.insertAdjacentHTML('beforeend', styles);
    document.body.insertAdjacentHTML('beforeend', widgetHTML);

    // Элементы
    const widgetBtn = document.getElementById('kristinaWidgetBtn');
    const chatWindow = document.getElementById('kristinaChatWindow');
    const chatClose = document.getElementById('kristinaChatClose');
    const chatMessages = document.getElementById('kristinaChatMessages');
    const chatInput = document.getElementById('kristinaChatInput');
    const sendBtn = document.getElementById('kristinaSendBtn');
    const dealForm = document.getElementById('kristinaDealForm');
    const formClose = document.getElementById('kristinaFormClose');
    const formCancel = document.getElementById('kristinaFormCancel');
    const formSubmit = document.getElementById('kristinaFormSubmit');

    // API функции
    async function fetchAPI(url, method = 'GET', body = null) {
        const options = {
            method,
            headers: {
                'Content-Type': 'application/json',
                'X-API-Key': API_KEY
            }
        };
        
        if (body) {
            options.body = JSON.stringify(body);
        }
        
        const response = await fetch(API_URL + url, options);
        return response.json();
    }

    // Открыть/закрыть чат
    widgetBtn.addEventListener('click', () => {
        chatWindow.classList.add('active');
        widgetBtn.style.display = 'none';
        if (!chatId) {
            initChat();
        }
    });

    chatClose.addEventListener('click', () => {
        chatWindow.classList.remove('active');
        widgetBtn.style.display = 'flex';
    });

    // Отправка сообщения
    async function sendMessage() {
        const text = chatInput.value.trim();
        if (!text || !chatId) return;
        
        try {
            await fetchAPI('/api/send', 'POST', {
                chat_id: chatId,
                text: text
            });
            
            chatInput.value = '';
            loadMessages();
        } catch (e) {
            console.error('Ошибка отправки:', e);
        }
    }

    sendBtn.addEventListener('click', sendMessage);
    chatInput.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') sendMessage();
    });

    // Инициализация чата
    async function initChat() {
        try {
            // Проверяем есть ли активный чат
            const chats = await fetchAPI('/api/chats');
            const activeChat = chats.find(c => c.status === 'active' || c.status === 'waiting');
            
            if (activeChat) {
                chatId = activeChat.id;
            } else {
                // Создаём новый чат
                const newChat = await fetchAPI('/api/chats', 'POST', {});
                chatId = newChat.id;
            }
            
            loadMessages();
            
            // Спрашиваем имя если нет
            if (!userName) {
                const name = prompt('👋 Привет! Как к вам обращаться?', '');
                if (name && name.trim()) {
                    userName = name.trim();
                    localStorage.setItem('kristina_user_name', userName);
                    await fetchAPI(`/api/chat/${chatId}/set_client_name`, 'POST', { name: userName });
                }
            }
        } catch (e) {
            console.error('Ошибка инициализации:', e);
        }
    }

    // Загрузка сообщений
    async function loadMessages() {
        if (!chatId) return;
        
        try {
            const response = await fetchAPI(`/api/messages/${chatId}`);
            messages = response.messages || [];
            formRequested = response.form_requested || false;
            
            renderMessages();
            
            // Показываем форму если запрошена
            if (formRequested && !dealForm.classList.contains('active') && !chatWindow.classList.contains('active')) {
                showDealForm();
            }
        } catch (e) {
            console.error('Ошибка загрузки:', e);
        }
    }

    // Отображение сообщений
    function renderMessages() {
        if (messages.length === 0) {
            chatMessages.innerHTML = `
                <div class="empty-state" style="text-align: center; padding: 40px; opacity: 0.6; color: #94a3b8;">
                    💬 Начните общение...
                </div>
            `;
            return;
        }
        
        chatMessages.innerHTML = messages.map(msg => {
            const isUser = msg.sender === 'user';
            return `
                <div class="kristina-message ${isUser ? 'kristina-message-user' : 'kristina-message-admin'}">
                    ${msg.text}
                </div>
            `;
        }).join('');
        
        chatMessages.scrollTop = chatMessages.scrollHeight;
    }

    // Форма заявки
    function showDealForm() {
        chatWindow.classList.remove('active');
        dealForm.classList.add('active');
        
        // Автозаполнение имени
        if (userName) {
            document.getElementById('dealClientName').value = userName;
        }
    }

    formClose.addEventListener('click', () => {
        dealForm.classList.remove('active');
        chatWindow.classList.add('active');
    });

    formCancel.addEventListener('click', () => {
        dealForm.classList.remove('active');
        chatWindow.classList.add('active');
    });

    formSubmit.addEventListener('click', async () => {
        const data = {
            chat_id: chatId,
            client_name: document.getElementById('dealClientName').value.trim(),
            sphere: document.getElementById('dealSphere').value.trim(),
            request: document.getElementById('dealRequest').value.trim(),
            budget: document.getElementById('dealBudget').value.trim(),
            contact_method: document.getElementById('dealContactMethod').value,
            contact_nickname: document.getElementById('dealContactNickname').value.trim()
        };
        
        // Валидация
        if (!data.client_name || !data.sphere || !data.request || !data.budget || !data.contact_method || !data.contact_nickname) {
            alert('❌ Заполните все обязательные поля');
            return;
        }
        
        // Валидация мессенджера
        const blocked = ['max', 'макс', 'макс к', 'макс.к', 'max.k'];
        if (blocked.includes(data.contact_method.toLowerCase())) {
            alert('❌ Укажите Telegram, VK, Одноклассники, Instagram или TenChat');
            return;
        }
        
        try {
            await fetchAPI('/api/deals', 'POST', data);
            alert('✅ Заявка отправлена! Мы свяжемся с вами soon.');
            dealForm.classList.remove('active');
            widgetBtn.style.display = 'flex';
        } catch (e) {
            alert('❌ Ошибка отправки: ' + e.message);
        }
    });

    // Автообновление сообщений
    setInterval(loadMessages, 3000);

})();
