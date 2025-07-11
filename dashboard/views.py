import csv, io, os
import matplotlib
matplotlib.use("Agg")           # ✅ add this line
import matplotlib.pyplot as plt
import random

from django.http import HttpResponse
from django.shortcuts import render, redirect
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.decorators import login_required
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from accounts.models import CustomUser  # your custom user model
from django.utils.safestring import mark_safe

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
            login(request, user)
            return redirect("monitor" if user.is_admin else "submit_report")
        else:
            messages.error(request, "Invalid credentials")
            return redirect("login")

    return render(request, "login.html")

def logout_view(request):
    logout(request)
    return redirect('login')  # change this to your login page's name
# admin views
@login_required
def monitor(request):
    if not request.user.is_admin:
        return redirect('submit_report')  # or any user-only page
    return render(request, 'monitor.html', {"users": user_entries})

@login_required
def register_slots(request):
    # block non‑admins
    if not request.user.is_admin:
        return redirect("submit_report")

    # ── 1. Handle explicit reset from “Back to Form” button ──────────
    if request.method == "POST" and request.POST.get("clear_session"):
        request.session.pop("slot_config", None)
        return render(request, "register_slots.html", {"generated": False})

    # Fake user info (demo only)
    fake_users = [
        "John Doe<br>Plate ABC‑123<br>Contact 0917‑123‑4567",
        "Jane Smith<br>Plate XYZ‑987<br>Contact 0998‑765‑4321",
        "Carlos PWD<br>Plate PWD‑001<br>Contact 0908‑555‑0000",
        "No One<br>Unassigned<br>—",
    ]

    # ── 2. Handle normal form submission ───────────────
    if request.method == "POST":
        floors      = int(request.POST.get("floors"))
        car_slots   = int(request.POST.get("car_slots"))
        motor_slots = int(request.POST.get("motor_slots"))
        pwd_slots   = int(request.POST.get("pwd_slots"))

        request.session["slot_config"] = {
            "floors": floors,
            "car":   car_slots,
            "motor": motor_slots,
            "pwd":   pwd_slots,
        }

    # ── 3. If nothing in POST, see if we have session data ───────────
    config = request.session.get("slot_config")
    if not config:
        # First visit — just show blank form
        return render(request, "register_slots.html", {"generated": False})

    floors      = config["floors"]
    car_slots   = config["car"]
    motor_slots = config["motor"]
    pwd_slots   = config["pwd"]

    # Build layout dict
    layout = {}
    for f in range(1, floors + 1):
        prefix = chr(64 + f)           # A, B, C …
        layout[f] = {
            "Car":   [(f"{prefix}C{i}",  random.choice(fake_users)) for i in range(1, car_slots   + 1)],
            "Motor": [(f"{prefix}M{i}",  random.choice(fake_users)) for i in range(1, motor_slots + 1)],
            "PWD":   [(f"{prefix}P{i}",  random.choice(fake_users)) for i in range(1, pwd_slots   + 1)],
        }

    return render(request, "register_slots.html", {
        "generated": True,
        "floors": floors,
        "layout": layout,
    })

@login_required
def pending(request):
    if not request.user.is_admin:
        return redirect('submit_report')
    return render(request, 'pending.html')

@login_required
def reports(request):
    if not request.user.is_admin:
        return redirect('submit_report')
    return render(request, 'reports.html', {"reports": report_entries})

@login_required
def database(request):
    if not request.user.is_admin:
        return redirect('submit_report')

    users = CustomUser.objects.filter(is_user=True)  # Only show normal users
    return render(request, 'database.html', {"users": users})
#user views
@login_required
def submit_report(request):
    if request.method == 'POST':
        subject = request.POST.get("subject")
        description = request.POST.get("description")
        # simulate current user as the last logged in user
        email = user_entries[-1]["name"] if user_entries else "Unknown"

        report_entries.append({
            "email": email,
            "subject": subject,
            "description": description,
        })

        return redirect("submit_report")  # or redirect somewhere else if needed

    return render(request, 'submit_report.html')

@login_required
def parking_details(request):
    return render(request, "parking_details.html")

@login_required
def verify_pwd(request):
     return render(request, "verify_pwd.html")
