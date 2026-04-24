const $ = id => document.getElementById(id);

// 打包給朋友前，把這兩行填好即可——朋友裝完就能直接用
const DEFAULT_BACKEND = 'https://sneaker-pricing-production.up.railway.app';  // 例：'https://cc-sneaker.railway.app'
const DEFAULT_TOKEN   = '400c67e13ef5cbc3b80b08c0cd2bdd24cc8ef75de53a547a';

async function loadSettings() {
  return new Promise(resolve => {
    chrome.storage.local.get(['backendUrl', 'adminToken'], stored => {
      resolve({
        backendUrl:  stored.backendUrl  || DEFAULT_BACKEND,
        adminToken:  stored.adminToken  || DEFAULT_TOKEN,
      });
    });
  });
}

async function checkLogin() {
  const cookies = await chrome.cookies.getAll({ domain: 'shopee.tw' });
  const uid = cookies.find(c => c.name === 'SPC_U');
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
        'X-Timestamp':   Date.now().toString(),
      },
      body: JSON.stringify({ cookie: cookieStr }),
    });

    const data = await res.json();
    if (res.ok) {
      btn.textContent = '✅ 已同步';
      btn.style.background = 'var(--green)';
      showResult(`同步成功！Cookie 長度：${data.length} 字元`, 'ok');
      setTimeout(() => {
        btn.textContent = '同步蝦皮 Cookie';
        btn.style.background = '';
      }, 3000);
    } else {
      showResult('❌ ' + (data.detail || '同步失敗'), 'err');
    }
  } catch (e) {
    showResult('❌ 網路錯誤：' + e.message, 'err');
  } finally {
    btn.disabled = false;
    if (!btn.textContent.includes('✅')) btn.textContent = '同步蝦皮 Cookie';
  }
}

async function saveSettings() {
  const backendUrl = $('backend-url').value.trim();
  const adminToken = $('admin-token').value.trim();
  await chrome.storage.local.set({ backendUrl, adminToken });
  showResult('✅ 設定已儲存', 'ok');
}

function showResult(msg, type) {
  const el = $('result');
  el.textContent = msg;
  el.className   = 'result show ' + type;
}

// 初始化
(async () => {
  const { backendUrl, adminToken } = await loadSettings();
  $('backend-url').value = backendUrl;
  $('admin-token').value = adminToken;
  if (!backendUrl) $('settings-panel').open = true;
  await checkLogin();
})();
