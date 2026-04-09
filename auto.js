// auto.js — Универсальный авто-интегратор для КРИСТИНА.AI CRM
(function(){
  if(window.blueflowLoaded) return;
  window.blueflowLoaded = true;

  // ✅ ТВОЯ РЕАЛЬНАЯ ССЫЛКА
  const CRM_URL = "https://kristina-ai-crm.onrender.com";
  const currentDomain = window.location.hostname;
  const pageUrl = window.location.href;

  async function checkAndInject() {
    try {
      const res = await fetch(`${CRM_URL}/api/widget-status?domain=${encodeURIComponent(currentDomain)}`);
      const data = await res.json();
      
      if (data.active && data.embed_url) {
        injectIframe(data.embed_url);
      }
    } catch (e) {
      console.warn('КРИСТИНА.AI CRM: проверка статуса не удалась', e);
    }
  }

  function injectIframe(src) {
    if (document.getElementById('kristina-crm-widget')) return;
    const container = document.createElement('div');
    container.id = 'kristina-crm-widget';
    container.style.cssText = 'position:fixed;bottom:20px;right:20px;z-index:99999;';
    document.body.appendChild(container);
    
    const shadow = container.attachShadow({mode: 'open'});
    shadow.innerHTML = `<iframe src="${src}" style="width:380px;height:600px;border:none;border-radius:16px;box-shadow:0 10px 40px rgba(0,0,0,0.3);"></iframe>`;
  }

  // Авто-регистрация при первом запуске
  fetch(`${CRM_URL}/api/auto-register`, {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({domain: currentDomain, url: pageUrl})
  }).then(r => r.json()).then(data => {
    if(data.status === 'active') checkAndInject();
  }).catch(() => {});

  // Периодическая проверка (если сайт ещё на модерации)
  setInterval(checkAndInject, 30000);
})();