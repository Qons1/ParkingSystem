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
@admin_only_required
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
        db.reference(f"/incidents/{incident_id}").update({
            "status": "RESOLVED",
            "resolvedAt": int(time.time()*1000)
        })
        return JsonResponse({"ok": True})
    except Exception as e:
        return JsonResponse({"ok": False, "error": str(e)})

@mall_owner_required
def analytics(request):
    # Your analytics logic here
    return render(request, "analytics.html")

    
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
