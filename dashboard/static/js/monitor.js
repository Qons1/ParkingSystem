import { firebaseConfig } from './firebaseConfig.js';

const cfgEl = document.getElementById('cfg');
const canEdit = (cfgEl?.dataset?.canEdit || 'false') === 'true';
const canAssign = (cfgEl?.dataset?.canAssign || 'false') === 'true';
const saveUrl = cfgEl?.dataset?.saveUrl || '';

const menu = document.getElementById('custom-context-menu');
const saveBtn = document.getElementById('save-layout-btn');
let selectedSlot = null;
let hasUnsaved = false;

let hoverTimer = null;
let lastHoverTarget = null;
let lastMouseEvent = null;
const hoverCard = document.getElementById('hover-details');
// Summary elements
const sumCar = document.getElementById('sum-car-left');
const sumMotor = document.getElementById('sum-motor-left');
const sumPwd = document.getElementById('sum-pwd-left');

function computeAndRenderSummary(occByName){
  // Count total per type from DOM, then subtract occupied
  const totals = { Car: 0, Motorcycle: 0, PWD: 0 };
  const occCounts = { Car: 0, Motorcycle: 0, PWD: 0 };
  document.querySelectorAll('.slot-box').forEach(box => {
    const t = (box.dataset.type || '').trim();
    if (t && totals[t] !== undefined) totals[t] += 1;
    const name = box.dataset.slot;
    const o = occByName[name];
    const isOcc = o && ((o.status || '').toString().toUpperCase() === 'OCCUPIED');
    if (isOcc && t && occCounts[t] !== undefined) occCounts[t] += 1;
  });
  const leftCar = Math.max(0, (totals.Car || 0) - (occCounts.Car || 0));
  const leftMotor = Math.max(0, (totals.Motorcycle || 0) - (occCounts.Motorcycle || 0));
  const leftPwd = Math.max(0, (totals.PWD || 0) - (occCounts.PWD || 0));
  if (sumCar) sumCar.textContent = String(leftCar);
  if (sumMotor) sumMotor.textContent = String(leftMotor);
  if (sumPwd) sumPwd.textContent = String(leftPwd);
}
const hdName = document.getElementById('hd-name');
const hdContact = document.getElementById('hd-contact');
const hdType = document.getElementById('hd-type');
const hdTime = document.getElementById('hd-time');

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
      computeAndRenderSummary(byName);
    });
  } catch (_) {}
  // Ensure hover card is attached to <body> to avoid clipping/stacking issues
  try {
    if (hoverCard && hoverCard.parentElement !== document.body) {
      document.body.appendChild(hoverCard);
      hoverCard.style.position = 'fixed';
    }
  } catch(_) {}
})();

document.querySelectorAll('.slot-box').forEach(box => {
  // Right-click menu visibility depends on role flags
  box.addEventListener('contextmenu', (e) => {
    e.preventDefault();
    selectedSlot = box;
    const showMenu = (canEdit || canAssign);
    menu.style.display = showMenu ? 'block' : 'none';
    if (showMenu) {
      menu.style.left = `${e.pageX}px`;
      menu.style.top = `${e.pageY}px`;
    }
  });

  // Hover show after 1.5s
  box.addEventListener('mouseenter', (e) => {
    clearTimeout(hoverTimer);
    lastHoverTarget = box;
    lastMouseEvent = e;
    hoverTimer = setTimeout(() => {
      if (lastHoverTarget === box) {
        openHoverForName(box, box.dataset.slot, lastMouseEvent || e);
      }
    }, 1500);
  });
  box.addEventListener('mousemove', (e) => {
    lastMouseEvent = e;
    if (hoverCard?.style.display === 'block' && lastHoverTarget === box) {
      positionHoverCard(lastMouseEvent);
    }
  });
  box.addEventListener('mouseleave', () => {
    clearTimeout(hoverTimer);
    lastHoverTarget = null;
    hideHoverCard();
  });

  // Inline rename handling
  box.addEventListener('dblclick', () => {
    if (canEdit) { box.contentEditable = box.isContentEditable ? 'false' : 'true'; box.focus(); }
  });
  box.addEventListener('input', () => { if (box.isContentEditable) enableSave(); });
  box.addEventListener('blur', () => { if (box.isContentEditable) enableSave(); });
});

document.addEventListener('click', () => { menu.style.display = 'none'; });

