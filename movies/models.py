from django.db import models
from django.utils import timezone
from django.contrib.auth.models import User
from urllib.parse import urlparse
import re


class Movie(models.Model):
    name = models.CharField(max_length=255)
    image = models.ImageField(upload_to='movies/')
    genre = models.CharField(
    max_length=100,
    blank=True,
    null=True,
    db_index=True
)
    cast = models.TextField()
    description = models.TextField(blank=True, null=True)
    language = models.CharField(
    max_length=50,
    default='English',
    db_index=True
)
    rating = models.DecimalField(
    max_digits=3,
    decimal_places=1,
    db_index=True
)
    duration = models.PositiveIntegerField(default=120)
    release_date = models.DateField(blank=True, null=True)
    trailer_url = models.URLField(
        blank=True, null=True,
        help_text='Paste YouTube URL: https://www.youtube.com/watch?v=VIDEO_ID'
    )

    def __str__(self):
        return self.name

    def duration_display(self):
        hours = self.duration // 60
        minutes = self.duration % 60
        return f'{hours}h {minutes}m'

    def get_video_id(self):
        if not self.trailer_url:
            return None
        url = self.trailer_url.strip()
        if not any(d in url for d in ['youtube.com', 'youtu.be']):
            return None
        patterns = [
            r'youtube\.com\/watch\?v=([a-zA-Z0-9_-]{11})',
            r'youtu\.be\/([a-zA-Z0-9_-]{11})',
            r'youtube\.com\/embed\/([a-zA-Z0-9_-]{11})',
        ]
        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                vid = match.group(1)
                if re.match(r'^[a-zA-Z0-9_-]{11}$', vid):
                    return vid
        return None

    @property
    def safe_trailer(self):
        video_id = self.get_video_id()
        if not video_id:
            return None
        return f'https://www.youtube.com/embed/{video_id}?rel=0&modestbranding=1'

    @property
    def trailer_thumbnail(self):
        video_id = self.get_video_id()
        if not video_id:
            return None
        return f'https://img.youtube.com/vi/{video_id}/maxresdefault.jpg'

    def has_valid_trailer(self):
        return self.safe_trailer is not None


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

    # TASK 2
    is_locked = models.BooleanField(default=False)

    locked_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='locked_seats'
    )

    lock_time = models.DateTimeField(
        null=True,
        blank=True
    )

    SEAT_CATEGORIES = [
        ('REGULAR', 'Regular'),
        ('PREMIUM', 'Premium'),
        ('RECLINER', 'Recliner'),
    ]

    category = models.CharField(
        max_length=20,
        choices=SEAT_CATEGORIES,
        default='REGULAR'
    )

    def __str__(self):
        return f'{self.seat_number} in {self.theater.name}'


class Booking(models.Model):

    STATUS_CHOICES = [ ('BOOKED', 'Booked'), ('CANCELLED', 'Cancelled'), ]
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    seat = models.OneToOneField(Seat, on_delete=models.CASCADE)
    movie = models.ForeignKey(Movie, on_delete=models.CASCADE)
    theater = models.ForeignKey(Theater, on_delete=models.CASCADE)
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='BOOKED'
    )
    booked_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f'Booking by {self.user.username} for {self.seat.seat_number}'
    
class Payment(models.Model):

    STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('SUCCESS', 'Success'),
        ('FAILED', 'Failed'),
    ]

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE
    )

    booking = models.ForeignKey(
        Booking,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )

    razorpay_order_id = models.CharField(
        max_length=255,
        unique=True
    )

    razorpay_payment_id = models.CharField(
        max_length=255,
        null=True,
        blank=True
    )

    amount = models.PositiveIntegerField()

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='PENDING'
    )

    webhook_received = models.BooleanField(
        default=False
    )

    webhook_event_id = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        unique=True
    )

    payment_verified = models.BooleanField(
        default=False
    )

    failure_reason = models.TextField(
        null=True,
        blank=True
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    def __str__(self):
        return self.razorpay_order_id
    
    