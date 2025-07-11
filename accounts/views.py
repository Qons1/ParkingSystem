from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth import get_user_model 
from django.contrib import messages

User = get_user_model()  # now points to CustomUser

def login_view(request):
    if request.method == "POST":
        email    = request.POST.get("email")
        password = request.POST.get("password")
        user = authenticate(request, username=email, password=password)
        if user:
            login(request, user)
            return redirect("monitor" if user.is_admin else "submit_report")
        messages.error(request, "Invalid credentials.")

    return render(request, "login.html")


def register_view(request):
    if request.method == "POST":
        name     = request.POST.get("name")
        email    = request.POST.get("email")
        password = request.POST.get("password")

        # check if already exists
        if User.objects.filter(username=email).exists():
            messages.error(request, "Email already registered.")
            return redirect("register")

        user = User.objects.create_user(
            username=email,
            email=email,
            password=password,
            first_name=name,
            is_admin=False,   # default regular user
            is_user=True
        )
        messages.success(request, "Account created — please log in.")
        return redirect("login")

    return render(request, "register.html")

def logout_view(request):
    logout(request)
    return redirect("login")
