import csv, io, os
import matplotlib
matplotlib.use("Agg")           # ✅ add this line
import matplotlib.pyplot as plt

from django.http import HttpResponse
from django.shortcuts import render, redirect
from django.views.decorators.csrf import csrf_exempt

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
        role  = request.POST.get("role")

        user_entries.append({
            "slot": "–",
            "plate": "N/A",
            "name":  email,
            "contact": "N/A",
            "type": "Unknown",
        })

        return redirect("monitor" if role == "admin" else "submit_report")

    return render(request, "login.html")

def monitor(request):
    return render(request, "monitor.html", {
        "users": user_entries  # ← passed to show registered users count
    })

def register_slots(request): return render(request, "register_slots.html")
def pending(request):        return render(request, "pending.html")
def reports(request):
    return render(request, "reports.html", {"reports": report_entries})

def database(request):       return render(request, "database.html", {"users": user_entries})
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
def parking_details(request):return render(request, "parking_details.html")
def verify_pwd(request):     return render(request, "verify_pwd.html")
