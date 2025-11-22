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
const hdTimeLeft = document.getElementById('hd-time-left');
const mTimeLeft = document.getElementById('m-time-left');
const mDeadline = document.getElementById('m-deadline');
const mViolationStatus = document.getElementById('m-violation-status');
const sendViolationBtn = document.getElementById('send-violation-btn');
const stopViolationBtn = document.getElementById('stop-violation-btn');
const violationModal = document.getElementById('violation-modal');
const violationMessageInput = document.getElementById('violation-message-input');
const violationSendBtn = document.getElementById('violation-send-btn');
const violationCancelBtn = document.getElementById('violation-cancel-btn');
const violationCharCount = document.getElementById('violation-char-count');
const toastEl = document.getElementById('save-toast');
const adminEmail = cfgEl?.dataset?.adminEmail || '';

let currentUid = null;
let currentSlotName = null;
let currentTxId = null;
let currentClosingInfo = null;
let closingTicker = null;
let violationActive = false;
const closingCache = new Map();

function enableSave() {
  if (!saveBtn) return;
  hasUnsaved = true;
  saveBtn.style.opacity = '1';
  saveBtn.style.cursor = 'pointer';
  saveBtn.disabled = false;
}

function showToast(message, variant = 'info') {
  if (!toastEl) return;
  toastEl.textContent = message;
  toastEl.style.background = variant === 'error' ? '#b40000' : '#333';
  toastEl.style.display = 'block';
  setTimeout(() => {
    if (toastEl.style.display === 'block') {
      toastEl.style.display = 'none';
    }
  }, 2200);
}

let cachedDbPromise = null;
async function getFirebaseDb() {
  if (!cachedDbPromise) {
    cachedDbPromise = (async () => {
      const appMod = await import('https://www.gstatic.com/firebasejs/11.0.1/firebase-app.js');
      const dbMod = await import('https://www.gstatic.com/firebasejs/11.0.1/firebase-database.js');
      const app = appMod.getApps && appMod.getApps().length ? appMod.getApp() : appMod.initializeApp(firebaseConfig);
      const db = dbMod.getDatabase(app);
      return { appMod, dbMod, db };
    })();
  }
  return cachedDbPromise;
}

function shortText(str, limit = 60) {
  if (!str) return '';
  return str.length > limit ? `${str.slice(0, limit)}…` : str;
}

function formatDateTime(value) {
  if (value === null || value === undefined || value === '') return '';
  let date;
  if (typeof value === 'number') {
    date = new Date(value);
  } else if (typeof value === 'string') {
    finalParsed:
    {
      const numeric = Number(value);
      if (!Number.isNaN(numeric) && numeric > 0) {
        date = new Date(numeric);
        if (!Number.isNaN(date.valueOf())) break finalParsed;
      }
      date = new Date(value);
    }
  } else {
    date = new Date(value);
  }
  if (Number.isNaN(date.valueOf())) return String(value);
  return date.toLocaleString();
}

function formatTimeRemaining(deadlineMs) {
  if (!deadlineMs && deadlineMs !== 0) return { label: '—', short: '—' };
  const deadline = Number(deadlineMs);
  if (!Number.isFinite(deadline)) return { label: '—', short: '—' };
  const diff = deadline - Date.now();
  if (diff <= 0) return { label: 'Overdue', short: 'Overdue' };
  const minutes = Math.floor(diff / 60000);
  const hours = Math.floor(minutes / 60);
  const remMins = minutes % 60;
  const parts = [];
  if (hours > 0) parts.push(`${hours} hr${hours === 1 ? '' : 's'}`);
  if (remMins > 0) parts.push(`${remMins} min${remMins === 1 ? '' : 's'}`);
  if (!parts.length) return { label: '< 1 min', short: '<1m' };
  const label = parts.join(' ');
  return { label, short: label };
}

function stopClosingTicker() {
  if (closingTicker) {
    clearInterval(closingTicker);
    closingTicker = null;
  }
}

function updateClosingDisplay() {
  if (!mTimeLeft) return;
  if (!currentClosingInfo || !currentClosingInfo.deadline) {
    mTimeLeft.textContent = '—';
    mTimeLeft.classList.remove('text-danger');
    if (mDeadline) mDeadline.textContent = '—';
    if (hdTimeLeft) hdTimeLeft.textContent = '—';
    return;
  }
  const deadline = Number(currentClosingInfo.deadline);
  const formatted = formatTimeRemaining(deadline);
  mTimeLeft.textContent = formatted.label;
  if (mDeadline) {
    mDeadline.textContent = formatDateTime(deadline);
  }
  if (hdTimeLeft) hdTimeLeft.textContent = formatted.short;
  if (deadline && Date.now() > deadline) {
    mTimeLeft.classList.add('text-danger');
  } else {
    mTimeLeft.classList.remove('text-danger');
  }
}

function startClosingTicker() {
  stopClosingTicker();
  updateClosingDisplay();
  closingTicker = setInterval(updateClosingDisplay, 30000);
}

