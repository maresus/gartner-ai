(function() {
  'use strict';

  const CONFIG = {
    apiUrl: 'https://gartner.up.railway.app/chat',
    brandColor: '#0D0D0D',
    brandColorHover: '#2a2a2a',
    accentColor: '#C4A44B',
    title: 'Gartner Bohinj',
    subtitle: 'Turistična kmetija Gartner, Bohinj',
    placeholder: 'Vprašajte o sirih, apartmajih...',
    welcomeMessage: 'Pozdravljeni! Sem AI pomočnik Turistične kmetije Gartner — odgovarjam samodejno in nisem živa oseba. Pomagam z informacijami o sirih, apartmajih in planini v Lazu. Kako vam lahko pomagam?',
    mobileBreakpoint: 768,
    maxStoredMessages: 50
  };

  const styles = `
    #gn-widget-container * {
      box-sizing: border-box;
      font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
    }

    #gn-launcher {
      position: fixed;
      bottom: 20px;
      right: 20px;
      z-index: 9999999;
      display: flex;
      flex-direction: column;
      align-items: flex-end;
      gap: 10px;
      pointer-events: none;
    }
    #gn-launcher > * { pointer-events: all; }

    #gn-widget-bubble {
      width: 60px;
      height: 60px;
      border-radius: 50%;
      background: ${CONFIG.brandColor};
      cursor: pointer;
      box-shadow: 0 4px 16px rgba(0,0,0,0.35);
      display: flex;
      align-items: center;
      justify-content: center;
      transition: transform 0.2s, box-shadow 0.2s;
      border: 2px solid ${CONFIG.accentColor};
      padding: 0;
      touch-action: manipulation;
      -webkit-tap-highlight-color: transparent;
      flex-shrink: 0;
      position: relative;
    }
    #gn-widget-bubble:hover {
      transform: scale(1.08);
      box-shadow: 0 6px 24px rgba(0,0,0,0.4);
    }
    #gn-widget-bubble svg {
      width: 28px;
      height: 28px;
      fill: ${CONFIG.accentColor};
    }
    #gn-widget-bubble.gn-has-notification::after {
      content: '';
      position: absolute;
      top: 2px; right: 2px;
      width: 14px; height: 14px;
      background: #ef4444;
      border-radius: 50%;
      border: 2px solid white;
    }

    #gn-widget-panel {
      position: fixed;
      bottom: 90px; right: 20px;
      width: 420px;
      height: 600px;
      max-height: calc(100vh - 120px);
      background: #fff;
      border-radius: 16px;
      box-shadow: 0 8px 40px rgba(0,0,0,0.25);
      display: flex;
      flex-direction: column;
      overflow: hidden;
      z-index: 999998;
      opacity: 0;
      visibility: hidden;
      transform: translateY(8px);
      transition: opacity 0.15s ease, transform 0.15s ease, visibility 0.15s;
    }
    #gn-widget-panel.gn-open {
      opacity: 1; visibility: visible; transform: translateY(0);
    }

    @media (max-width: ${CONFIG.mobileBreakpoint}px) {
      #gn-widget-panel {
        position: fixed !important;
        inset: 0 !important;
        width: 100% !important;
        height: 100dvh !important;
        height: 100vh !important;
        max-height: none !important;
        border-radius: 0 !important;
        margin: 0 !important;
      }
      #gn-widget-header {
        padding-top: max(16px, env(safe-area-inset-top)) !important;
      }
      #gn-widget-input-area {
        padding-bottom: max(12px, env(safe-area-inset-bottom)) !important;
      }
      #gn-widget-input { font-size: 16px !important; }
    }

    #gn-widget-header {
      background: ${CONFIG.brandColor};
      color: #ffffff;
      padding: 14px 16px;
      display: flex;
      align-items: center;
      gap: 12px;
      flex-shrink: 0;
    }
    #gn-widget-header-logo {
      width: 44px; height: 44px;
      display: flex; align-items: center; justify-content: center;
      flex-shrink: 0;
    }
    #gn-widget-header-logo svg { width: 44px; height: 44px; }
    #gn-widget-header-text { flex: 1; }
    #gn-widget-header-text h3 {
      margin: 0; font-size: 15px; font-weight: 700;
      color: #ffffff; letter-spacing: 0.5px;
    }
    #gn-widget-header-text h3 span { color: ${CONFIG.accentColor}; }
    #gn-widget-header-text p {
      margin: 2px 0 0; font-size: 11px; color: rgba(255,255,255,0.6);
    }
    .gn-header-btn {
      background: none; border: none;
      color: rgba(255,255,255,0.7);
      cursor: pointer; padding: 7px;
      border-radius: 8px; transition: background 0.15s;
    }
    .gn-header-btn:hover { background: rgba(255,255,255,0.12); }
    .gn-header-btn svg { width: 18px; height: 18px; fill: rgba(255,255,255,0.8); }

    #gn-widget-messages {
      flex: 1; overflow-y: auto;
      padding: 16px;
      background: #F5F0E8;
    }
    .gn-message { margin-bottom: 12px; display: flex; flex-direction: column; }
    .gn-message.gn-bot { align-items: flex-start; }
    .gn-message.gn-user { align-items: flex-end; }
    .gn-message-bubble {
      max-width: 85%;
      padding: 11px 15px;
      border-radius: 16px;
      font-size: 14px; line-height: 1.5;
      word-wrap: break-word;
    }
    .gn-bot .gn-message-bubble {
      background: white;
      color: #1a1a1a;
      border-bottom-left-radius: 4px;
      box-shadow: 0 1px 4px rgba(0,0,0,0.08);
    }
    .gn-user .gn-message-bubble {
      background: ${CONFIG.brandColor};
      color: white;
      border-bottom-right-radius: 4px;
    }

    .gn-typing {
      display: flex; gap: 4px; padding: 12px 16px;
    }
    .gn-typing span {
      width: 8px; height: 8px;
      background: #999; border-radius: 50%;
      animation: gn-bounce 1.2s infinite;
    }
    .gn-typing span:nth-child(2) { animation-delay: 0.2s; }
    .gn-typing span:nth-child(3) { animation-delay: 0.4s; }
    @keyframes gn-bounce {
      0%, 60%, 100% { transform: translateY(0); }
      30% { transform: translateY(-6px); }
    }

    #gn-widget-input-area {
      padding: 12px 16px;
      background: white;
      border-top: 1px solid #e8e0d0;
      display: flex; gap: 10px; flex-shrink: 0;
    }
    #gn-widget-input {
      flex: 1;
      border: 1px solid #ddd; border-radius: 24px;
      padding: 11px 18px; font-size: 14px;
      outline: none; transition: border-color 0.15s;
    }
    #gn-widget-input:focus { border-color: ${CONFIG.accentColor}; }
    #gn-widget-send {
      width: 44px; height: 44px;
      border-radius: 50%;
      background: ${CONFIG.accentColor};
      border: none; cursor: pointer;
      display: flex; align-items: center; justify-content: center;
      transition: background 0.15s; flex-shrink: 0;
    }
    #gn-widget-send:hover { background: #b0923e; }
    #gn-widget-send:disabled { background: #ccc; cursor: not-allowed; }
    #gn-widget-send svg { width: 20px; height: 20px; fill: white; }

    #gn-scroll-down {
      position: absolute;
      bottom: 80px; left: 50%;
      transform: translateX(-50%);
      width: 36px; height: 36px;
      background: ${CONFIG.brandColor};
      border-radius: 50%;
      display: none; align-items: center; justify-content: center;
      cursor: pointer;
      box-shadow: 0 2px 8px rgba(0,0,0,0.3);
      z-index: 10;
    }
    #gn-scroll-down.gn-visible { display: flex; }
    #gn-scroll-down svg { width: 20px; height: 20px; fill: white; }

    #gn-widget-disclaimer {
      font-size: 11px; color: #999; line-height: 1.4;
      padding: 5px 14px 3px; background: white; text-align: center;
    }
    #gn-widget-disclaimer a { color: ${CONFIG.accentColor}; text-decoration: none; }
    #gn-widget-powered {
      text-align: center; font-size: 11px; color: #ccc;
      padding: 2px 0 6px; background: white;
    }
    #gn-widget-powered a { color: #bbb; text-decoration: none; }
    #gn-widget-powered a:hover { color: ${CONFIG.accentColor}; }
  `;

  const icons = {
    chat: '<svg viewBox="0 0 24 24"><path d="M20 2H4c-1.1 0-2 .9-2 2v18l4-4h14c1.1 0 2-.9 2-2V4c0-1.1-.9-2-2-2zm0 14H5.17L4 17.17V4h16v12z"/></svg>',
    close: '<svg viewBox="0 0 24 24"><path d="M19 6.41L17.59 5 12 10.59 6.41 5 5 6.41 10.59 12 5 17.59 6.41 19 12 13.41 17.59 19 19 17.59 13.41 12z"/></svg>',
    send: '<svg viewBox="0 0 24 24"><path d="M2.01 21L23 12 2.01 3 2 10l15 2-15 2z"/></svg>',
    refresh: '<svg viewBox="0 0 24 24"><path d="M17.65 6.35A7.958 7.958 0 0012 4c-4.42 0-7.99 3.58-7.99 8s3.57 8 7.99 8c3.73 0 6.84-2.55 7.73-6h-2.08A5.99 5.99 0 0112 18c-3.31 0-6-2.69-6-6s2.69-6 6-6c1.66 0 3.14.69 4.22 1.78L13 11h7V4l-2.35 2.35z"/></svg>',
    arrowDown: '<svg viewBox="0 0 24 24"><path d="M7.41 8.59L12 13.17l4.59-4.58L18 10l-6 6-6-6 1.41-1.41z"/></svg>',
    cheese: '<svg viewBox="0 0 64 48" fill="none"><path d="M2 46 L32 4 L62 46 Z" fill="#C4A44B" stroke="#8B6B1A" stroke-width="2"/><circle cx="20" cy="35" r="5" fill="#8B6B1A" opacity="0.4"/><circle cx="38" cy="28" r="4" fill="#8B6B1A" opacity="0.4"/><circle cx="30" cy="40" r="3" fill="#8B6B1A" opacity="0.4"/><circle cx="48" cy="38" r="4" fill="#8B6B1A" opacity="0.4"/></svg>'
  };

  // Logo SVG za header (minimalistična verzija Gartner logotipa)
  const logoSvg = `<svg viewBox="0 0 44 44" fill="none">
    <circle cx="22" cy="22" r="22" fill="#0D0D0D"/>
    <path d="M8 34 L22 12 L36 34 Z" fill="#C4A44B" stroke="none"/>
    <circle cx="16" cy="28" r="2.5" fill="#0D0D0D" opacity="0.5"/>
    <circle cx="26" cy="25" r="2" fill="#0D0D0D" opacity="0.5"/>
    <circle cx="22" cy="32" r="1.8" fill="#0D0D0D" opacity="0.5"/>
    <circle cx="30" cy="31" r="2" fill="#0D0D0D" opacity="0.5"/>
  </svg>`;

  let sessionId = localStorage.getItem('gn_widget_session') || generateSessionId();
  localStorage.setItem('gn_widget_session', sessionId);

  let storedMessages = [];
  try {
    const stored = localStorage.getItem('gn_widget_messages');
    if (stored) storedMessages = JSON.parse(stored);
  } catch(e) { storedMessages = []; }

  function generateSessionId() {
    return 'gn_' + Date.now() + '_' + Math.random().toString(36).substr(2, 9);
  }

  function saveMessages() {
    localStorage.setItem('gn_widget_messages', JSON.stringify(storedMessages.slice(-CONFIG.maxStoredMessages)));
  }

  function clearConversation() {
    storedMessages = [];
    localStorage.removeItem('gn_widget_messages');
    sessionId = generateSessionId();
    localStorage.setItem('gn_widget_session', sessionId);
    const messages = document.getElementById('gn-widget-messages');
    messages.innerHTML = '';
    addMessage(CONFIG.welcomeMessage, 'bot', false);
  }

  function createWidget() {
    const styleEl = document.createElement('style');
    styleEl.textContent = styles;
    document.head.appendChild(styleEl);

    const launcher = document.createElement('div');
    launcher.id = 'gn-launcher';

    // Greeting kartice
    const cardStyle = [
      'display:block', 'background:#0D0D0D', 'color:#C4A44B',
      'font-size:14px', 'font-family:-apple-system,BlinkMacSystemFont,sans-serif',
      'font-weight:600', 'padding:10px 16px', 'border-radius:18px 18px 4px 18px',
      'box-shadow:0 2px 12px rgba(0,0,0,0.25)', 'cursor:pointer',
      'border:1px solid rgba(196,164,75,0.3)', 'max-width:230px',
      'text-align:right', 'touch-action:manipulation',
      '-webkit-tap-highlight-color:transparent', 'margin-bottom:8px', 'line-height:1.4',
    ].join(';');

    const closeStyle = [
      'display:block', 'background:#0D0D0D', 'color:#C4A44B',
      'border:1px solid rgba(196,164,75,0.4)', 'border-radius:50%',
      'width:24px', 'height:24px', 'font-size:13px', 'cursor:pointer',
      'touch-action:manipulation', '-webkit-tap-highlight-color:transparent',
      'margin-bottom:6px', 'margin-left:auto', 'line-height:22px',
      'text-align:center', 'padding:0',
    ].join(';');

    const greetingCards = document.createElement('div');
    greetingCards.id = 'gn-greeting-cards';
    greetingCards.setAttribute('style', [
      'position:fixed', 'bottom:90px', 'right:0', 'z-index:2147483647',
      'display:none', 'flex-direction:column', 'align-items:flex-end', 'padding-right:0',
    ].join(';'));

    const xBtn = document.createElement('button');
    xBtn.setAttribute('style', closeStyle + ';margin-right:6px');
    xBtn.textContent = '✕';
    xBtn.onclick = function(e) { e.stopPropagation(); e.preventDefault(); hideCards(); };
    greetingCards.appendChild(xBtn);

    ['Pozdravljeni! 🧀', 'Turistična kmetija Gartner.', 'Kako vam lahko pomagam?'].forEach(function(text) {
      const btn = document.createElement('button');
      btn.setAttribute('style', cardStyle);
      btn.textContent = text;
      btn.onclick = function(e) { e.stopPropagation(); e.preventDefault(); setTimeout(openPanel, 0); };
      greetingCards.appendChild(btn);
    });

    const bubble = document.createElement('button');
    bubble.id = 'gn-widget-bubble';
    bubble.innerHTML = '<img src="/static/images.jpeg" style="width:54px;height:54px;border-radius:50%;object-fit:cover;pointer-events:none;display:block;" alt="Gartner">';
    bubble.onclick = function(e) {
      e.stopPropagation(); e.preventDefault();
      setTimeout(togglePanel, 0);
    };

    const panel = document.createElement('div');
    panel.id = 'gn-widget-panel';
    panel.innerHTML = `
      <div id="gn-widget-header">
        <div id="gn-widget-header-logo">${logoSvg}</div>
        <div id="gn-widget-header-text">
          <h3><span>GARTNER</span> Bohinj</h3>
          <p>${CONFIG.subtitle}</p>
        </div>
        <button class="gn-header-btn" id="gn-widget-refresh" title="Nov pogovor">${icons.refresh}</button>
        <button class="gn-header-btn" id="gn-widget-close" title="Zapri">${icons.close}</button>
      </div>
      <div id="gn-widget-messages"></div>
      <div id="gn-scroll-down">${icons.arrowDown}</div>
      <div id="gn-widget-input-area">
        <input type="text" id="gn-widget-input" placeholder="${CONFIG.placeholder}">
        <button id="gn-widget-send">${icons.send}</button>
      </div>
      <div id="gn-widget-disclaimer">🤖 AI pomočnik — EU AI Act čl. 50. Odgovori so informativni. Za naročila in rezervacije: <a href="tel:+38641205182">+386 41 205 182</a></div>
      <div id="gn-widget-powered">built by: <a href="https://spoznaj-ai.si" target="_blank">spoznaj-ai.si</a></div>
    `;

    launcher.appendChild(bubble);
    document.body.appendChild(launcher);
    document.body.appendChild(greetingCards);
    document.body.appendChild(panel);

    panel.addEventListener('click', function(e) { e.stopPropagation(); });
    greetingCards.addEventListener('click', function(e) { e.stopPropagation(); });
    launcher.addEventListener('click', function(e) { e.stopPropagation(); });

    document.getElementById('gn-widget-close').onclick = closePanel;
    document.getElementById('gn-widget-refresh').onclick = clearConversation;
    document.getElementById('gn-widget-send').onclick = sendMessage;
    document.getElementById('gn-widget-input').onkeypress = function(e) {
      if (e.key === 'Enter') sendMessage();
    };
    document.getElementById('gn-widget-input').addEventListener('focus', function() {
      const msgs = document.getElementById('gn-widget-messages');
      if (msgs) setTimeout(function() { msgs.scrollTo({ top: msgs.scrollHeight, behavior: 'smooth' }); }, 350);
    });

    const messagesEl = document.getElementById('gn-widget-messages');
    const scrollArrow = document.getElementById('gn-scroll-down');
    scrollArrow.onclick = function() { messagesEl.scrollTop = messagesEl.scrollHeight; };
    messagesEl.onscroll = function() {
      const nearBottom = messagesEl.scrollHeight - messagesEl.scrollTop - messagesEl.clientHeight < 50;
      if (nearBottom) scrollArrow.classList.remove('gn-visible');
    };

    if (storedMessages.length > 0) {
      storedMessages.forEach(function(msg) { addMessageToUI(msg.text, msg.sender, false); });
    } else {
      addMessageToUI(CONFIG.welcomeMessage, 'bot', false);
    }

    setTimeout(function() { if (!panelOpen) showCards(); }, 800);
  }

  let panelOpen = false;

  function showCards() {
    const c = document.getElementById('gn-greeting-cards');
    if (c) c.style.display = 'flex';
  }
  function hideCards() {
    const c = document.getElementById('gn-greeting-cards');
    if (c) c.style.display = 'none';
  }
  function togglePanel() { if (panelOpen) closePanel(); else openPanel(); }

  function openPanel() {
    if (panelOpen) return;
    panelOpen = true;
    const panel = document.getElementById('gn-widget-panel');
    panel.classList.add('gn-open');
    panel.style.opacity = '1';
    panel.style.visibility = 'visible';
    panel.style.transform = 'translateY(0)';
    if (window.innerWidth <= CONFIG.mobileBreakpoint) {
      panel.style.position = 'fixed';
      panel.style.inset = '0';
      panel.style.width = '100%';
      panel.style.height = '100%';
      panel.style.maxHeight = 'none';
      panel.style.borderRadius = '0';
      document.body.style.overflow = 'hidden';
    }
    hideCards();
    document.getElementById('gn-widget-bubble').classList.remove('gn-has-notification');
    document.getElementById('gn-widget-input').focus();
  }

  function closePanel() {
    if (!panelOpen) return;
    panelOpen = false;
    const panel = document.getElementById('gn-widget-panel');
    panel.classList.remove('gn-open');
    panel.style.opacity = '0';
    panel.style.visibility = 'hidden';
    panel.style.transform = 'translateY(8px)';
    document.body.style.overflow = '';
    showCards();
  }

  function addMessageToUI(text, sender, autoScroll) {
    if (autoScroll === undefined) autoScroll = true;
    const messages = document.getElementById('gn-widget-messages');
    const scrollArrow = document.getElementById('gn-scroll-down');
    const msg = document.createElement('div');
    msg.className = 'gn-message gn-' + sender;
    msg.innerHTML = '<div class="gn-message-bubble">' + (sender === 'bot' ? renderMarkdown(text) : escapeHtml(text)) + '</div>';
    messages.appendChild(msg);
    if (!autoScroll) return;
    if (sender === 'user') {
      msg.scrollIntoView({ behavior: 'smooth', block: 'start' });
    } else {
      const allUserMsgs = messages.querySelectorAll('.gn-user');
      const lastUser = allUserMsgs[allUserMsgs.length - 1];
      if (lastUser) lastUser.scrollIntoView({ behavior: 'smooth', block: 'start' });
      else msg.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }
    if (scrollArrow) scrollArrow.classList.remove('gn-visible');
  }

  function addMessage(text, sender, save) {
    if (save === undefined) save = true;
    addMessageToUI(text, sender);
    if (save) {
      storedMessages.push({ text: text, sender: sender, time: Date.now() });
      saveMessages();
    }
  }

  function showTyping() {
    const messages = document.getElementById('gn-widget-messages');
    const typing = document.createElement('div');
    typing.id = 'gn-typing-indicator';
    typing.className = 'gn-message gn-bot';
    typing.innerHTML = '<div class="gn-message-bubble gn-typing"><span></span><span></span><span></span></div>';
    messages.appendChild(typing);
    typing.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
  }
  function hideTyping() {
    const t = document.getElementById('gn-typing-indicator');
    if (t) t.remove();
  }

  function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML.replace(/\n/g, '<br>');
  }

  function renderMarkdown(text) {
    let escaped = (function(t) { const d = document.createElement('div'); d.textContent = t; return d.innerHTML; })(text);
    escaped = escaped.replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>');
    escaped = escaped.replace(/\[([^\]]+)\]\((https?:\/\/[^)]+)\)/g, '<a href="$2" target="_blank" rel="noopener" style="color:' + CONFIG.accentColor + ';text-decoration:underline;">$1</a>');
    escaped = escaped.replace(/(?<!=["'])(https?:\/\/[^\s<>"')\]]+)/g, '<a href="$1" target="_blank" rel="noopener" style="color:' + CONFIG.accentColor + ';text-decoration:underline;">$1</a>');
    escaped = escaped.replace(/((?:^|\n)- [^\n]+)+/g, function(block) {
      const items = block.trim().split(/\n/).map(function(line) { return '<li>' + line.replace(/^- /, '') + '</li>'; }).join('');
      return '<ul style="margin:6px 0 6px 16px;padding:0;">' + items + '</ul>';
    });
    escaped = escaped.replace(/\n\n+/g, '</p><p style="margin:6px 0;">');
    escaped = escaped.replace(/\n/g, '<br>');
    return '<p style="margin:0;">' + escaped + '</p>';
  }

  async function sendMessage() {
    const input = document.getElementById('gn-widget-input');
    const sendBtn = document.getElementById('gn-widget-send');
    const text = input.value.trim();
    if (!text) return;

    addMessage(text, 'user');
    input.value = '';
    sendBtn.disabled = true;
    showTyping();

    try {
      const response = await fetch(CONFIG.apiUrl, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: text, session_id: sessionId })
      });
      hideTyping();
      if (!response.ok) throw new Error('API error');
      const data = await response.json();
      const reply = data.reply || data.response || data.message || 'Oprostite, prišlo je do napake.';
      addMessage(reply, 'bot');
    } catch(err) {
      hideTyping();
      addMessage('Oprostite, trenutno ni mogoče vzpostaviti povezave. Pokličite nas: +386 41 205 182', 'bot');
    }

    sendBtn.disabled = false;
    input.focus();
  }

  function initWidget() {
    if (document.getElementById('gn-launcher')) return;
    createWidget();
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initWidget);
  } else {
    requestAnimationFrame(initWidget);
  }
})();

