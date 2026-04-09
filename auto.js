// auto.js — Виджет чата для сайтов клиентов
// Версия для PythonAnywhere (Polling)

(function() {
  // === НАСТРОЙКИ ===
  const CRM_URL = "https://Kristina1.pythonanywhere.com";
  const SITE_KEY = window.christinaSiteKey || ''; // Ключ сайта (передаётся при вставке)
  
  // === СОЗДАЁМ ВИДЖЕТ ===
  function createWidget() {
    // Проверяем, не загружен ли уже виджет
    if (document.getElementById('kristina-widget')) return;
    
    // Контейнер виджета
    const widget = document.createElement('div');
    widget.id = 'kristina-widget';
    widget.style.cssText = `
      position:fixed;bottom:20px;right:20px;z-index:99999;
      font-family:system-ui,-apple-system,sans-serif;
    `;
    
    // Кнопка открытия
    const toggleBtn = document.createElement('button');
    toggleBtn.innerHTML = '💬';
    toggleBtn.style.cssText = `
      width:60px;height:60px;border-radius:50%;
      background:linear-gradient(135deg,#3b82f6,#06b6d4);
      color:#fff;border:none;cursor:pointer;
      font-size:24px;box-shadow:0 4px 20px rgba(0,0,0,0.3);
      transition:transform 0.2s;
    `;
    toggleBtn.onmouseenter = () => toggleBtn.style.transform = 'scale(1.1)';
    toggleBtn.onmouseleave = () => toggleBtn.style.transform = 'scale(1)';
    
    // Окно чата (скрыто по умолчанию)
    const chatWindow = document.createElement('div');
    chatWindow.style.cssText = `
      display:none;position:absolute;bottom:70px;right:0;
      width:320px;max-height:450px;background:#fff;
      border-radius:16px;box-shadow:0 10px 40px rgba(0,0,0,0.2);
      overflow:hidden;flex-direction:column;
    `;
    
    // Заголовок
    const header = document.createElement('div');
    header.style.cssText = `
      padding:12px 16px;background:linear-gradient(135deg,#3b82f6,#06b6d4);
      color:#fff;font-weight:600;display:flex;justify-content:space-between;align-items:center;
    `;
    header.innerHTML = `<span>Поддержка</span><button id="kristina-close" style="background:none;border:none;color:#fff;font-size:20px;cursor:pointer">&times;</button>`;
    
    // Область сообщений
    const messages = document.createElement('div');
    messages.id = 'kristina-messages';
    messages.style.cssText = `
      flex:1;padding:12px;overflow-y:auto;background:#f8fafc;
      display:flex;flex-direction:column;gap:8px;
    `;
    
    // Поле ввода
    const inputWrap = document.createElement('div');
    inputWrap.style.cssText = `padding:12px;border-top:1px solid #e2e8f0;display:flex;gap:8px`;
    
    const input = document.createElement('input');
    input.type = 'text';
    input.placeholder = 'Введите сообщение...';
    input.style.cssText = `
      flex:1;padding:10px 14px;border:1px solid #cbd5e1;
      border-radius:10px;outline:none;font-size:14px;
    `;
    
    const sendBtn = document.createElement('button');
    sendBtn.textContent = '➤';
    sendBtn.style.cssText = `
      padding:10px 16px;background:#3b82f6;color:#fff;
      border:none;border-radius:10px;cursor:pointer;font-weight:600;
    `;
    
    // Индикатор "печатает..."
    const typing = document.createElement('div');
    typing.id = 'kristina-typing';
    typing.style.cssText = `
      padding:8px 16px;font-size:12px;color:#64748b;
      display:none;background:#f1f5f9;
    `;
    typing.textContent = 'Оператор печатает...';
    
    // Собираем всё вместе
    inputWrap.appendChild(input);
    inputWrap.appendChild(sendBtn);
    chatWindow.appendChild(header);
    chatWindow.appendChild(messages);
    chatWindow.appendChild(typing);
    chatWindow.appendChild(inputWrap);
    widget.appendChild(chatWindow);
    widget.appendChild(toggleBtn);
    document.body.appendChild(widget);
    
    // === ЛОГИКА ===
    let chatId = null;
    let visitorId = localStorage.getItem('kristina_visitor_id') || 'v_' + Math.random().toString(36).slice(2, 10);
    localStorage.setItem('kristina_visitor_id', visitorId);
    
    // Открыть/закрыть чат
    toggleBtn.onclick = () => {
      const isHidden = chatWindow.style.display === 'none' || !chatWindow.style.display;
      chatWindow.style.display = isHidden ? 'flex' : 'none';
      if (isHidden && !chatId) startChat();
    };
    
    document.getElementById('kristina-close').onclick = () => {
      chatWindow.style.display = 'none';
    };
    
    // Отправка сообщения
    function sendMessage() {
      const text = input.value.trim();
      if (!text || !chatId) return;
      
      addMessage(text, 'visitor');
      input.value = '';
      
      fetch(`${CRM_URL}/api/send_message`, {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({chat_id: chatId, text: text})
      }).catch(e => console.error('Send error:', e));
    }
    
    sendBtn.onclick = sendMessage;
    input.onkeypress = (e) => { if (e.key === 'Enter') sendMessage(); };
    
    // Добавление сообщения в чат
    function addMessage(text, sender) {
      const msg = document.createElement('div');
      msg.style.cssText = `
        padding:10px 14px;border-radius:12px;max-width:85%;
        ${sender === 'visitor' ? 'background:#dbeafe;color:#1e3a8a;align-self:flex-end' : 'background:#f1f5f9;color:#334155;align-self:flex-start'}
      `;
      msg.textContent = text;
      messages.appendChild(msg);
      messages.scrollTop = messages.scrollHeight;
    }
    
    // Старт нового чата
    async function startChat() {
      try {
        const res = await fetch(`${CRM_URL}/api/chat/${SITE_KEY}`, {
          method: 'POST',
          headers: {'Content-Type': 'application/json'},
          body: JSON.stringify({visitor_id: visitorId})
        });
        const data = await res.json();
        if (data.chat_id) {
          chatId = data.chat_id;
          addMessage('Здравствуйте! Чем можем помочь?', 'operator');
          pollMessages();
        }
      } catch (e) {
        console.error('Chat start error:', e);
        addMessage('⚠️ Ошибка подключения. Попробуйте позже.', 'operator');
      }
    }
    
    // Опрос новых сообщений (POLLING)
    function pollMessages() {
      if (!chatId) return;
      
      setInterval(async () => {
        try {
          const res = await fetch(`${CRM_URL}/api/messages/${chatId}`);
          const msgs = await res.json();
          
          // Показываем только новые (простая логика)
          const existing = messages.querySelectorAll('.msg').length;
          if (msgs.length > existing) {
            msgs.slice(existing).forEach(m => {
              if (m.sender !== 'visitor') addMessage(m.text, 'operator');
            });
          }
        } catch (e) {
          console.error('Poll error:', e);
        }
      }, 2500); // Опрос каждые 2.5 секунды
    }
    
    // Авто-старт если есть site_key
    if (SITE_KEY) {
      // Можно добавить логику авто-открытия при определённых условиях
      // Например, через 10 секунд на сайте:
      setTimeout(() => {
        if (!chatId) {
          // Показываем уведомление
          toggleBtn.style.animation = 'pulse 2s infinite';
        }
      }, 10000);
    }
  }
  
  // Загружаем виджет когда страница готова
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', createWidget);
  } else {
    createWidget();
  }
  
})();