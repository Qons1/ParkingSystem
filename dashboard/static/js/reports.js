import { firebaseConfig } from './firebaseConfig.js';

const cfg = document.getElementById('cfg');
const isAdmin = (cfg && cfg.dataset && cfg.dataset.isAdmin === 'true');
const resolveUrl = (cfg && cfg.dataset && cfg.dataset.resolveUrl) ? cfg.dataset.resolveUrl : '';

const tbody = document.getElementById('incidentsBody');
const pastBody = document.getElementById('pastIncidentsBody');
const tabBtnCurrent = document.getElementById('tabBtnCurrent');
const tabBtnPast = document.getElementById('tabBtnPast');
const tabCurrent = document.getElementById('tabCurrent');
const tabPast = document.getElementById('tabPast');
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
    let entries = Object.entries(data)
      .filter(([id, r]) => {
        if (!r) return false;
        const st = String(r.status || '').trim().toUpperCase();
        return st !== 'RESOLVED';
      });

    // Sort by priority (high > medium > low), then timestamp desc
    const weight = (p) => ({ HIGH:3, MEDIUM:2, LOW:1 }[String(p||'').toUpperCase()]||0);
    entries.sort((a,b)=>{
      const pa = weight(a[1]?.priority);
      const pb = weight(b[1]?.priority);
      if (pb !== pa) return pb - pa;
      const ta = String(a[1]?.timestamp||'');
      const tb = String(b[1]?.timestamp||'');
      return tb.localeCompare(ta);
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
      const cat = (r.categoryTitle || '').toString().replace(/</g,'&lt;');
      const descOnly = (r.description || '').toString().replace(/</g,'&lt;');
      const desc = cat ? `<strong>${cat}</strong><br/>${descOnly}` : descOnly;
      const reporter = nameByUid[r.uid] || r.uid || '';
      const ts = r.timestamp || '';
      const st = (r.status || '').toString();
      const pr = (r.priority || '').toString();
      const prBadge = pr ? `<span class="prio prio-${pr.toLowerCase()}">${pr.toUpperCase()}</span>` : '';
      // Prefer record key; fallback to stored incidentId if present
      const rid = (r.incidentId && String(r.incidentId).length) ? r.incidentId : id;
      const normSt = st.trim().toUpperCase();
      const showBtn = isAdmin && normSt !== 'RESOLVED';
      const actionBtn = showBtn ? `<button type="button" class="resolve-btn" data-id="${rid}" style="cursor:pointer;">Resolve</button>` : '';
      return `<tr data-id="${rid}">
        <td style="padding: 2px;text-align:center;">${img}</td>
        <td>${desc}</td>
        <td style="white-space:nowrap;">${prBadge}</td>
        <td>${reporter}</td>
        <td>${ts}</td>
        <td>${actionBtn || st.replace(/_/g,' ')}</td>
      </tr>`;
    });
    const html = rows.length ? rows.join('') : `<tr><td colspan="6" style="text-align:center;color:#777;">No incidents.</td></tr>`;
    tbody.innerHTML = html;
    try { console.log('[reports] render rows', { count: rows.length }); } catch {}
  });

  // Load past incidents into the Past Reports tab
  dbMod.onValue(dbMod.ref(db, '/pastIncidents'), async (snap) => {
    if (!pastBody) return;
    const data = snap.val() || {};
    let entries = Object.entries(data || {});
    // Sort by resolvedAt desc
    entries.sort((a,b)=>{
      const ta = Number(a[1]?.resolvedAt||0);
      const tb = Number(b[1]?.resolvedAt||0);
      return tb - ta;
    });
    // Preload names
    const uidSet = new Set(entries.map(([id, r]) => r?.uid).filter(Boolean));
    const nameByUid = {};
    for (const uid of uidSet) {
      try {
        const us = await dbMod.get(dbMod.ref(db, `/users/${uid}/displayName`));
        nameByUid[uid] = us.exists() ? (us.val() || '') : '';
      } catch { nameByUid[uid] = ''; }
    }
    const rows = entries.map(([id, r])=>{
      const imgUrl = r?.imageUrl || '';
      const img = imgUrl ? `<img src="${imgUrl}" data-full="${imgUrl}" class="incident-thumb" style="height:90px;width:120px;border-radius:4px;cursor:pointer;"/>` : '';
      const cat = (r?.categoryTitle || '').toString().replace(/</g,'&lt;');
      const descOnly = (r?.description || '').toString().replace(/</g,'&lt;');
      const desc = cat ? `<strong>${cat}</strong><br/>${descOnly}` : descOnly;
      const reporter = nameByUid[r?.uid] || r?.uid || '';
      const ts = r?.timestamp || '';
      const rs = r?.resolvedAt ? new Date(Number(r.resolvedAt)).toLocaleString() : '';
      return `<tr>
        <td style="padding:2px;text-align:center;">${img}</td>
        <td>${desc}</td>
        <td style="white-space:nowrap;">${(r?.priority||'').toString().toUpperCase()}</td>
        <td>${reporter}</td>
        <td>${ts}</td>
        <td>${rs}</td>
      </tr>`;
    });
    pastBody.innerHTML = rows.length ? rows.join('') : `<tr><td colspan="6" style="text-align:center;color:#777;">No past reports.</td></tr>`;
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
    // Immediate resolve: finalize=true and optimistically remove row
    try {
      tr?.remove();
      await fetch(resolveUrl, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ incidentId: id, finalize: true })
      });
    } catch (e) {
      console.error('[reports] resolve error', e);
    }
  }
});

overlay.addEventListener('click', () => {
  overlay.style.display = 'none';
  overlay.setAttribute('aria-hidden','true');
  imgFull.src = '';
});

// Tabs
function showTab(which){
  if (!tabCurrent || !tabPast) return;
  if (which === 'past') {
    tabCurrent.style.display = 'none';
    tabPast.style.display = 'block';
    if (tabBtnCurrent) tabBtnCurrent.style.background = '#f3f3f3';
    if (tabBtnPast) tabBtnPast.style.background = '#e6f0ff';
  } else {
    tabCurrent.style.display = 'block';
    tabPast.style.display = 'none';
    if (tabBtnCurrent) tabBtnCurrent.style.background = '#e6f0ff';
    if (tabBtnPast) tabBtnPast.style.background = '#f3f3f3';
  }
}
tabBtnCurrent?.addEventListener('click', ()=> showTab('current'));
tabBtnPast?.addEventListener('click', ()=> showTab('past'));
showTab('current');


