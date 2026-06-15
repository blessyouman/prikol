from django.urls import path
from . import views

urlpatterns = [
    path('', views.rooms_view, name='rooms'),
    path('register/', views.register_view, name='register'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('book/<int:room_id>/', views.book_room, name='book_room'),
    path('profile/', views.profile_view, name='profile'),
    path('booking/cancel/<int:booking_id>/', views.cancel_booking, name='cancel_booking'),
]