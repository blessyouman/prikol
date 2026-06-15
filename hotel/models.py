from django.db import models
from django.contrib.auth.models import AbstractUser

class User(AbstractUser):
    full_name = models.CharField(max_length=255)
    avatar_path = models.ImageField(upload_to='avatars/', max_length=255, null=True, blank=True)

    class Meta:
        db_table = 'users'

    def __str__(self):
        return self.username

User._meta.get_field('password').db_column = 'password_hash'


class Room(models.Model):
    ROOM_TYPES = (
        (1, 'standard'),
        (2, 'deluxe'),
        (3, 'suite'),
    )
    room_number = models.CharField(max_length=10, unique=True)
    type = models.IntegerField(choices=ROOM_TYPES)
    price_per_night = models.IntegerField()
    capacity = models.IntegerField()
    description = models.TextField()
    image_path = models.CharField(max_length=255)  # Путь к фото внутри статики

    class Meta:
        db_table = 'rooms'  # Имя таблицы строго по ТЗ

    def __str__(self):
        return f"Комната {self.room_number} ({self.get_type_display()})"


class Booking(models.Model):
    STATUS_CHOICES = (
        ('active', 'active'),
        ('cancelled', 'cancelled'),
    )
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='bookings', db_column='user_id')
    room = models.ForeignKey(Room, on_delete=models.CASCADE, related_name='bookings', db_column='room_id')
    check_in_date = models.DateField()
    check_out_date = models.DateField()
    total_price = models.IntegerField()
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='active')

    class Meta:
        db_table = 'bookings'  # Имя таблицы строго по ТЗ

    def __str__(self):
        return f"Бронь {self.id} (Пользователь: {self.user.username})"
    
