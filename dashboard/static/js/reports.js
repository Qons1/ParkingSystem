import { firebaseConfig } from './firebaseConfig.js';

const cfg = document.getElementById('cfg');
const isAdmin = (cfg?.dataset?.isAdmin === 'true');
const resolveUrl = cfg?.dataset?.resolveUrl || '';

const tbody = document.getElementById('incidentsBody');
const overlay = document.getElementById('imgOverlay');
const imgFull = document.getElementById('imgFull');

let app, db, appMod, dbMod;
(async () => {
  appMod = await import('https://www.gstatic.com/firebasejs/11.0.1/firebase-app.js');
  dbMod = await import('https://www.gstatic.com/firebasejs/11.0.1/firebase-database.js');
  app = appMod.initializeApp(firebaseConfig, 'reports');
  db = dbMod.getDatabase(app);

  dbMod.onValue(dbMod.ref(db, '/incidents'), async (snap) => {
    const data = snap.val() || {};
    const entries = Object.values(data);
    const uidSet = new Set(entries.map((r) => r.uid).filter(Boolean));
    const nameByUid = {};
    for (const uid of uidSet) {
      try {
        const us = await dbMod.get(dbMod.ref(db, `/users/${uid}/displayName`));
        nameByUid[uid] = us.exists() ? (us.val() || '') : '';
      } catch { nameByUid[uid] = ''; }
    }
    const rows = entries.map((r) => {
      const imgUrl = r.imageUrl || '';
      const img = imgUrl ? `<img src="${imgUrl}" data-full="${imgUrl}" class="incident-thumb" style="height:120px;width:150px;border-radius:4px;cursor:pointer;"/>` : '';
      const desc = (r.description || '').replace(/</g,'&lt;');
      const reporter = nameByUid[r.uid] || r.uid || '';
      const ts = r.timestamp || '';
      const st = r.status || '';
      const id = r.incidentId || '';
      const actionBtn = (st === 'OPEN' && isAdmin) ? '<button class="resolve-btn">Resolve</button>' : '';
      return `<tr data-id="${id}">
        <td style="padding: 2px;text-align:center;">${img}</td>
        <td>${desc}</td>
        <td>${reporter}</td>
        <td>${ts}</td>
        <td>${actionBtn || st}</td>
      </tr>`;
    });
    tbody.innerHTML = rows.length ? rows.join('') : `<tr><td colspan="5" style="text-align:center;color:#777;">No incidents.</td></tr>`;
  });
})();

tbody.addEventListener('click', async (e) => {
  const t = e.target;
  if (t && t.classList && t.classList.contains('incident-thumb')) {
    imgFull.src = t.getAttribute('data-full') || t.src || '';
    overlay.style.display = 'flex';
    overlay.setAttribute('aria-hidden','false');
    return;
  }
  const btn = t.closest?.('.resolve-btn');
  if (btn && isAdmin && resolveUrl) {
    const tr = btn.closest('tr');
    const id = tr?.getAttribute('data-id');
    if (!id) return;
    try { await fetch(resolveUrl, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ incidentId: id }) }); } catch {}
  }
});

overlay.addEventListener('click', () => {
  overlay.style.display = 'none';
  overlay.setAttribute('aria-hidden','true');
  imgFull.src = '';
});


