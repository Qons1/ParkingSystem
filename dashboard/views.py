import csv, io, os
import matplotlib
matplotlib.use("Agg")           # ✅ add this line
import matplotlib.pyplot as plt

from django.http import HttpResponse
from django.shortcuts import render, redirect
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.decorators import login_required
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from accounts.models import CustomUser  # your custom user model
from django.utils.safestring import mark_safe
from django.contrib.auth.decorators import user_passes_test
from core.firebase import rtdb
from django.http import JsonResponse
from datetime import datetime, timedelta, timezone
import base64, requests

# Role-based decorators

def mall_owner_required(view_func):
    return user_passes_test(lambda u: u.is_authenticated and u.is_mall_owner)(view_func)

def admin_required(view_func):
    return user_passes_test(lambda u: u.is_authenticated and (u.is_admin or u.is_mall_owner))(view_func)

def admin_only_required(view_func):
    return user_passes_test(lambda u: u.is_authenticated and u.is_admin)(view_func)

report_entries = []

# ───────────────────────────────────────────────────────────────
#  Dynamic graph view
# ───────────────────────────────────────────────────────────────
def entries_graph(request):
    """
    Reads data/parking_entries.csv and renders a bar chart as PNG.
    URL:  /entries-graph/
    """
    csv_path = os.path.join(
        os.path.dirname(os.path.dirname(__file__)),  # project root (where manage.py lives)
        "data",
        "parking_entries.csv"
    )

    if not os.path.exists(csv_path):
        return HttpResponse("CSV file not found.", content_type="text/plain")

    days, entries = [], []
    with open(csv_path, newline="") as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            days.append(row["Day"])
            entries.append(int(row["Entries"]))

    # Build the graph
    fig, ax = plt.subplots(figsize=(10, 6))  # or even (12, 6)          # ← size so it’s not tiny
    ax.bar(days, entries, color="#e8b931")
    ax.set_title("Weekly Parking Entries")
    ax.set_ylabel("Entries")
    ax.set_xlabel("Day")

    # Stream image back to browser
    buffer = io.BytesIO()
    fig.tight_layout()
    fig.savefig(buffer, format="png")
    plt.close(fig)
    buffer.seek(0)
    return HttpResponse(buffer.getvalue(), content_type="image/png")

def earnings_graph(request):
    """
    Reads data/monthly_earnings.csv and renders a bar chart.
    URL:  /earnings-graph/
    """
    csv_path = os.path.join(
        os.path.dirname(os.path.dirname(__file__)),
        "data",
        "monthly_earnings.csv"
    )

    if not os.path.exists(csv_path):
        return HttpResponse("CSV file not found.", content_type="text/plain")

    months, earnings = [], []
    with open(csv_path) as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            months.append(row["Month"])
            earnings.append(int(row["Earnings"]))

    fig, ax = plt.subplots(figsize=(10, 6))  # or even (12, 6)
    ax.plot(months, earnings, marker='o', color="#333")
    ax.set_title("Monthly Earnings")
    ax.set_ylabel("Earnings (₱)")
    ax.set_xlabel("Month")
    ax.grid(True)

    buffer = io.BytesIO()
    fig.tight_layout()
    fig.savefig(buffer, format="png")
    plt.close(fig)
    buffer.seek(0)
    return HttpResponse(buffer.getvalue(), content_type="image/png")


# ───────────────────────────────────────────────────────────────
#  Basic demo login / pages (unchanged except minor comment tidy)
# ───────────────────────────────────────────────────────────────
user_entries = []

@csrf_exempt   # demo only
def login_view(request):
    if request.method == "POST":
        email = request.POST.get("email")
        password = request.POST.get("password")

        try:
            user_obj = CustomUser.objects.get(email=email)
            user = authenticate(request, username=user_obj.username, password=password)
        except CustomUser.DoesNotExist:
            user = None

        if user is not None:
            # Only allow admins or mall owners to access the dashboard
            if user.is_admin or user.is_mall_owner:
                login(request, user)
                return redirect("monitor")
            messages.error(request, "This web dashboard is only for admins and mall owners. Please use the mobile app for user access.")
            return redirect("login")
        else:
            messages.error(request, "Invalid credentials")
            return redirect("login")

    return render(request, "login.html")