async function getClosingInfo(uid) {
  if (!uid) return null;
  if (closingCache.has(uid)) return closingCache.get(uid);
  try {
    const { dbMod, db } = await getFirebaseDb();
    const snap = await dbMod.get(dbMod.ref(db, '/users/' + uid + '/closingInfo'));
    const info = snap.exists() ? (snap.val() || {}) : null;
    if (info) closingCache.set(uid, info);
    else closingCache.delete(uid);
    return info;
  } catch (_) {
    return null;
  }
}

async function loadClosingInfo(uid, fallbackTxId) {
  if (!uid) {
    currentClosingInfo = null;
    stopClosingTicker();
    updateClosingDisplay();
    return;
  }
  const info = await getClosingInfo(uid);
  currentClosingInfo = info;
  if (info && typeof info === 'object') {
    currentTxId = info.txId || fallbackTxId || currentTxId;
    updateClosingDisplay();
    startClosingTicker();
  } else {
    currentClosingInfo = null;
    stopClosingTicker();
    updateClosingDisplay();
  }
}

async function loadViolationInfo(uid) {
  if (!uid) {
    violationActive = false;
    if (mViolationStatus) mViolationStatus.textContent = 'None';
    toggleViolationButtons(false);
    return;
  }
  try {
    const { dbMod, db } = await getFirebaseDb();
    const snap = await dbMod.get(dbMod.ref(db, '/users/' + uid + '/violationNotice'));
    if (snap.exists()) {
      const val = snap.val() || {};
      violationActive = val.active === true;
      const message = (val.message || '').toString();
      if (mViolationStatus) {
        const trimmed = shortText(message, 80);
        if (violationActive) {
          mViolationStatus.textContent = trimmed ? `Active — ${trimmed}` : 'Active';
        } else {
          mViolationStatus.textContent = trimmed ? `Stopped — ${trimmed}` : 'Stopped';
        }
      }
    } else {
      violationActive = false;
      if (mViolationStatus) mViolationStatus.textContent = 'None';
    }
  } catch (_) {
    violationActive = false;
    if (mViolationStatus) mViolationStatus.textContent = 'None';
  }
  toggleViolationButtons(violationActive);
}

function toggleViolationButtons(active) {
  if (sendViolationBtn) sendViolationBtn.style.display = active ? 'none' : 'inline-flex';
  if (stopViolationBtn) stopViolationBtn.style.display = active ? 'inline-flex' : 'none';
}

function openViolationModal() {
  if (!violationModal) return;
  if (violationMessageInput) {
    violationMessageInput.value = '';
    violationMessageInput.focus();
  }
  if (violationCharCount) violationCharCount.textContent = '0 / 50';
  violationModal.classList.add('show');
  violationModal.setAttribute('aria-hidden', 'false');
}

function closeViolationModal() {
  if (!violationModal) return;
  violationModal.classList.remove('show');
  violationModal.setAttribute('aria-hidden', 'true');
}

function clearSelection() {
  currentUid = null;
  currentSlotName = null;
  currentTxId = null;
  currentClosingInfo = null;
  violationActive = false;
  stopClosingTicker();
  if (mTimeLeft) {
    mTimeLeft.textContent = '—';
    mTimeLeft.classList.remove('text-danger');
  }
  if (mDeadline) mDeadline.textContent = '—';
  if (mViolationStatus) mViolationStatus.textContent = 'None';
  toggleViolationButtons(false);
  closeViolationModal();
}

