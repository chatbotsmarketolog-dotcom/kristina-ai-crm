// КРИСТИНА.AI CRM Widget
(function() {
    'use strict';
    
    // Конфигурация
    const API_URL = window.KRISTINA_API_URL || window.location.origin;
    const API_KEY = window.KRISTINA_API_KEY;
    
    if (!API_KEY) {
        console.error('❌ KRISTINA_API_KEY не указан!');
        return;
    }

    console.log('🚀 Widget initializing...', { API_URL, API_KEY: API_KEY.substring(0, 10) + '...' });

    // Состояние
    let chatId = null;
    let messages = [];
    let formRequested = false;
    let userName = localStorage.getItem('kristina_user_name') || '';
    let pollInterval = null;
    let selectedFiles = [];
    let isOpen = false;

    // Стили
    const styles = `
        <style>
            /* Плавающая кнопка */
            .kristina-widget-btn {
                position: fixed !important;
                bottom: 30px !important;
                right: 30px !important;
                background: linear-gradient(135deg, #3b82f6 0%, #2563eb 100%) !important;
                color: white !important;
                padding: 16px 24px !important;
                border-radius: 50px !important;
                box-shadow: 0 10px 30px rgba(59, 130, 246, 0.4) !important;
                cursor: pointer !important;
                font-family: system-ui, -apple-system, sans-serif !important;
                font-weight: 600 !important;
                font-size: 15px !important;
                z-index: 999999 !important;
                transition: all 0.3s ease !important;
                border: none !important;
                display: flex !important;
                align-items: center !important;
                gap: 10px !important;
            }
            
            .kristina-widget-btn:hover {
                transform: translateY(-3px) !important;
                box-shadow: 0 15px 40px rgba(59, 130, 246, 0.5) !important;
            }
            
            .kristina-widget-btn::before {
                content: '💬' !important;
                font-size: 20px !important;
            }
            
            /* Окно чата - АДАПТИВНОЕ */
            .kristina-chat-window {
                position: fixed !important;
                bottom: 100px !important;
                right: 30px !important;
                width: 450px !important;
                max-width: calc(100vw - 60px) !important;
                height: 650px !important;
                max-height: calc(100vh - 150px) !important;
                background: #0b132b !important;
                border-radius: 20px !important;
                box-shadow: 0 20px 60px rgba(0, 0, 0, 0.4) !important;
                z-index: 999999 !important;
                display: none !important;
                flex-direction: column !important;
                overflow: hidden !important;
                border: 1px solid rgba(59, 130, 246, 0.3) !important;
            }
            
            .kristina-chat-window.active {
                display: flex !important;
            }
            
            /* Шапка */
            .kristina-chat-header {
                background: linear-gradient(135deg, rgba(59, 130, 246, 0.9) 0%, rgba(37, 99, 235, 0.9) 100%) !important;
                padding: 20px !important;
                color: white !important;
                display: flex !important;
                justify-content: space-between !important;
                align-items: center !important;
                flex-shrink: 0 !important;
            }
            
            .kristina-chat-header h3 {
                margin: 0 !important;
                font-size: 18px !important;
                font-weight: 600 !important;
            }
            
            .kristina-chat-close {
                background: rgba(255, 255, 255, 0.2) !important;
                border: none !important;
                color: white !important;
                width: 32px !important;
                height: 32px !important;
                border-radius: 50% !important;
                cursor: pointer !important;
                font-size: 18px !important;
                display: flex !important;
                align-items: center !important;
                justify-content: center !important;
            }
            
            /* Сообщения */
            .kristina-chat-messages {
                flex: 1 !important;
                overflow-y: auto !important;
                padding: 20px !important;
                display: flex !important;
                flex-direction: column !important;
                gap: 12px !important;
                background: #0b132b !important;
            }
            
            .kristina-message {
                max-width: 80% !important;
                padding: 12px 16px !important;
                border-radius: 16px !important;
                font-size: 14px !important;
                line-height: 1.5 !important;
                animation: fadeIn 0.3s ease !important;
                word-wrap: break-word !important;
            }
            
            @keyframes fadeIn {
                from { opacity: 0; transform: translateY(10px); }
                to { opacity: 1; transform: translateY(0); }
            }
            
            .kristina-message-user {
                background: rgba(16, 185, 129, 0.2) !important;
                color: #10b981 !important;
                align-self: flex-end !important;
                border-bottom-right-radius: 4px !important;
            }
            
            .kristina-message-admin {
                background: rgba(59, 130, 246, 0.15) !important;
                color: #93c5fd !important;
                align-self: flex-start !important;
                border-bottom-left-radius: 4px !important;
            }
            
            .kristina-message-file {
                background: rgba(59, 130, 246, 0.1) !important;
                border: 1px solid rgba(59, 130, 246, 0.3) !important;
                padding: 10px !important;
                border-radius: 12px !important;
                margin-top: 8px !important;
            }
            
            .kristina-file-link {
                color: #60a5fa !important;
                text-decoration: none !important;
                display: inline-flex !important;
                align-items: center !important;
                gap: 8px !important;
            }
            
            .kristina-file-link:hover {
                text-decoration: underline !important;
            }
            
            /* Поле ввода с кнопками */
            .kristina-chat-input-wrapper {
                padding: 16px 20px !important;
                background: rgba(15, 23, 42, 0.9) !important;
                border-top: 1px solid rgba(59, 130, 246, 0.2) !important;
                flex-shrink: 0 !important;
            }
            
            /* Прикреплённые файлы */
            .kristina-attached-files {
                display: flex !important;
                gap: 8px !important;
                margin-bottom: 12px !important;
                flex-wrap: wrap !important;
            }
            
            .kristina-file-tag {
                background: rgba(59, 130, 246, 0.2) !important;
                color: #93c5fd !important;
                padding: 6px 12px !important;
                border-radius: 20px !important;
                font-size: 12px !important;
                display: flex !important;
                align-items: center !important;
                gap: 8px !important;
            }
            
            .kristina-file-tag .remove-file {
                cursor: pointer !important;
                opacity: 0.7 !important;
                font-weight: bold !important;
            }
            
            .kristina-file-tag .remove-file:hover {
                opacity: 1 !important;
            }
            
            .kristina-chat-input-row {
                display: flex !important;
                gap: 10px !important;
                align-items: center !important;
            }
            
            .kristina-chat-input {
                flex: 1 !important;
                padding: 14px 18px !important;
                border-radius: 25px !important;
                border: 1px solid rgba(59, 130, 246, 0.3) !important;
                background: rgba(0, 0, 0, 0.3) !important;
                color: #e2e8f0 !important;
                font-family: system-ui, -apple-system, sans-serif !important;
                font-size: 14px !important;
                outline: none !important;
                min-width: 0 !important;
            }
            
            .kristina-chat-input::placeholder {
                color: rgba(226, 232, 240, 0.5) !important;
            }
            
            .kristina-file-btn {
                background: rgba(59, 130, 246, 0.2) !important;
                color: #60a5fa !important;
                border: 1px solid rgba(59, 130, 246, 0.3) !important;
                width: 44px !important;
                height: 44px !important;
                border-radius: 50% !important;
                cursor: pointer !important;
                display: flex !important;
                align-items: center !important;
                justify-content: center !important;
                font-size: 20px !important;
                transition: all 0.3s ease !important;
                flex-shrink: 0 !important;
            }
            
            .kristina-file-btn:hover {
                background: rgba(59, 130, 246, 0.3) !important;
                transform: scale(1.1) !important;
            }
            
            .kristina-send-btn {
                background: linear-gradient(135deg, #3b82f6 0%, #2563eb 100%) !important;
                color: white !important;
                border: none !important;
                padding: 14px 24px !important;
                border-radius: 25px !important;
                cursor: pointer !important;
                font-weight: 600 !important;
                transition: all 0.3s ease !important;
                flex-shrink: 0 !important;
            }
            
            .kristina-send-btn:hover {
                transform: scale(1.05) !important;
            }
            
            /* Скрытый input для файлов */
            #kristinaFileInput {
                display: none !important;
            }
            
            /* Форма заявки */
            .kristina-deal-form {
                position: fixed !important;
                bottom: 100px !important;
                right: 30px !important;
                width: 450px !important;
                max-width: calc(100vw - 60px) !important;
                max-height: calc(100vh - 150px) !important;
                background: #0b132b !important;
                border-radius: 20px !important;
                box-shadow: 0 20px 60px rgba(0, 0, 0, 0.4) !important;
                z-index: 999999 !important;
                display: none !important;
                flex-direction: column !important;
                overflow: hidden !important;
                border: 1px solid rgba(59, 130, 246, 0.3) !important;
            }
            
            .kristina-deal-form.active {
                display: flex !important;
            }
            
            .kristina-form-header {
                background: linear-gradient(135deg, rgba(16, 185, 129, 0.9) 0%, rgba(5, 150, 105, 0.9) 100%) !important;
                padding: 20px !important;
                color: white !important;
                display: flex !important;
                justify-content: space-between !important;
                align-items: center !important;
                flex-shrink: 0 !important;
            }
            
            .kristina-form-header h3 {
                margin: 0 !important;
                font-size: 18px !important;
            }
            
            .kristina-form-content {
                padding: 20px !important;
                overflow-y: auto !important;
                flex: 1 !important;
            }
            
            .kristina-form-group {
                margin-bottom: 16px !important;
            }
            
            .kristina-form-group label {
                display: block !important;
                color: #94a3b8 !important;
                margin-bottom: 6px !important;
                font-size: 13px !important;
            }
            
            .kristina-form-group input,
            .kristina-form-group textarea,
            .kristina-form-group select {
                width: 100% !important;
                padding: 12px !important;
                border-radius: 8px !important;
                border: 1px solid rgba(59, 130, 246, 0.3) !important;
                background: rgba(0, 0, 0, 0.3) !important;
                color: #e2e8f0 !important;
                font-family: system-ui, -apple-system, sans-serif !important;
                font-size: 14px !important;
                box-sizing: border-box !important;
            }
            
            .kristina-form-group textarea {
                resize: vertical !important;
                min-height: 80px !important;
            }
            
            .kristina-form-buttons {
                display: flex !important;
                gap: 10px !important;
                margin-top: 20px !important;
            }
            
            .kristina-btn {
                flex: 1 !important;
                padding: 14px !important;
                border: none !important;
                border-radius: 8px !important;
                cursor: pointer !important;
                font-weight: 600 !important;
                font-size: 14px !important;
            }
            
            .kristina-btn-cancel {
                background: rgba(239, 68, 68, 0.2) !important;
                color: #ef4444 !important;
            }
            
            .kristina-btn-submit {
                background: linear-gradient(135deg, #10b981 0%, #059669 100%) !important;
                color: white !important;
            }
            
            /* Скроллбар */
            .kristina-chat-messages::-webkit-scrollbar,
            .kristina-form-content::-webkit-scrollbar {
                width: 6px !important;
            }
            
            .kristina-chat-messages::-webkit-scrollbar-thumb,
            .kristina-form-content::-webkit-scrollbar-thumb {
                background: rgba(59, 130, 246, 0.3) !important;
                border-radius: 3px !important;
            }
            
            /* МОБИЛЬНАЯ АДАПТАЦИЯ */
            @media (max-width: 768px) {
                .kristina-widget-btn {
                    bottom: 20px !important;
                    right: 20px !important;
                    padding: 14px 20px !important;
                    font-size: 14px !important;
                }
                
                .kristina-chat-window,
                .kristina-deal-form {
                    bottom: 90px !important;
                    right: 15px !important;
                    left: 15px !important;
                    width: calc(100% - 30px) !important;
                    max-width: none !important;
                    height: calc(100vh - 120px) !important;
                    max-height: none !important;
                    border-radius: 16px !important;
                }
                
                .kristina-chat-messages {
                    padding: 15px !important;
                }
                
                .kristina-message {
                    max-width: 90% !important;
                    font-size: 13px !important;
                    padding: 10px 14px !important;
                }
                
                .kristina-chat-input-wrapper {
                    padding: 12px 15px !important;
                }
                
                .kristina-chat-input-row {
                    flex-wrap: wrap !important;
                }
                
                .kristina-file-btn {
                    width: 40px !important;
                    height: 40px !important;
                    order: 1 !important;
                }
                
                .kristina-chat-input {
                    flex: 1 1 calc(100% - 100px) !important;
                    order: 2 !important;
                    min-width: 0 !important;
                }
                
                .kristina-send-btn {
                    order: 3 !important;
                    padding: 12px 20px !important;
                }
                
                .kristina-form-content {
                    padding: 15px !important;
                }
            }
            
            @media (max-width: 480px) {
                .kristina-widget-btn {
                    padding: 12px 18px !important;
                    font-size: 13px !important;
                }
                
                .kristina-chat-header h3 {
                    font-size: 16px !important;
                }
                
                .kristina-message {
                    font-size: 12px !important;
                    padding: 8px 12px !important;
                }
                
                .kristina-chat-input {
                    font-size: 13px !important;
                    padding: 12px 16px !important;
                }
                
                .kristina-send-btn {
                    font-size: 13px !important;
                    padding: 12px 18px !important;
                }
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
            <div class="kristina-chat-input-wrapper">
                <div class="kristina-attached-files" id="kristinaAttachedFiles"></div>
                <div class="kristina-chat-input-row">
                    <input type="file" id="kristinaFileInput" multiple accept=".pdf,.jpg,.jpeg,.png,.gif,.webp">
                    <button class="kristina-file-btn" id="kristinaFileBtn" title="Прикрепить файл">📎</button>
                    <input type="text" class="kristina-chat-input" id="kristinaChatInput" placeholder="Введите сообщение...">
                    <button class="kristina-send-btn" id="kristinaSendBtn">Отправить</button>
                </div>
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

    try {
        // Добавляем стили и HTML
        document.head.insertAdjacentHTML('beforeend', styles);
        document.body.insertAdjacentHTML('beforeend', widgetHTML);
        
        console.log('✅ Widget HTML inserted');

        // Элементы
        const widgetBtn = document.getElementById('kristinaWidgetBtn');
        const chatWindow = document.getElementById('kristinaChatWindow');
        const chatClose = document.getElementById('kristinaChatClose');
        const chatMessages = document.getElementById('kristinaChatMessages');
        const chatInput = document.getElementById('kristinaChatInput');
        const sendBtn = document.getElementById('kristinaSendBtn');
        const fileBtn = document.getElementById('kristinaFileBtn');
        const fileInput = document.getElementById('kristinaFileInput');
        const attachedFiles = document.getElementById('kristinaAttachedFiles');
        const dealForm = document.getElementById('kristinaDealForm');
        const formClose = document.getElementById('kristinaFormClose');
        const formCancel = document.getElementById('kristinaFormCancel');
        const formSubmit = document.getElementById('kristinaFormSubmit');

        // Проверка элементов
        if (!widgetBtn || !chatWindow) {
            console.error('❌ Widget elements not found!');
            return;
        }

        // API функции
        async function fetchAPI(url, method = 'GET', body = null, useFormData = false) {
            const options = {
                method,
                headers: {}
            };
            
            if (!useFormData) {
                options.headers['Content-Type'] = 'application/json';
            }
            options.headers['X-API-Key'] = API_KEY;
            
            if (body) {
                options.body = body;
            }
            
            const fullUrl = API_URL + url;
            console.log('📡 API Request:', method, fullUrl);
            
            const response = await fetch(fullUrl, options);
            
            if (!response.ok) {
                const errorText = await response.text();
                console.error('❌ API Error:', response.status, errorText);
                throw new Error(`HTTP ${response.status}: ${errorText}`);
            }
            
            if (response.status === 204) return null;
            
            return response.json();
        }

        // Открыть/закрыть чат
        widgetBtn.addEventListener('click', () => {
            console.log('🔔 Widget button clicked');
            isOpen = !isOpen;
            
            if (isOpen) {
                chatWindow.classList.add('active');
                widgetBtn.style.display = 'none';
                if (!chatId) {
                    initChat();
                }
            } else {
                chatWindow.classList.remove('active');
                widgetBtn.style.display = 'flex';
            }
        });

        chatClose.addEventListener('click', () => {
            isOpen = false;
            chatWindow.classList.remove('active');
            widgetBtn.style.display = 'flex';
        });

        // Выбор файлов
        fileBtn.addEventListener('click', () => {
            fileInput.click();
        });

        fileInput.addEventListener('change', (e) => {
            const files = Array.from(e.target.files);
            
            // Валидация файлов
            const validTypes = ['application/pdf', 'image/jpeg', 'image/jpg', 'image/png', 'image/gif', 'image/webp'];
            const maxSize = 20 * 1024 * 1024; // 20MB
            
            files.forEach(file => {
                if (!validTypes.includes(file.type)) {
                    alert(`❌ Файл "${file.name}" имеет неподдерживаемый формат. Разрешены: PDF, JPG, PNG, GIF, WebP`);
                    return;
                }
                
                if (file.size > maxSize) {
                    alert(`❌ Файл "${file.name}" слишком большой. Максимум 20MB`);
                    return;
                }
                
                selectedFiles.push(file);
            });
            
            renderAttachedFiles();
            fileInput.value = '';
        });

        // Отображение прикреплённых файлов
        function renderAttachedFiles() {
            attachedFiles.innerHTML = selectedFiles.map((file, index) => `
                <div class="kristina-file-tag">
                    📎 ${file.name}
                    <span class="remove-file" onclick="removeFile(${index})">×</span>
                </div>
            `).join('');
        }

        // Удаление файла
        window.removeFile = function(index) {
            selectedFiles.splice(index, 1);
            renderAttachedFiles();
        };

        // Отправка сообщения с файлами
        async function sendMessage() {
            const text = chatInput.value.trim();
            
            if (!text && selectedFiles.length === 0) return;
            if (!chatId) {
                alert('❌ Чат не инициализирован. Попробуйте позже.');
                return;
            }
            
            try {
                let response;
                
                if (selectedFiles.length > 0) {
                    // Отправка с файлами
                    const formData = new FormData();
                    formData.append('chat_id', chatId);
                    formData.append('text', text);
                    
                    selectedFiles.forEach(file => {
                        formData.append('files', file);
                    });
                    
                    response = await fetchAPI('/api/send_with_files', 'POST', formData, true);
                } else {
                    // Отправка только текста
                    response = await fetchAPI('/api/send', 'POST', {
                        chat_id: chatId,
                        text: text
                    });
                }
                
                // Очистка
                chatInput.value = '';
                selectedFiles = [];
                renderAttachedFiles();
                
                // Обновление сообщений
                loadMessages();
            } catch (e) {
                console.error('Ошибка отправки:', e);
                alert('❌ Ошибка отправки: ' + e.message);
            }
        }

        sendBtn.addEventListener('click', sendMessage);
        chatInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') sendMessage();
        });

        // Инициализация чата
        async function initChat() {
            try {
                console.log('🔄 Initializing chat...');
                
                // Проверяем есть ли активный чат
                const chats = await fetchAPI('/api/chats');
                console.log('📋 Chats:', chats);
                
                const activeChat = chats.find(c => c.status === 'active' || c.status === 'waiting');
                
                if (activeChat) {
                    chatId = activeChat.id;
                    console.log('✅ Using existing chat:', chatId);
                } else {
                    // Создаём новый чат
                    const newChat = await fetchAPI('/api/chats', 'POST', {});
                    chatId = newChat.id;
                    console.log('✅ Created new chat:', chatId);
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
                console.error('❌ Ошибка инициализации:', e);
                alert('❌ Ошибка подключения к чату: ' + e.message);
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
                console.error('❌ Ошибка загрузки:', e);
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
                let fileHtml = '';
                
                if (msg.files && msg.files.length > 0) {
                    fileHtml = msg.files.map(file => {
                        const isImage = file.url && file.url.match(/\.(jpg|jpeg|png|gif|webp)$/i);
                        if (isImage) {
                            return `<div class="kristina-message-file">
                                <a href="${file.url}" target="_blank" class="kristina-file-link">
                                    🖼️ ${file.name || 'Изображение'}
                                </a>
                            </div>`;
                        } else {
                            return `<div class="kristina-message-file">
                                <a href="${file.url}" target="_blank" class="kristina-file-link">
                                    📄 ${file.name || 'Файл'}
                                </a>
                            </div>`;
                        }
                    }).join('');
                }
                
                return `
                    <div class="kristina-message ${isUser ? 'kristina-message-user' : 'kristina-message-admin'}">
                        ${msg.text || ''}
                        ${fileHtml}
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
                isOpen = false;
            } catch (e) {
                alert('❌ Ошибка отправки: ' + e.message);
            }
        });

        // Автообновление сообщений
        setInterval(loadMessages, 3000);
        
        console.log('✅ Widget initialized successfully');
        
    } catch (error) {
        console.error('❌ Widget initialization error:', error);
    }

})();