def logout_view(request):
    logout(request)
    return redirect('login')  # change this to your login page's name
# admin views
@login_required
@admin_required
def monitor(request):
    # Try to read from Firebase layout first so saved names persist
    floors = None
    layout_for_template = {}
    try:
        db = rtdb()
        fb_layout = db.reference('/configurations/layout').get() or {}
        floors = fb_layout.get('floors')
        sbf = fb_layout.get('slotsByFloor', {})
        # Handle dict or list
        if isinstance(sbf, dict):
            items_iter = sbf.items()
        else:
            items_iter = enumerate(sbf)
        for floor_key, types in items_iter:
            if types is None:
                continue
            floor_num = int(floor_key)
            layout_for_template[floor_num] = {"Car": [], "Motorcycle": [], "PWD": []}
            for tkey in ("Car", "Motorcycle", "PWD"):
                slots_list = types.get(tkey, []) if isinstance(types, dict) else []
                if not isinstance(slots_list, list):
                    continue
                for item in slots_list:
                    if isinstance(item, dict):
                        sid = item.get('id') or ''
                        name = item.get('name') or sid
                    else:
                        sid = str(item)
                        name = sid
                    layout_for_template[floor_num][tkey].append((name, sid))
    except Exception:
        layout_for_template = {}

    if not layout_for_template:
        # Fallback to session-generated layout (use id for both name and id)
        session_layout = request.session.get('layout') or {}
        floors = request.session.get('floors')
        for floor, types in session_layout.items():
            layout_for_template[floor] = {"Car": [], "Motorcycle": [], "PWD": []}
            for tkey in ("Car", "Motorcycle", "PWD"):
                for slot_id, _ in types.get(tkey, []):
                    layout_for_template[floor][tkey].append((slot_id, slot_id))

    generated = bool(layout_for_template and floors)
    return render(request, "monitor.html", {
        "layout": layout_for_template,
        "floors": floors,
        "generated": generated,
    })

@mall_owner_required
@csrf_exempt
def register_slots(request):
    if request.method == "POST" and not request.POST.get("clear_session"):
        # Get form data
        floors = int(request.POST.get("floors", 1))
        car_slots = int(request.POST.get("car_slots", 0))
        motor_slots = int(request.POST.get("motor_slots", 0))
        pwd_slots = int(request.POST.get("pwd_slots", 0))

        # Generate layout and store in session
        layout = {}
        for floor in range(1, floors + 1):
            layout[floor] = {
                "Car": [(f"C{floor}-{i+1}", "") for i in range(car_slots)],
                "Motorcycle": [(f"M{floor}-{i+1}", "") for i in range(motor_slots)],
                "PWD": [(f"P{floor}-{i+1}", "") for i in range(pwd_slots)],
            }
        request.session['layout'] = layout
        request.session['floors'] = floors

        # Push full layout to Firebase (Car, Motorcycle, PWD) with id+name per slot.
        try:
            db = rtdb()
            ref = db.reference("/configurations/layout")
            # Build a simplified layout: floors and slots per type
            mobile_layout = {"floors": floors, "slotsByFloor": {}}
            for floor, types in layout.items():
                car_slots = [{"id": slot, "name": slot} for slot, _ in types.get("Car", [])]
                motor_slots = [{"id": slot, "name": slot} for slot, _ in types.get("Motorcycle", [])]
                pwd_slots_list = [{"id": slot, "name": slot} for slot, _ in types.get("PWD", [])]
                mobile_layout["slotsByFloor"][str(floor)] = {
                    "Car": car_slots,
                    "Motorcycle": motor_slots,
                    "PWD": pwd_slots_list,
                }
            # Overwrite layout
            ref.set(mobile_layout)
            # Clear any existing occupancy since slot mapping changed
            try:
                ref.child('occupied').set({})
            except Exception:
                # ignore if occupied path does not exist yet
                pass
        except Exception:
            # Silent fail in dev; we will configure env later
            pass

        return redirect('monitor')

    # If clear_session is posted, clear the session and reload form
    if request.method == "POST" and request.POST.get("clear_session"):
        request.session.pop('layout', None)
        request.session.pop('floors', None)
        return redirect('register_slots')

    return render(request, "register_slots.html")

