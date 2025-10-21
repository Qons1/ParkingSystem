import { firebaseConfig } from './firebaseConfig.js';

const cfg = document.getElementById('cfg');
const isAdmin = (cfg && cfg.dataset && cfg.dataset.isAdmin === 'true');
const resolveUrl = (cfg && cfg.dataset && cfg.dataset.resolveUrl) ? cfg.dataset.resolveUrl : '';

const tbody = document.getElementById('incidentsBody');
const overlay = document.getElementById('imgOverlay');
const imgFull = document.getElementById('imgFull');

let app, db, appMod, dbMod;
(async () => {
  try { console.log('[reports] init start', { isAdmin, resolveUrl }); } catch {}
  appMod = await import('https://www.gstatic.com/firebasejs/11.0.1/firebase-app.js');
  dbMod = await import('https://www.gstatic.com/firebasejs/11.0.1/firebase-database.js');
  app = appMod.initializeApp(firebaseConfig, 'reports');
  db = dbMod.getDatabase(app);

  dbMod.onValue(dbMod.ref(db, '/incidents'), async (snap) => {
    try { console.log('[reports] incidents onValue fired'); } catch {}
    const data = snap.val() || {};
    // Keep keys and filter out resolved incidents so they disappear from the list
    const entries = Object.entries(data)
      .filter(([id, r]) => {
        if (!r) return false;
        const st = String(r.status || '').trim().toUpperCase();
        return st !== 'RESOLVED';
      });

    // Auto-finalize items pending user confirmation past deadline if admin
    try {
      const now = Date.now();
      for (const [id, r] of entries) {
        const st = String(r.status || '').toUpperCase();
        const dl = Number(r.confirmDeadline || 0);
        const rid = (r.incidentId && String(r.incidentId).length) ? r.incidentId : id;
        if (isAdmin && resolveUrl && st === 'PENDING_USER_CONFIRM' && dl > 0 && dl <= now) {
          fetch(resolveUrl, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ incidentId: rid, finalize: true }) }).catch(()=>{});
        }
      }
    } catch {}
    const uidSet = new Set(entries.map(([id, r]) => r.uid).filter(Boolean));
    const nameByUid = {};
    for (const uid of uidSet) {
      try {
        const us = await dbMod.get(dbMod.ref(db, `/users/${uid}/displayName`));
        nameByUid[uid] = us.exists() ? (us.val() || '') : '';
      } catch { nameByUid[uid] = ''; }
    }
    const rows = entries.map(([id, r]) => {
      const imgUrl = r.imageUrl || '';
      const img = imgUrl ? `<img src="${imgUrl}" data-full="${imgUrl}" class="incident-thumb" style="height:120px;width:150px;border-radius:4px;cursor:pointer;"/>` : '';
      const desc = (r.description || '').replace(/</g,'&lt;');
      const reporter = nameByUid[r.uid] || r.uid || '';
      const ts = r.timestamp || '';
      const st = (r.status || '').toString();
      // Prefer record key; fallback to stored incidentId if present
      const rid = (r.incidentId && String(r.incidentId).length) ? r.incidentId : id;
      const normSt = st.trim().toUpperCase();
      const showBtn = isAdmin && normSt !== 'RESOLVED';
      const actionBtn = showBtn ? `<button type="button" class="resolve-btn" data-id="${rid}" style="cursor:pointer;">Resolve</button>` : '';
      return `<tr data-id="${rid}">
        <td style="padding: 2px;text-align:center;">${img}</td>
        <td>${desc}</td>
        <td>${reporter}</td>
        <td>${ts}</td>
        <td>${actionBtn || st}</td>
      </tr>`;
    });
    const html = rows.length ? rows.join('') : `<tr><td colspan="5" style="text-align:center;color:#777;">No incidents.</td></tr>`;
    tbody.innerHTML = html;
    try { console.log('[reports] render rows', { count: rows.length }); } catch {}
  });
})();

tbody.addEventListener('click', async (e) => {
  const t = e.target;
  const el = (t && t.nodeType === 1) ? t : (t && t.parentElement ? t.parentElement : null);
  if (el && el.classList && el.classList.contains('incident-thumb')) {
    imgFull.src = t.getAttribute('data-full') || t.src || '';
    overlay.style.display = 'flex';
    overlay.setAttribute('aria-hidden','false');
    return;
  }
  const btn = el && (el.classList?.contains('resolve-btn') ? el : el.closest?.('.resolve-btn'));
  if (btn && isAdmin && resolveUrl) {
    const tr = btn.closest('tr');
    const id = tr?.getAttribute('data-id');
    if (!id) return;
    // First request: mark as PENDING_USER_CONFIRM and set deadline; not final
    try {
      console.log('[reports] clicking resolve', { id, resolveUrl });
      const res = await fetch(resolveUrl, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ incidentId: id, finalize: false }) });
      console.log('[reports] resolve response', res.status);
    } catch (e) { console.error('[reports] resolve error', e); }
  }
});

overlay.addEventListener('click', () => {
  overlay.style.display = 'none';
  overlay.setAttribute('aria-hidden','true');
  imgFull.src = '';
});


