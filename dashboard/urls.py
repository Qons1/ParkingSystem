from django.urls import path
from django.urls import reverse_lazy
from django.contrib.auth import views as auth_views
from . import views


urlpatterns = [
    path('', views.login_view, name='login'),
    path('monitor/', views.monitor, name='monitor'),
    path('surveillance/', views.surveillance, name='surveillance'),
    path('register-slot/', views.register_slots, name='register_slots'),
    path('save-layout/', views.save_layout_labels, name='save_layout_labels'),
    path('api/approve-pwd/', views.approve_pwd, name='approve_pwd'),
    path('api/decline-pwd/', views.decline_pwd, name='decline_pwd'),
    path('api/resolve-incident/', views.resolve_incident, name='resolve_incident'),
    path('api/delete-user/', views.delete_firebase_user, name='delete_firebase_user'),
    path('pending/', views.pending, name='pending'),
    path('reports/', views.reports, name='reports'),
    path('database/', views.database, name='database'),
    path('api/entrance-snapshot/', views.entrance_snapshot, name='entrance_snapshot'),
    path('mockpay/start', views.mockpay_start, name='mockpay_start'),
    path('mockpay/complete', views.mockpay_complete, name='mockpay_complete'),
    path('verify_pwd/', views.verify_pwd, name='verify_pwd'),
    path('entries-graph/', views.entries_graph, name='entries_graph'),
    path("earnings-graph/", views.earnings_graph, name="earnings_graph"),
    path('api/analytics/summary', views.analytics_summary, name='analytics_summary'),
    path('logout/', views.logout_view, name='logout'),
    path('analytics/', views.analytics, name='analytics'),
    # Registration and email verification
    path('register/', views.register_view, name='register'),
    path('verify-email/<uidb64>/<token>/', views.verify_email, name='verify_email'),
    # Password reset flow
    path('password-reset/', auth_views.PasswordResetView.as_view(
        template_name='password_reset.html',
        email_template_name='password_reset_email.html',
        subject_template_name='password_reset_subject.txt',
        success_url=reverse_lazy('password_reset_done')
    ), name='password_reset'),
    path('password-reset/done/', auth_views.PasswordResetDoneView.as_view(
        template_name='password_reset_done.html'
    ), name='password_reset_done'),
    path('reset/<uidb64>/<token>/', auth_views.PasswordResetConfirmView.as_view(
        template_name='password_reset_confirm.html',
        success_url=reverse_lazy('password_reset_complete')
    ), name='password_reset_confirm'),
    path('reset/done/', auth_views.PasswordResetCompleteView.as_view(
        template_name='password_reset_complete.html'
    ), name='password_reset_complete'),
]