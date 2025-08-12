from django.urls import path
from . import views
from dashboard.views import logout_view


urlpatterns = [
    path('', views.login_view, name='login'),
    path('monitor/', views.monitor, name='monitor'),
    path('register-slot/', views.register_slots, name='register_slots'),
    path('pending/', views.pending, name='pending'),
    path('reports/', views.reports, name='reports'),
    path('database/', views.database, name='database'),
    path('verify_pwd/', views.verify_pwd, name='verify_pwd'),
    path('entries-graph/', views.entries_graph, name='entries_graph'),
    path("earnings-graph/", views.earnings_graph, name="earnings_graph"),
    path('logout/', logout_view, name='logout'),
    path('analytics/', views.analytics, name='analytics'),
]