@csrf_exempt
@mall_owner_required
def save_layout_labels(request):
    if request.method != 'POST':
        return JsonResponse({"error": "POST required"}, status=405)
    try:
        import json
        payload = json.loads(request.body.decode('utf-8'))
        # Expected payload: { labels: { "C1-1": "Custom A1", ... } }
        labels = payload.get('labels', {})
        if not isinstance(labels, dict):
            return JsonResponse({"error": "Invalid labels"}, status=400)
        db = rtdb()
        layout_ref = db.reference('/configurations/layout')
        layout = layout_ref.get() or {}
        slots_by_floor = (layout or {}).get('slotsByFloor', {})
        # Normalize floor iteration to handle dict or list structures
        def floor_iter(sbf):
            if isinstance(sbf, dict):
                for k, v in sbf.items():
                    yield str(k), v
            elif isinstance(sbf, list):
                for i, v in enumerate(sbf):
                    if v is not None:
                        yield str(i), v
        changed = False
        new_sbf = {}
        for floor_key, types in floor_iter(slots_by_floor):
            # Ensure types is a dict of categories
            if not isinstance(types, dict):
                continue
            for tkey in ('Car', 'Motorcycle', 'PWD'):
                slots_list = types.get(tkey, [])
                if not isinstance(slots_list, list):
                    continue
                new_list = []
                for item in slots_list:
                    if isinstance(item, dict):
                        sid = item.get('id')
                        if sid and sid in labels:
                            item['name'] = labels[sid]
                            changed = True
                        # ensure both id and name exist
                        if 'id' in item and 'name' not in item:
                            item['name'] = item['id']
                        new_list.append(item)
                    else:
                        # legacy string; convert to object with name override if provided
                        sid = str(item)
                        name = labels.get(sid, sid)
                        new_list.append({'id': sid, 'name': name})
                        if sid in labels:
                            changed = True
                types[tkey] = new_list
            new_sbf[floor_key] = types
        if changed:
            layout['slotsByFloor'] = new_sbf
            layout_ref.set(layout)
        return JsonResponse({"ok": True})
    except Exception as e:
        # Return 200 with ok=false so frontend can show a friendly toast
        return JsonResponse({"ok": False, "error": str(e)})

# ───────────────────────────────────────────────────────────────
#  Admin SDK endpoints: PWD approvals (admin or mall owner) and incidents (admin only)
# ───────────────────────────────────────────────────────────────

@csrf_exempt
@admin_required
def approve_pwd(request):
    if request.method != 'POST':
        return JsonResponse({"error": "POST required"}, status=405)
    try:
        import json
        payload = json.loads(request.body or '{}')
        uid = payload.get('uid')
        if not uid:
            return JsonResponse({"error": "uid required"}, status=400)
        db = rtdb()
        db.reference(f"/pwdRequests/{uid}").update({"status": "approved"})
        db.reference(f"/users/{uid}").update({"pwdStatus": "approved", "isPWD": True})
        return JsonResponse({"ok": True})
    except Exception as e:
        return JsonResponse({"ok": False, "error": str(e)})

