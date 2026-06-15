from datetime import datetime
from django.contrib import messages
from django.contrib.auth.hashers import check_password, make_password
from django.core.files.storage import FileSystemStorage
from django.db import connection
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from .models import Booking, Room

def get_current_user(request):
    user_id = request.session.get('user_id')
    if not user_id:
        return None
    with connection.cursor() as cursor:
        cursor.execute('SELECT id, username, full_name, avatar_path FROM users WHERE id = %s', [user_id])
        row = cursor.fetchone()
        return {'id': row[0], 'username': row[1], 'full_name': row[2], 'avatar_path': row[3]} if row else None


def register_view(request):
    if request.method != 'POST':
        return render(request, 'register.html')
        
    username = request.POST.get('username')
    password = request.POST.get('password')
    full_name = request.POST.get('full_name')
    
    if not all([username, password, full_name]):
        messages.error(request, "Все поля обязательны для заполнения.")
        return render(request, 'register.html')
        
    with connection.cursor() as cursor:
        cursor.execute('SELECT id FROM users WHERE username = %s', [username])
        if cursor.fetchone():
            messages.error(request, "Пользователь с таким логином уже существует.")
            return render(request, 'register.html')
        
        cursor.execute(
            '''
            INSERT INTO users 
            (username, password_hash, full_name, avatar_path, first_name, last_name, email, is_superuser, is_staff, is_active, date_joined) 
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s) RETURNING id
            ''',
            [username, make_password(password), full_name, '', '', '', '', False, False, True, timezone.now()]
        )
        request.session['user_id'] = cursor.fetchone()[0]
        
    return redirect('rooms')


def login_view(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        
        with connection.cursor() as cursor:
            cursor.execute('SELECT id, password_hash FROM users WHERE username = %s', [username])
            row = cursor.fetchone()
            
        if row and check_password(password, row[1]):
            request.session['user_id'] = row[0]
            return redirect('rooms')
        messages.error(request, "Неверный логин или пароль.")
        
    return render(request, 'login.html')


def logout_view(request):
    request.session.pop('user_id', None)
    return redirect('rooms')


def rooms_view(request):
    rooms = Room.objects.all()
    
    room_type = request.GET.get('type')
    if room_type:
        rooms = rooms.filter(type=room_type)
        
    capacity = request.GET.get('capacity')
    if capacity:
        rooms = rooms.filter(capacity=capacity)
        
    sort = request.GET.get('sort')
    if sort in ['asc', 'desc']:
        rooms = rooms.order_by('price_per_night' if sort == 'asc' else '-price_per_night')
        
    return render(request, 'rooms.html', {'rooms': rooms, 'custom_user': get_current_user(request)})


def book_room(request, room_id):
    current_user = get_current_user(request)
    if not current_user:
        return redirect('login')
        
    if request.method == 'POST':
        room = get_object_or_404(Room, id=room_id)
        
        try:
            check_in = datetime.strptime(request.POST.get('check_in', ''), '%Y-%m-%d').date()
            check_out = datetime.strptime(request.POST.get('check_out', ''), '%Y-%m-%d').date()
        except (ValueError, TypeError):
            messages.error(request, "Неверный формат дат.")
            return redirect('rooms')
            
        if check_in < datetime.today().date():
            messages.error(request, "Дата заезда не может быть в прошлом.")
            return redirect('rooms')
            
        if check_out <= check_in:
            messages.error(request, "Дата выезда должна быть строго позже даты заезда.")
            return redirect('rooms')
            
        total_price = (check_out - check_in).days * room.price_per_night
        
        with connection.cursor() as cursor:
            cursor.execute(
                'INSERT INTO bookings (user_id, room_id, check_in_date, check_out_date, total_price, status) VALUES (%s, %s, %s, %s, %s, %s)',
                [current_user['id'], room.id, check_in, check_out, total_price, 'active']
            )
            
        messages.success(request, "Номер успешно забронирован!")
        return redirect('profile')
        
    return redirect('rooms')


def profile_view(request):
    current_user = get_current_user(request)
    if not current_user:
        return redirect('login')
        
    if request.method == 'POST' and request.FILES.get('avatar'):
        avatar = request.FILES['avatar']
        fs = FileSystemStorage()
        filename = fs.save(f"avatars/{avatar.name}", avatar)
        
        with connection.cursor() as cursor:
            cursor.execute('UPDATE users SET avatar_path = %s WHERE id = %s', [fs.url(filename), current_user['id']])
        return redirect('profile')
        
    bookings = []
    types_map = {1: 'standard', 2: 'deluxe', 3: 'suite'}
    
    with connection.cursor() as cursor:
        cursor.execute('''
            SELECT b.id, b.check_in_date, b.check_out_date, b.total_price, b.status, r.room_number, r.type
            FROM bookings b JOIN rooms r ON b.room_id = r.id
            WHERE b.user_id = %s ORDER BY b.id DESC
        ''', [current_user['id']])
        
        for row in cursor.fetchall():
            bookings.append({
                'id': row[0], 'check_in_date': row[1], 'check_out_date': row[2],
                'total_price': row[3], 'status': row[4], 'room_number': row[5],
                'room_type': types_map.get(row[6], 'standard')
            })
            
    return render(request, 'profile.html', {'bookings': bookings, 'custom_user': current_user})


def cancel_booking(request, booking_id):
    current_user = get_current_user(request)
    if not current_user:
        return redirect('login')
        
    with connection.cursor() as cursor:
        cursor.execute('UPDATE bookings SET status = %s WHERE id = %s AND user_id = %s', ['cancelled', booking_id, current_user['id']])
        
    messages.success(request, "Бронирование отменено.")
    return redirect('profile')