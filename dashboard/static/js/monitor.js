import { firebaseConfig } from './firebaseConfig.js';

const cfgEl = document.getElementById('cfg');
const canEdit = (cfgEl?.dataset?.canEdit || 'false') === 'true';
const saveUrl = cfgEl?.dataset?.saveUrl || '';

const menu = document.getElementById('custom-context-menu');
const saveBtn = document.getElementById('save-layout-btn');
let selectedSlot = null;
let hasUnsaved = false;

function enableSave() {
  if (!saveBtn) return;
  hasUnsaved = true;
  saveBtn.style.opacity = '1';
  saveBtn.style.cursor = 'pointer';
  saveBtn.disabled = false;
}

(async () => {
  try {
    const appMod = await import('https://www.gstatic.com/firebasejs/11.0.1/firebase-app.js');
    const dbMod = await import('https://www.gstatic.com/firebasejs/11.0.1/firebase-database.js');
    const app = appMod.initializeApp(firebaseConfig);
    const db = dbMod.getDatabase(app);
    const occRef = dbMod.ref(db, '/configurations/layout/occupied');
    dbMod.onValue(occRef, (snap) => {
      const occ = snap.val() || {};
      const byName = {};
      Object.entries(occ).forEach(([k, v]) => { byName[v?.slotName || k] = v; });
      document.querySelectorAll('.slot-box').forEach(box => {
        const name = box.dataset.slot;
        const o = byName[name];
        const isOcc = o && ((o.status || '').toString().toUpperCase() === 'OCCUPIED');
        box.style.background = isOcc ? '#ffdddd' : '#f7f7f7';
        box.style.borderColor = isOcc ? '#d33' : '#ccc';
      });
      window.__occByName = byName;
    });
  } catch (_) {}
})();

document.querySelectorAll('.slot-box').forEach(box => {
  box.addEventListener('contextmenu', (e) => {
    e.preventDefault();
    selectedSlot = box;
    menu.style.display = 'block';
    menu.style.left = `${e.pageX}px`;
    menu.style.top = `${e.pageY}px`;
  });
  box.addEventListener('dblclick', () => {
    if (canEdit) { box.contentEditable = box.isContentEditable ? 'false' : 'true'; box.focus(); }
    else { openDetailsForName(box.dataset.slot); }
  });
  box.addEventListener('blur', () => { if (box.isContentEditable) enableSave(); });
});

document.addEventListener('click', () => { menu.style.display = 'none'; });

const editBtn = document.getElementById('edit-option');
if (editBtn) {
  editBtn.addEventListener('click', () => {
    if (!canEdit) return;
    if (selectedSlot) { selectedSlot.contentEditable = 'true'; selectedSlot.focus(); }
    menu.style.display = 'none';
  });
}
document.getElementById('details-option')?.addEventListener('click', () => {
  if (selectedSlot) { openDetailsForName(selectedSlot.dataset.slot); }
  menu.style.display = 'none';
});

saveBtn?.addEventListener('click', async () => {
  if (!hasUnsaved || !saveUrl) return;
  const labels = {};
  document.querySelectorAll('.slot-box').forEach(el => {
    const slotId = el.dataset.slot;
    const name = el.textContent.trim();
    if (slotId && name) labels[slotId] = name;
  });
  try {
    const res = await fetch(saveUrl, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ labels }) });
    let ok = res.ok; try { const j = await res.json(); if (j && j.ok === false) ok = false; } catch(_){}
    const toast = document.getElementById('save-toast');
    toast.textContent = ok ? 'Changes saved to Firebase' : 'Save failed';
    toast.style.display = 'block'; setTimeout(() => { toast.style.display = 'none'; }, 1600);
    if (ok) { hasUnsaved = false; saveBtn.style.opacity = '.6'; saveBtn.style.cursor = 'not-allowed'; saveBtn.disabled = true; }
  } catch(_){}
});

async function openDetailsForName(slotName){
  const overlay = document.getElementById('user-details-overlay');
  const mName = document.getElementById('m-name');
  const mContact = document.getElementById('m-contact');
  const mType = document.getElementById('m-type');
  const mTime = document.getElementById('m-time');
  mName.textContent = 'Loading…'; mContact.textContent=''; mType.textContent=''; mTime.textContent='';
  overlay.style.display = 'flex'; overlay.setAttribute('aria-hidden','false');
  try {
    const appMod = await import('https://www.gstatic.com/firebasejs/11.0.1/firebase-app.js');
    const dbMod = await import('https://www.gstatic.com/firebasejs/11.0.1/firebase-database.js');
    const app = appMod.getApps && appMod.getApps().length ? appMod.getApp() : appMod.initializeApp(firebaseConfig);
    const db = dbMod.getDatabase(app);
    const occ = (window.__occByName || {})[slotName];
    if (!occ || !occ.uid) { mName.textContent='N/A'; return; }
    const snap = await dbMod.get(dbMod.ref(db, '/users/' + occ.uid));
    if (snap.exists()) {
      const u = snap.val() || {};
      mName.textContent = u.displayName || u.email || occ.uid;
      mContact.textContent = u.contactNumber || '';
      mType.textContent = u.isPWD ? 'pwd' : 'regular';
      mTime.textContent = occ.timeIn || '';
    } else { mName.textContent = occ.uid; }
  } catch(_) { mName.textContent = 'N/A'; }
}