@csrf_exempt
@admin_required
def decline_pwd(request):
    if request.method != 'POST':
        return JsonResponse({"error": "POST required"}, status=405)
    try:
        import json
        payload = json.loads(request.body or '{}')
        uid = payload.get('uid')
        if not uid:
            return JsonResponse({"error": "uid required"}, status=400)
        db = rtdb()
        db.reference(f"/pwdRequests/{uid}").update({"status": "rejected"})
        db.reference(f"/users/{uid}").update({"pwdStatus": "rejected"})
        return JsonResponse({"ok": True})
    except Exception as e:
        return JsonResponse({"ok": False, "error": str(e)})

@csrf_exempt
@admin_required
def resolve_incident(request):
    if request.method != 'POST':
        return JsonResponse({"error": "POST required"}, status=405)
    try:
        import json, time
        payload = json.loads(request.body or '{}')
        incident_id = payload.get('incidentId')
        if not incident_id:
            return JsonResponse({"error": "incidentId required"}, status=400)
        db = rtdb()
        finalize = bool(payload.get('finalize'))
        now_ms = int(time.time()*1000)
        if finalize:
            db.reference(f"/incidents/{incident_id}").update({
                "status": "RESOLVED",
                "resolvedAt": now_ms
            })
        else:
            # Ask user to confirm; auto-resolve after 1 hour
            db.reference(f"/incidents/{incident_id}").update({
                "status": "PENDING_USER_CONFIRM",
                "confirmRequestedAt": now_ms,
                "confirmDeadline": now_ms + 3600*1000
            })
        return JsonResponse({"ok": True})
    except Exception as e:
        return JsonResponse({"ok": False, "error": str(e)})

@mall_owner_required
def analytics(request):
    """Mall owner analytics: show registered users count and weekly entries.

    - Registered users: count of keys under /users
    - Weekly entries: number of transactions with timeIn in current ISO week (Mon-Sun)
    """
    registered_users_count = 0
    weekly_entries_count = 0
    try:
        db = rtdb()
        # Registered users count
        users_snapshot = db.reference('/users').get() or {}
        if isinstance(users_snapshot, dict):
            registered_users_count = len(users_snapshot.keys())
        elif isinstance(users_snapshot, list):
            registered_users_count = len([x for x in users_snapshot if x is not None])

        # Weekly entries from /transactions by timeIn
        now = datetime.now(timezone.utc)
        # Start of current week (Monday 00:00) in UTC
        start_of_week = (now - timedelta(days=now.weekday())).replace(hour=0, minute=0, second=0, microsecond=0)
        start_ms = int(start_of_week.timestamp() * 1000)
        tx_snapshot = db.reference('/transactions').get() or {}
        if isinstance(tx_snapshot, dict):
            for tx in tx_snapshot.values():
                if not isinstance(tx, dict):
                    continue
                t_in = tx.get('timeIn')
                if isinstance(t_in, (int, float)) and t_in >= start_ms:
                    weekly_entries_count += 1
        elif isinstance(tx_snapshot, list):
            for tx in tx_snapshot:
                if not isinstance(tx, dict):
                    continue
                t_in = tx.get('timeIn')
                if isinstance(t_in, (int, float)) and t_in >= start_ms:
                    weekly_entries_count += 1
    except Exception:
        # In dev, fail silently and show zeros
        pass

    return render(request, "analytics.html", {
        "registered_users_count": registered_users_count,
        "weekly_entries_count": weekly_entries_count,
    })