window.clearMonitorSelection = clearSelection;

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
      const activeUids = new Set();
      Object.entries(occ).forEach(([k, v]) => {
        const slotKey = v?.slotName || k;
        if (slotKey) byName[slotKey] = v;
        const uid = v?.uid;
        if (uid) activeUids.add(uid.toString());
      });
      Array.from(closingCache.keys()).forEach((uidKey) => {
        if (!activeUids.has(uidKey)) {
          closingCache.delete(uidKey);
        }
      });
      document.querySelectorAll('.slot-box').forEach(box => {
        const name = box.dataset.slot;
        const o = byName[name];
        const isOcc = o && ((o.status || '').toString().toUpperCase() === 'OCCUPIED');
        box.style.background = isOcc ? '#ffdddd' : '#d5f5d5';
        box.style.borderColor = isOcc ? '#d33' : '#7ac27a';
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

  box.addEventListener('click', () => {
    if (box.isContentEditable) return;
    const slotName = box.dataset.slot;
    if (!slotName) return;
    openDetailsForName(slotName);
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
  clearSelection();
  mName.textContent = 'Loading…'; mContact.textContent=''; mType.textContent=''; mTime.textContent='';
  if (mTimeLeft) mTimeLeft.textContent = 'Loading…';
  if (mDeadline) mDeadline.textContent = '…';
  if (mViolationStatus) mViolationStatus.textContent = 'Loading…';
  overlay.style.display = 'flex'; overlay.setAttribute('aria-hidden','false');
  try {
    const { dbMod, db } = await getFirebaseDb();
    const occ = (window.__occByName || {})[slotName];
    if (!occ || !occ.uid) {
      mName.textContent='N/A';
      clearSelection();
      return;
    }
    currentUid = occ.uid.toString();
    currentSlotName = slotName;
    currentTxId = occ.txId || null;
    const snap = await dbMod.get(dbMod.ref(db, '/users/' + occ.uid));
    if (snap.exists()) {
      const u = snap.val() || {};
      mName.textContent = u.displayName || u.email || occ.uid;
      mContact.textContent = u.contactNumber || '';
      mType.textContent = u.isPWD ? 'pwd' : 'regular';
      mTime.textContent = formatDateTime(occ.timeIn || '');
    } else { mName.textContent = occ.uid; }
    closingCache.delete(currentUid);
    await loadClosingInfo(currentUid, occ.txId);
    await loadViolationInfo(currentUid);
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
  if (hdTimeLeft) hdTimeLeft.textContent = '…';
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
      hdTime.textContent = formatDateTime(occ.timeIn || '');
    } else {
      hdName.textContent = occ.uid;
      hdTime.textContent = formatDateTime(occ.timeIn || '');
    }
    const closing = await getClosingInfo(occ.uid.toString());
    if (closing && closing.deadline) {
      const formatted = formatTimeRemaining(closing.deadline);
      if (hdTimeLeft) hdTimeLeft.textContent = formatted.short;
    } else if (hdTimeLeft) {
      hdTimeLeft.textContent = '—';
    }
  } catch(_) {
    hdName.textContent = 'N/A';
    if (hdTimeLeft) hdTimeLeft.textContent = '—';
  }
}

function hideHoverCard(){
  if (!hoverCard) return;
  hoverCard.style.display = 'none';
  hoverCard.setAttribute('aria-hidden', 'true');
}

async function handleViolationSend() {
  if (!currentUid) {
    showToast('Select an occupied slot first.', 'error');
    return;
  }
  const message = (violationMessageInput?.value || '').trim();
  if (!message) {
    showToast('Please enter a violation message.', 'error');
    return;
  }
  if (message.length > 50) {
    showToast('Message must be 50 characters or less.', 'error');
    return;
  }
  if (violationSendBtn) violationSendBtn.disabled = true;
  try {
    const { dbMod, db } = await getFirebaseDb();
    const now = Date.now();
    await dbMod.set(dbMod.ref(db, '/users/' + currentUid + '/violationNotice'), {
      active: true,
      message,
      repeatSeconds: 180,
      startedAt: now,
      startedBy: adminEmail || 'admin',
      slotName: currentSlotName || '',
      txId: currentTxId || null,
    });
    violationActive = true;
    if (mViolationStatus) mViolationStatus.textContent = message ? `Active — ${message}` : 'Active';
    toggleViolationButtons(true);
    closeViolationModal();
    showToast('Violation notice sent.');
  } catch (err) {
    console.error(err);
    showToast('Failed to send violation notice.', 'error');
  } finally {
    if (violationSendBtn) violationSendBtn.disabled = false;
  }
}

async function handleViolationStop() {
  if (!currentUid) return;
  if (stopViolationBtn) stopViolationBtn.disabled = true;
  try {
    const { dbMod, db } = await getFirebaseDb();
    const now = Date.now();
    await dbMod.update(dbMod.ref(db, '/users/' + currentUid + '/violationNotice'), {
      active: false,
      stoppedAt: now,
      stoppedBy: adminEmail || 'admin',
    });
    violationActive = false;
    if (mViolationStatus) mViolationStatus.textContent = 'Stopped';
    toggleViolationButtons(false);
    showToast('Violation notice stopped.');
  } catch (err) {
    console.error(err);
    showToast('Failed to stop notice.', 'error');
  } finally {
    if (stopViolationBtn) stopViolationBtn.disabled = false;
  }
}

violationMessageInput?.addEventListener('input', () => {
  if (!violationMessageInput) return;
  if (violationMessageInput.value.length > 50) {
    violationMessageInput.value = violationMessageInput.value.substring(0, 50);
  }
  if (violationCharCount) violationCharCount.textContent = `${violationMessageInput.value.length} / 50`;
});

violationCancelBtn?.addEventListener('click', (e) => {
  e.preventDefault();
  closeViolationModal();
});

violationSendBtn?.addEventListener('click', async (e) => {
  e.preventDefault();
  await handleViolationSend();
});

violationModal?.addEventListener('click', (e) => {
  if (e.target === violationModal) {
    closeViolationModal();
  }
});

document.addEventListener('keydown', (e) => {
  if (e.key === 'Escape' && violationModal?.classList.contains('show')) {
    closeViolationModal();
  }
});

sendViolationBtn?.addEventListener('click', (e) => {
  e.preventDefault();
  if (!currentUid) {
    showToast('Select an occupied slot first.', 'error');
    return;
  }
  openViolationModal();
});

stopViolationBtn?.addEventListener('click', async (e) => {
  e.preventDefault();
  if (!currentUid) return;
  if (!confirm('Stop violation notice for this user?')) return;
  await handleViolationStop();
});


