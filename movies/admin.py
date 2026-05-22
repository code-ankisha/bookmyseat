from django.contrib import admin
from .models import Movie, Theater, Seat, Booking


@admin.register(Movie)
class MovieAdmin(admin.ModelAdmin):
    list_display = ['name', 'rating', 'genre', 'language', 'duration', 'release_date']
    list_filter = ['genre', 'language']
    search_fields = ['name', 'cast', 'description']


@admin.register(Theater)
class TheaterAdmin(admin.ModelAdmin):
    list_display = ['name', 'movie', 'time', 'location', 'available_seats_count']
    list_filter = ['movie']
    search_fields = ['name', 'location']


@admin.register(Seat)
class SeatAdmin(admin.ModelAdmin):
    list_display = ['theater', 'seat_number', 'category', 'is_booked']
    list_filter = ['is_booked', 'category', 'theater']


@admin.register(Booking)
class BookingAdmin(admin.ModelAdmin):
    list_display = ['user', 'movie', 'theater', 'seat', 'booked_at']
    list_filter = ['movie', 'theater']
    search_fields = ['user__username', 'movie__name']