# ───────────────────────────────────────────────────────────────
#  Live analytics JSON for charts (mall owner/admin)
# ───────────────────────────────────────────────────────────────
@login_required
@admin_required
def analytics_summary(request):
    try:
        db = rtdb()

        # Occupancy
        occ = db.reference('/configurations/layout/occupied').get() or {}
        car_occ = 0; motor_occ = 0; pwd_occ = 0
        if isinstance(occ, dict):
            for v in occ.values():
                if not isinstance(v, dict):
                    continue
                if str(v.get('status','')).upper() != 'OCCUPIED':
                    continue
                vt = str(v.get('vehicleType','')).upper()
                if vt == 'MOTORCYCLE': motor_occ += 1
                elif vt == 'PWD': pwd_occ += 1
                else: car_occ += 1

        # Transactions snapshot
        txs = db.reference('/transactions').get() or {}
        if not isinstance(txs, (dict, list)):
            txs = {}

        now = datetime.now(timezone.utc)
        start_today = now.replace(hour=0, minute=0, second=0, microsecond=0)
        start_yesterday = (start_today - timedelta(days=1))
        start_week = (now - timedelta(days=now.weekday())).replace(hour=0, minute=0, second=0, microsecond=0)

        def to_dt(val):
            # timeIn/Out can be ISO string; sometimes ms epoch in older data
            try:
                if isinstance(val, (int, float)):
                    return datetime.fromtimestamp(float(val)/1000.0, tz=timezone.utc)
                return datetime.fromisoformat(str(val).replace('Z','+00:00'))
            except Exception:
                return None

        today_earn = 0.0; week_earn = 0.0
        today_entries = 0; yesterday_entries = 0
        completed_today = 0; started_today = 0
        stay_mins_sum = 0.0; stay_mins_n = 0
        hist = [0]*24

        items = txs.items() if isinstance(txs, dict) else enumerate(txs)
        for _, tx in items:
            if not isinstance(tx, dict):
                continue
            t_in = to_dt(tx.get('timeIn'))
            t_out = to_dt(tx.get('timeOut'))
            status = str(tx.get('status','')).upper()
            amt_paid = float(tx.get('amountPaid') or 0)

            if t_in:
                if t_in >= start_today:
                    today_entries += 1
                    hour = (t_in.astimezone(timezone.utc).hour)
                    if 0 <= hour < 24:
                        hist[hour] += 1
                    started_today += 1
                elif start_yesterday <= t_in < start_today:
                    yesterday_entries += 1

            if t_out:
                if t_out >= start_today:
                    today_earn += amt_paid
                    completed_today += 1
                if t_out >= start_week:
                    week_earn += amt_paid

            if t_in and t_out:
                stay = (t_out - t_in).total_seconds()/60.0
                if stay > 0:
                    stay_mins_sum += stay
                    stay_mins_n += 1

        avg_stay = round(stay_mins_sum/stay_mins_n, 1) if stay_mins_n else 0.0
        conversion = round((completed_today/max(1, started_today))*100.0, 1)

        return JsonResponse({
            'totals': {
                'todayEarnings': round(today_earn,2),
                'weekEarnings': round(week_earn,2),
                'todayEntries': today_entries,
                'yesterdayEntries': yesterday_entries,
                'conversionTodayPct': conversion,
                'avgStayMinsWeek': avg_stay,
            },
            'occupancy': {
                'car': car_occ,
                'motorcycle': motor_occ,
                'pwd': pwd_occ,
            },
            'histogramToday': hist,
        })
    except Exception as e:
        return JsonResponse({'ok': False, 'error': str(e)}, status=500)

    
@login_required
@admin_required
def pending(request):
    return render(request, 'pending.html')

@login_required
@admin_required
def reports(request):
    return render(request, 'reports.html', {"reports": report_entries})

@login_required
@admin_required
def database(request):
    users = CustomUser.objects.filter(is_user=True)
    return render(request, 'database.html', {"users": users})
@login_required
@admin_required
def verify_pwd(request):
     return render(request, "verify_pwd.html")

