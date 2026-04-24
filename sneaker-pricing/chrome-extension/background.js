const DEFAULT_BACKEND = 'https://sneaker-pricing-production.up.railway.app';
const DEFAULT_TOKEN   = '400c67e13ef5cbc3b80b08c0cd2bdd24cc8ef75de53a547a';

chrome.runtime.onInstalled.addListener(() => {
  chrome.alarms.create('auto-sync-check', { periodInMinutes: 360 }); // 每 6 小時
  updateBadge();
});

chrome.runtime.onStartup.addListener(() => {
  updateBadge();
});

chrome.alarms.onAlarm.addListener(async (alarm) => {
  if (alarm.name === 'auto-sync-check') {
    await autoSyncIfNeeded();
  }
});

async function getSettings() {
  return new Promise(resolve => {
    chrome.storage.local.get(['backendUrl', 'adminToken'], stored => {
      resolve({
        backendUrl: stored.backendUrl || DEFAULT_BACKEND,
        adminToken: stored.adminToken || DEFAULT_TOKEN,
      });
    });
  });
}

async function updateBadge() {
  const { backendUrl, adminToken } = await getSettings();
  try {
    const res  = await fetch(`${backendUrl.replace(/\/$/, '')}/admin/cookie-status`, {
      headers: { 'X-Admin-Token': adminToken },
    });
    const data = await res.json();
    if (res.ok && (data.length || 0) > 200) {
      chrome.action.setBadgeText({ text: '' });
    } else {
      chrome.action.setBadgeText({ text: '!' });
      chrome.action.setBadgeBackgroundColor({ color: '#ef4444' });
    }
  } catch {
    chrome.action.setBadgeText({ text: '?' });
    chrome.action.setBadgeBackgroundColor({ color: '#6b7280' });
  }
}

async function autoSyncIfNeeded() {
  const { backendUrl, adminToken } = await getSettings();

  // 確認蝦皮已登入
  const cookies = await chrome.cookies.getAll({ domain: 'shopee.tw' });
  const uid = cookies.find(c => c.name === 'SPC_U');
  if (!uid || !uid.value || uid.value === '0') {
    updateBadge();
    return;
  }

  try {
    const statusRes  = await fetch(`${backendUrl.replace(/\/$/, '')}/admin/cookie-status`, {
      headers: { 'X-Admin-Token': adminToken },
    });
    const statusData = await statusRes.json();

    // cookie 仍有效，不需同步
    if (statusRes.ok && (statusData.length || 0) > 200) {
      chrome.action.setBadgeText({ text: '' });
      return;
    }

    // 自動同步
    const cookieStr = cookies.map(c => `${c.name}=${c.value}`).join('; ');
    const syncRes   = await fetch(`${backendUrl.replace(/\/$/, '')}/admin/update-shopee-cookie`, {
      method: 'POST',
      headers: {
        'Content-Type':  'application/json',
        'X-Admin-Token': adminToken,
      },
      body: JSON.stringify({ cookie: cookieStr }),
    });

    if (syncRes.ok) {
      const now = new Date().toLocaleString('zh-TW', { hour12: false });
      await chrome.storage.local.set({ lastSynced: now, autoSynced: true });
      // 短暫顯示綠色勾，之後清除
      chrome.action.setBadgeText({ text: '✓' });
      chrome.action.setBadgeBackgroundColor({ color: '#22c55e' });
      setTimeout(() => chrome.action.setBadgeText({ text: '' }), 8000);
    } else {
      chrome.action.setBadgeText({ text: '!' });
      chrome.action.setBadgeBackgroundColor({ color: '#ef4444' });
    }
  } catch {
    chrome.action.setBadgeText({ text: '?' });
    chrome.action.setBadgeBackgroundColor({ color: '#6b7280' });
  }
}
