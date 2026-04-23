const $ = id => document.getElementById(id);

async function loadSettings() {
  return new Promise(resolve => {
    chrome.storage.local.get(['backendUrl', 'adminToken'], data => resolve(data));
  });
}

async function checkLogin() {
  const cookies = await chrome.cookies.getAll({ domain: 'shopee.tw' });
  const uid = cookies.find(c => c.name === 'SPC_U');
  const dot  = $('status-dot');
  const text = $('status-text');
  const btn  = $('sync-btn');

  if (uid && uid.value && uid.value !== '0') {
    dot.className  = 'dot green';
    text.textContent = `已登入蝦皮（UID: ${uid.value}）`;
    btn.disabled   = false;
  } else {
    dot.className  = 'dot red';
    text.textContent = '尚未登入蝦皮，請先到蝦皮登入';
    btn.disabled   = true;
  }
}

async function syncCookie() {
  const { backendUrl, adminToken } = await loadSettings();

  if (!backendUrl) {
    showResult('請先在設定中填入後端 URL', 'err');
    $('settings-panel').open = true;
    return;
  }
  if (!adminToken) {
    showResult('請先在設定中填入 Admin Token', 'err');
    $('settings-panel').open = true;
    return;
  }

  const btn = $('sync-btn');
  btn.disabled = true;
  btn.textContent = '同步中…';

  try {
    const cookies = await chrome.cookies.getAll({ domain: 'shopee.tw' });
    const cookieStr = cookies.map(c => `${c.name}=${c.value}`).join('; ');

    const res = await fetch(`${backendUrl.replace(/\/$/, '')}/admin/update-shopee-cookie`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-Admin-Token': adminToken,
      },
      body: JSON.stringify({ cookie: cookieStr }),
    });

    const data = await res.json();
    if (res.ok) {
      showResult(`✅ 同步成功！Cookie 長度：${data.length} 字元`, 'ok');
    } else {
      showResult('❌ ' + (data.detail || '同步失敗'), 'err');
    }
  } catch (e) {
    showResult('❌ 網路錯誤：' + e.message, 'err');
  } finally {
    btn.disabled = false;
    btn.textContent = '同步蝦皮 Cookie';
  }
}

async function saveSettings() {
  const backendUrl  = $('backend-url').value.trim();
  const adminToken  = $('admin-token').value.trim();
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
  if (backendUrl)  $('backend-url').value  = backendUrl;
  if (adminToken)  $('admin-token').value  = adminToken;
  if (!backendUrl || !adminToken) $('settings-panel').open = true;
  await checkLogin();
})();