# ───────────────────────────────────────────────────────────────
#  Entrance snapshot: fetch from OV2640, upload to Cloudinary, OCR, write to RTDB
# ───────────────────────────────────────────────────────────────
@csrf_exempt
def entrance_snapshot(request):
    """POST { uid, txId, cameraUrl } → captures JPEG, uploads to Cloudinary (dy5kbbskp),
    OCRs text (optional via OCR.space if OCR_API_KEY set), writes plate to /transactions/<txId>/plateNumber and /users/<uid>/lastPlate.
    Returns { ok, url, plate }.
    """
    if request.method != 'POST':
        return JsonResponse({"error": "POST required"}, status=405)
    try:
        import json
        payload = json.loads(request.body or '{}')
        uid = (payload.get('uid') or '').strip()
        tx_id = (payload.get('txId') or '').strip()
        cam_url = (payload.get('cameraUrl') or request.GET.get('cameraUrl') or request.POST.get('cameraUrl') or '').strip()
        if not (uid and tx_id and cam_url):
            return JsonResponse({"error": "uid, txId, cameraUrl required"}, status=400)

        # 1) Capture JPEG from OV2640 /capture
        cap_url = cam_url.rstrip('/') + '/capture'
        cap_res = requests.get(cap_url, timeout=30)
        if cap_res.status_code != 200 or not cap_res.content:
            return JsonResponse({"ok": False, "error": "capture failed"})

        # 2) Upload to Cloudinary (unsigned)
        cloud = 'dy5kbbskp'
        upload_preset = os.environ.get('CLOUDINARY_UPLOAD_PRESET', 'unsigned')
        cld_url = f'https://api.cloudinary.com/v1_1/{cloud}/image/upload'
        files = { 'file': ('plate.jpg', cap_res.content, 'image/jpeg') }
        data = { 'upload_preset': upload_preset, 'folder': 'cygo/entry' }
        cld_res = requests.post(cld_url, files=files, data=data, timeout=30)
        cld_json = {}
        try: cld_json = cld_res.json()
        except Exception: cld_json = {}
        if cld_res.status_code >= 300 or 'secure_url' not in cld_json:
            return JsonResponse({"ok": False, "error": "cloudinary upload failed", "status": cld_res.status_code})
        secure_url = cld_json['secure_url']

        # 3) OCR (optional via OCR.space) – with fallback and plate pattern extraction
        def extract_plate(raw: str) -> str:
            import re
            s = (raw or '').upper().replace('\n', ' ').replace('\r',' ')
            s = ' '.join(s.split())
            # common confusions
            s = s.replace('0', 'O') if s.count('0') <= 3 else s
            s = s.replace('1', 'I') if s.count('1') <= 3 else s
            # PH-like: ABC 123 or ABC 1234; also allow 2 letters + up to 4 digits
            m = re.search(r'([A-Z]{2,4})\s*[- ]?\s*(\d{2,4})', s)
            return (m.group(1) + ' ' + m.group(2)) if m else s if s else ''

        plate_text = ''
        ocr_key = os.environ.get('OCR_API_KEY')
        if ocr_key:
            try:
                ocr_api = 'https://api.ocr.space/parse/image'
                # First try Engine 2
                resp = requests.post(
                    ocr_api,
                    data={'apikey': ocr_key, 'language': 'eng', 'scale': 'true', 'OCREngine': 2, 'url': secure_url},
                    timeout=25
                )
                js = resp.json()
                if not js.get('IsErroredOnProcessing'):
                    pars = js.get('ParsedResults') or []
                    raw = (pars[0].get('ParsedText') or '') if pars else ''
                    plate_text = extract_plate(raw)
                # Fallback to Engine 1 if empty
                if not plate_text:
                    resp1 = requests.post(
                        ocr_api,
                        data={'apikey': ocr_key, 'language': 'eng', 'scale': 'true', 'OCREngine': 1, 'url': secure_url},
                        timeout=25
                    )
                    js1 = resp1.json()
                    if not js1.get('IsErroredOnProcessing'):
                        pars1 = js1.get('ParsedResults') or []
                        raw1 = (pars1[0].get('ParsedText') or '') if pars1 else ''
                        plate_text = extract_plate(raw1)
            except Exception:
                pass

        # 4) Write to RTDB (only per-transaction fields; no writes to users/lastPlate)
        db = rtdb()
        try:
            if plate_text:
                db.reference(f'/transactions/{tx_id}').update({'plateNumber': plate_text, 'plateImageUrl': secure_url})
            else:
                db.reference(f'/transactions/{tx_id}').update({'plateImageUrl': secure_url})
        except Exception as e:
            return JsonResponse({'ok': False, 'error': f'RTDB write failed: {e}', 'url': secure_url})

        # Read back current tx snapshot for debugging visibility
        try:
            tx_snapshot = db.reference(f'/transactions/{tx_id}').get() or {}
        except Exception:
            tx_snapshot = {}
        return JsonResponse({ 'ok': True, 'url': secure_url, 'plate': plate_text, 'txId': tx_id, 'tx': tx_snapshot })
    except Exception as e:
        return JsonResponse({ 'ok': False, 'error': str(e) })

