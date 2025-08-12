from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth import get_user_model 
from django.contrib import messages

# Deprecated duplicate login implementation retained briefly for reference.
# This module is no longer routed; dashboard.views.login_view handles login.
User = get_user_model()

def login_view(request):
    return redirect('login')

def logout_view(request):
    logout(request)
    return redirect('login')
