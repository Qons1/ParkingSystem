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

# Role-based decorators

def mall_owner_required(view_func):
    return user_passes_test(lambda u: u.is_authenticated and u.is_mall_owner)(view_func)

def admin_required(view_func):
    return user_passes_test(lambda u: u.is_authenticated and (u.is_admin or u.is_mall_owner))(view_func)

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
    layout = request.session.get('layout')
    floors = request.session.get('floors')
    generated = bool(layout and floors)
    return render(request, "monitor.html", {
        "layout": layout,
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

        return redirect('monitor')

    # If clear_session is posted, clear the session and reload form
    if request.method == "POST" and request.POST.get("clear_session"):
        request.session.pop('layout', None)
        request.session.pop('floors', None)
        return redirect('register_slots')

    return render(request, "register_slots.html")

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