# ───────────────────────────────────────────────────────────────
#  Surveillance (admin or mall owner)
# ───────────────────────────────────────────────────────────────
@login_required
@admin_required
def surveillance(request):
    """Simple page that embeds an ESP32-CAM MJPEG stream.

    The template will read a default URL from context and allow override via localStorage.
    """
    # Sensible default; template can override from localStorage UI
    default_stream_url = request.GET.get('url') or "http://192.168.1.150:81/stream"
    return render(request, "surveillance.html", {"default_stream_url": default_stream_url})

# ───────────────────────────────────────────────────────────────
#  Mock payment flow (for testing mobile app without real GCash)
# ───────────────────────────────────────────────────────────────
@csrf_exempt
def mockpay_start(request):
    """GET /mockpay/start?txId=&amount=
    Render a mock checkout UI styled to resemble GCash.
    """
    tx_id = request.GET.get('txId') or ''
    amount = request.GET.get('amount') or '0'
    try:
        amt = float(amount)
        amount_disp = f"₱{amt:,.2f}"
    except Exception:
        amount_disp = f"₱{amount}"
    merchant_name = "CYGO Parking"
    account_label = "GCash"
    html = f"""
    <!doctype html>
    <html lang='en'>
    <head>
      <meta charset='utf-8'/>
      <meta name='viewport' content='width=device-width, initial-scale=1'/>
      <title>GCash - Pay</title>
      <style>
        :root {{
          --gcash-blue: #007BFF;
          --gcash-blue-dark: #0052CC;
          --bg: #f2f5f8;
          --text: #1c1c1c;
        }}
        * {{ box-sizing: border-box; }}
        body {{ margin: 0; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, 'Helvetica Neue', Arial, 'Noto Sans', sans-serif; background: var(--bg); color: var(--text); }}
        .appbar {{ background: linear-gradient(135deg, var(--gcash-blue), var(--gcash-blue-dark)); color: #fff; padding: 14px 16px; display: flex; align-items: center; gap: 10px; }}
        .logo {{ width: 28px; height: 28px; border-radius: 8px; background: rgba(255,255,255,.2); display:flex; align-items:center; justify-content:center; font-weight:700; }}
        .title {{ font-weight: 700; font-size: 16px; }}
        .container {{ max-width: 440px; margin: 18px auto; padding: 0 14px; }}
        .card {{ background: #fff; border-radius: 14px; box-shadow: 0 10px 30px rgba(0,0,0,.06); padding: 16px; margin-bottom: 14px; }}
        .row {{ display: flex; justify-content: space-between; align-items: center; padding: 10px 0; border-bottom: 1px solid #f0f0f0; }}
        .row:last-child {{ border-bottom: none; }}
        .label {{ color: #666; font-size: 14px; }}
        .value {{ font-weight: 600; }}
        .amount {{ font-size: 28px; font-weight: 800; letter-spacing: .3px; }}
        .btn {{ width: 100%; padding: 14px; background: var(--gcash-blue); border: none; color: #fff; font-weight: 700; border-radius: 10px; cursor: pointer; box-shadow: 0 8px 18px rgba(0,123,255,.25); }}
        .btn:disabled {{ opacity: .7; cursor: not-allowed; }}
        .muted {{ color: #888; font-size: 12px; text-align: center; margin-top: 10px; }}
      </style>
    </head>
    <body>
      <div class='appbar'>
        <div class='logo'>G</div>
        <div class='title'>GCash</div>
      </div>
      <div class='container'>
        <div class='card'>
          <div class='row'><div class='label'>Pay to</div><div class='value'>{merchant_name}</div></div>
          <div class='row'><div class='label'>Method</div><div class='value'>{account_label}</div></div>
          <div class='row'><div class='label'>Reference (TxID)</div><div class='value' style='overflow:hidden;text-overflow:ellipsis;max-width:60%; text-align:right;'>{tx_id}</div></div>
        </div>

        <div class='card'>
          <div class='row'><div class='label'>Amount Due</div><div class='amount'>{amount_disp}</div></div>
          <div class='row'><div class='label'>Convenience Fee</div><div class='value'>₱0.00</div></div>
          <div class='row'><div class='label'>Total</div><div class='amount'>{amount_disp}</div></div>
        </div>

        <form class='card' action='/mockpay/complete' method='POST' onsubmit="document.getElementById('paybtn').disabled=true; document.getElementById('paybtn').innerText='Processing…';">
          <input type='hidden' name='txId' value='{tx_id}'/>
          <input type='hidden' name='amount' value='{amount}'/>
          <button id='paybtn' type='submit' class='btn'>Pay Now</button>
          <div class='muted'>This is a mock checkout for testing only.</div>
        </form>
      </div>
    </body>
    </html>
    """
    return HttpResponse(html)