const editBtn = document.getElementById('edit-option');
const assignBtn = document.getElementById('assign-user-option');
const assignOverlay = document.getElementById('assign-overlay');
const assignSlotName = document.getElementById('assign-slot-name');
const assignSelect = document.getElementById('assign-user-select');
const assignCancel = document.getElementById('assign-cancel');
const assignConfirm = document.getElementById('assign-confirm');
if (editBtn) {
  editBtn.addEventListener('click', () => {
    if (!canEdit) return;
    if (selectedSlot) { selectedSlot.contentEditable = 'true'; selectedSlot.focus(); }
    menu.style.display = 'none';
  });
}
if (assignBtn) {
  assignBtn.addEventListener('click', async () => {
    try {
      menu.style.display = 'none';
      if (!selectedSlot || !assignOverlay) return;
      const slotName = selectedSlot.dataset.slot;
      assignSlotName && (assignSlotName.textContent = slotName);
      // load candidates
      const appMod = await import('https://www.gstatic.com/firebasejs/11.0.1/firebase-app.js');
      const dbMod = await import('https://www.gstatic.com/firebasejs/11.0.1/firebase-database.js');
      const app = appMod.getApps && appMod.getApps().length ? appMod.getApp() : appMod.initializeApp(firebaseConfig);
      const db = dbMod.getDatabase(app);
      const [usersSnap, txSnap] = await Promise.all([
        dbMod.get(dbMod.ref(db, '/users')),
        dbMod.get(dbMod.ref(db, '/transactions')),
      ]);
      const users = usersSnap.exists() ? usersSnap.val() || {} : {};
      const txs = txSnap.exists() ? txSnap.val() || {} : {};
      const candidates = [];
      Object.entries(users).forEach(([uid, u]) => {
        const txId = u?.activeTransaction; if (!txId) return;
        const t = txs[txId]; const hasSlot = !!(t && t.slot);
        if (!hasSlot) candidates.push({ uid, txId, name: u.displayName || u.email || uid });
      });
      assignSelect.innerHTML = '';
      if (!candidates.length) {
        const opt = document.createElement('option'); opt.value=''; opt.textContent='No eligible users'; assignSelect.appendChild(opt);
      } else {
        candidates.forEach((c) => { const opt = document.createElement('option'); opt.value = JSON.stringify(c); opt.textContent = `${c.name} [${c.txId.slice(0,6)}]`; assignSelect.appendChild(opt); });
      }
      assignOverlay.style.display = 'flex'; assignOverlay.setAttribute('aria-hidden','false');

      const close = ()=>{ assignOverlay.style.display='none'; assignOverlay.setAttribute('aria-hidden','true'); };
      assignCancel?.addEventListener('click', close, { once:true });
      assignConfirm?.addEventListener('click', async ()=>{
        try {
          const v = assignSelect.value; if (!v) { close(); return; }
          const chosen = JSON.parse(v);
          await dbMod.update(dbMod.ref(db, '/transactions/' + chosen.txId), { slot: slotName });
          const safeKey = slotName.replaceAll('/', '_').replaceAll('.', '_').replaceAll('#','_').replaceAll('[','(').replaceAll(']',')');
          await dbMod.set(dbMod.ref(db, '/configurations/layout/occupied/' + safeKey), {
            uid: chosen.uid, txId: chosen.txId, status: 'OCCUPIED', timeIn: new Date().toISOString(), vehicleType: 'CAR', slotName
          });
        } catch(_) { alert('Failed to assign.'); }
        close();
      }, { once:true });
    } catch (e) { alert('Failed to open assign modal.'); }
  });
}
// Removed details via context menu – now handled by hover

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
    let ok = res.ok; try { const j = await res.json(); if (j && j.ok === false) ok = false; } catch(_){ }
    const toast = document.getElementById('save-toast');
    if (toast) { toast.textContent = ok ? 'Changes saved to Firebase' : 'Save failed'; toast.style.display = 'block'; setTimeout(() => { toast.style.display = 'none'; }, 1600); }
    if (ok) { hasUnsaved = false; saveBtn.style.opacity = '.6'; saveBtn.style.cursor = 'not-allowed'; saveBtn.disabled = true; }
  } catch(_){ }
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

function positionHoverCard(evt){
  if (!hoverCard) return;
  const pad = 12;
  const vw = window.innerWidth;
  const vh = window.innerHeight;
  let x = (evt?.clientX || 0) + pad;
  let y = (evt?.clientY || 0) + pad;
  const rect = hoverCard.getBoundingClientRect();
  if (x + rect.width > vw - 8) x = Math.max(8, vw - rect.width - 8);
  if (y + rect.height > vh - 8) y = Math.max(8, vh - rect.height - 8);
  hoverCard.style.left = `${x}px`;
  hoverCard.style.top = `${y}px`;
}

async function openHoverForName(box, slotName, evt){
  if (!hoverCard) return;
  hdName.textContent = 'Loading…';
  hdContact.textContent = '';
  hdType.textContent = '';
  hdTime.textContent = '';
  hoverCard.style.display = 'block';
  hoverCard.setAttribute('aria-hidden', 'false');
  positionHoverCard(evt);
  try {
    const occ = (window.__occByName || {})[slotName];
    if (!occ || !occ.uid) { hdName.textContent = 'N/A'; return; }
    const appMod = await import('https://www.gstatic.com/firebasejs/11.0.1/firebase-app.js');
    const dbMod = await import('https://www.gstatic.com/firebasejs/11.0.1/firebase-database.js');
    const app = appMod.getApps && appMod.getApps().length ? appMod.getApp() : appMod.initializeApp(firebaseConfig);
    const db = dbMod.getDatabase(app);
    const snap = await dbMod.get(dbMod.ref(db, '/users/' + occ.uid));
    if (snap.exists()) {
      const u = snap.val() || {};
      hdName.textContent = u.displayName || u.email || occ.uid;
      hdContact.textContent = u.contactNumber || '';
      hdType.textContent = u.isPWD ? 'pwd' : 'regular';
      hdTime.textContent = occ.timeIn || '';
    } else { hdName.textContent = occ.uid; }
  } catch(_) {
    hdName.textContent = 'N/A';
  }
}

function hideHoverCard(){
  if (!hoverCard) return;
  hoverCard.style.display = 'none';
  hoverCard.setAttribute('aria-hidden', 'true');
}


