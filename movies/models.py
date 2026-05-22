from django.db import models
from django.contrib.auth.models import User


class Movie(models.Model):
    name = models.CharField(max_length=255)
    image = models.ImageField(upload_to='movies/')
    rating = models.DecimalField(max_digits=3, decimal_places=1)
    cast = models.TextField()
    description = models.TextField(blank=True, null=True)
    genre = models.CharField(max_length=100, blank=True, null=True)
    language = models.CharField(max_length=50, default='English')
    duration = models.PositiveIntegerField(help_text='Duration in minutes', default=120)
    release_date = models.DateField(blank=True, null=True)

    def __str__(self):
        return self.name

    def duration_display(self):
        hours = self.duration // 60
        minutes = self.duration % 60
        return f'{hours}h {minutes}m'


class Theater(models.Model):
    name = models.CharField(max_length=255)
    movie = models.ForeignKey(Movie, on_delete=models.CASCADE, related_name='theaters')
    time = models.DateTimeField()
    location = models.CharField(max_length=255, blank=True, null=True)
    total_seats = models.PositiveIntegerField(default=50)

    def __str__(self):
        return f'{self.name} - {self.movie.name} at {self.time}'

    def available_seats_count(self):
        return self.seats.filter(is_booked=False).count()


class Seat(models.Model):
    theater = models.ForeignKey(Theater, on_delete=models.CASCADE, related_name='seats')
    seat_number = models.CharField(max_length=10)
    is_booked = models.BooleanField(default=False)

    SEAT_CATEGORIES = [
        ('REGULAR', 'Regular'),
        ('PREMIUM', 'Premium'),
        ('RECLINER', 'Recliner'),
    ]
    category = models.CharField(max_length=20, choices=SEAT_CATEGORIES, default='REGULAR')

    def __str__(self):
        return f'{self.seat_number} in {self.theater.name}'


class Booking(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    seat = models.OneToOneField(Seat, on_delete=models.CASCADE)
    movie = models.ForeignKey(Movie, on_delete=models.CASCADE)
    theater = models.ForeignKey(Theater, on_delete=models.CASCADE)
    booked_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f'Booking by {self.user.username} for {self.seat.seat_number} at {self.theater.name}'