@csrf_exempt
def mockpay_complete(request):
    """POST from mockpay_start form; marks payment as completed in RTDB and renders a success page."""
    try:
        tx_id = request.POST.get('txId') or ''
        amount = request.POST.get('amount') or '0'
        db = rtdb()
        if tx_id:
            db.reference(f'/payments/{tx_id}').set({
                'txId': tx_id,
                'amount': float(amount or 0),
                'method': 'MOCKPAY',
                'referenceNumber': 'MOCK-' + tx_id[:6],
                'status': 'PAID',
                'createdAt': datetime.utcnow().isoformat() + 'Z'
            })
            db.reference(f'/transactions/{tx_id}').update({
                'status': 'COMPLETED',
                'amountPaid': float(amount or 0),
                'timeOut': int(datetime.utcnow().timestamp()*1000)
            })
        html = """
        <!doctype html>
        <html lang='en'>
        <head>
          <meta charset='utf-8'/>
          <meta name='viewport' content='width=device-width, initial-scale=1'/>
          <title>GCash - Success</title>
          <style>
            body { margin:0; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Arial, 'Noto Sans', sans-serif; background:#f2f5f8; color:#1c1c1c; }
            .appbar { background: linear-gradient(135deg, #007BFF, #0052CC); color:#fff; padding:14px 16px; font-weight:700; }
            .container { max-width: 440px; margin: 22px auto; padding: 0 14px; }
            .card { background:#fff; border-radius:14px; box-shadow:0 10px 30px rgba(0,0,0,.06); padding:22px; text-align:center; }
            .check { font-size:44px; color:#0aaf5c; }
            .btn { margin-top:14px; display:inline-block; padding:10px 16px; background:#007BFF; color:#fff; border-radius:10px; text-decoration:none; }
          </style>
        </head>
        <body>
          <div class='appbar'>GCash</div>
          <div class='container'>
            <div class='card'>
              <div class='check'>✔</div>
              <h3 style='margin:10px 0 8px;'>Payment Successful</h3>
              <div style='color:#666;'>You can close this page and return to the app.</div>
            </div>
          </div>
        </body>
        </html>
        """
        return HttpResponse(html)
    except Exception as e:
        return HttpResponse(f"<html><body>Failed: {e}</body></html>", status=500)