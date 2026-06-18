from django.urls import path
from . import views

urlpatterns = [
    path('', views.movie_list, name='movie_list'),
    path('<int:movie_id>/', views.movie_detail, name='movie_detail'),
    path('<int:movie_id>/theaters/', views.theater_list, name='theater_list'),
    path('theater/<int:theater_id>/seats/book/', views.book_seats, name='book_seats'),
    path('booking/<int:booking_id>/confirmation/', views.booking_confirmation, name='booking_confirmation'),

   
    path('lock-seat/<int:seat_id>/', views.lock_seat, name='lock_seat'),
    path('unlock-seat/<int:seat_id>/', views.unlock_seat, name='unlock_seat'),
    path('payment/', views.create_payment, name='create_payment'),
    path(
    'payment-success/',
    views.payment_success,
    name='payment_success'
    
),
path(
    'payment-failed/',
    views.payment_failed,
    name='payment_failed'
),
path(
    'payment-cancelled/',
    views.payment_cancelled,
    name='payment_cancelled'
),
path(
    'razorpay-webhook/',
    views.razorpay_webhook,
    name='razorpay_webhook'
),
path('admin-dashboard/', views.admin_dashboard, name='admin_dashboard'),
path(
    'cancel-booking/<int:booking_id>/',
    views.cancel_booking,
    name='cancel_booking'
),
path(
    "payment-success-demo/",
    views.payment_success_demo,
    name="payment_success_demo"
),
]