const $ = id => document.getElementById(id);

const DEFAULT_BACKEND = 'https://sneaker-pricing-production.up.railway.app';
const DEFAULT_TOKEN   = '400c67e13ef5cbc3b80b08c0cd2bdd24cc8ef75de53a547a';

async function loadSettings() {
  return new Promise(resolve => {
    chrome.storage.local.get(['backendUrl', 'adminToken', 'lastSynced'], stored => {
      resolve({
        backendUrl:  stored.backendUrl  || DEFAULT_BACKEND,
        adminToken:  stored.adminToken  || DEFAULT_TOKEN,
        lastSynced:  stored.lastSynced  || null,
      });
    });
  });
}

async function checkLogin() {
  const cookies = await chrome.cookies.getAll({ domain: 'shopee.tw' });
  const uid  = cookies.find(c => c.name === 'SPC_U');
  const dot  = $('status-dot');
  const text = $('status-text');
  const btn  = $('sync-btn');

  if (uid && uid.value && uid.value !== '0') {
    dot.className    = 'dot green';
    text.textContent = `已登入蝦皮（UID: ${uid.value}）`;
    btn.disabled     = false;
  } else {
    dot.className    = 'dot red';
    text.textContent = '尚未登入蝦皮，請先到蝦皮登入';
    btn.disabled     = true;
  }
}

async function checkBackendCookie() {
  const { backendUrl, adminToken } = await loadSettings();
  const el = $('backend-status');
  el.textContent = '檢查中…';
  el.className   = 'backend-status checking';

  try {
    const res  = await fetch(`${backendUrl.replace(/\/$/, '')}/admin/cookie-status`, {
      headers: { 'X-Admin-Token': adminToken },
    });
    const data = await res.json();
    if (res.ok) {
      const preview = data.preview || '';
      const len     = data.length  || 0;
      if (len > 200) {
        el.textContent = `✅ 後端 cookie 有效（${len} 字元）`;
        el.className   = 'backend-status ok';
      } else {
        el.textContent = `⚠️ 後端 cookie 過短（${len} 字元），可能已失效`;
        el.className   = 'backend-status warn';
      }
    } else {
      el.textContent = `❌ 查詢失敗：${data.detail || res.status}`;
      el.className   = 'backend-status err';
    }
  } catch (e) {
    el.textContent = `❌ 無法連線後端`;
    el.className   = 'backend-status err';
  }
}

async function syncCookie() {
  const { backendUrl, adminToken } = await loadSettings();

  if (!backendUrl) {
    showResult('請先在設定中填入後端 URL', 'err');
    $('settings-panel').open = true;
    return;
  }

  const btn = $('sync-btn');
  btn.disabled    = true;
  btn.textContent = '同步中…';

  try {
    const cookies   = await chrome.cookies.getAll({ domain: 'shopee.tw' });
    const cookieStr = cookies.map(c => `${c.name}=${c.value}`).join('; ');

    const res = await fetch(`${backendUrl.replace(/\/$/, '')}/admin/update-shopee-cookie`, {
      method: 'POST',
      headers: {
        'Content-Type':  'application/json',
        'X-Admin-Token': adminToken,
      },
      body: JSON.stringify({ cookie: cookieStr }),
    });

    const data = await res.json();
    if (res.ok) {
      const now = new Date().toLocaleString('zh-TW', { hour12: false });
      await chrome.storage.local.set({ lastSynced: now, autoSynced: false });
      updateLastSynced(now, false);

      btn.textContent = '✅ 已同步';
      btn.style.background = 'var(--green)';
      showResult(`同步成功！Cookie 長度：${data.length} 字元`, 'ok');
      checkBackendCookie();
      setTimeout(() => {
        btn.textContent      = '同步蝦皮 Cookie';
        btn.style.background = '';
        btn.disabled         = false;
      }, 3000);
    } else {
      showResult('❌ ' + (data.detail || '同步失敗'), 'err');
      btn.disabled = false;
    }
  } catch (e) {
    showResult('❌ 網路錯誤：' + e.message, 'err');
    btn.disabled = false;
  } finally {
    if (!btn.textContent.includes('✅')) btn.textContent = '同步蝦皮 Cookie';
  }
}

async function refreshStatus() {
  const btn = $('refresh-btn');
  btn.disabled    = true;
  btn.textContent = '…';
  await checkBackendCookie();
  btn.disabled    = false;
  btn.textContent = '↻';
}

function updateLastSynced(ts, auto) {
  const el = $('last-synced');
  if (!el) return;
  if (!ts) { el.textContent = ''; return; }
  el.textContent = auto ? `自動同步：${ts}` : `上次同步：${ts}`;
}

async function saveSettings() {
  const backendUrl = $('backend-url').value.trim();
  const adminToken = $('admin-token').value.trim();
  await chrome.storage.local.set({ backendUrl, adminToken });
  showResult('✅ 設定已儲存', 'ok');
  checkBackendCookie();
}

function showResult(msg, type) {
  const el = $('result');
  el.textContent = msg;
  el.className   = 'result show ' + type;
}

(async () => {
  const stored = await new Promise(resolve =>
    chrome.storage.local.get(['backendUrl', 'adminToken', 'lastSynced', 'autoSynced'], resolve)
  );
  const backendUrl = stored.backendUrl || DEFAULT_BACKEND;
  const adminToken = stored.adminToken || DEFAULT_TOKEN;
  $('backend-url').value = backendUrl;
  $('admin-token').value = adminToken;
  if (!backendUrl) $('settings-panel').open = true;
  updateLastSynced(stored.lastSynced, stored.autoSynced);
  await checkLogin();
  await checkBackendCookie();
})();
