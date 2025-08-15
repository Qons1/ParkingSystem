from django.urls import path
from . import views


urlpatterns = [
    path('', views.login_view, name='login'),
    path('monitor/', views.monitor, name='monitor'),
    path('register-slot/', views.register_slots, name='register_slots'),
    path('save-layout/', views.save_layout_labels, name='save_layout_labels'),
    path('pending/', views.pending, name='pending'),
    path('reports/', views.reports, name='reports'),
    path('database/', views.database, name='database'),
    path('verify_pwd/', views.verify_pwd, name='verify_pwd'),
    path('entries-graph/', views.entries_graph, name='entries_graph'),
    path("earnings-graph/", views.earnings_graph, name="earnings_graph"),
    path('logout/', views.logout_view, name='logout'),
    path('analytics/', views.analytics, name='analytics'),
]