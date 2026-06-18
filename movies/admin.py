from django.contrib import admin
from .models import Movie, Theater, Seat, Booking


@admin.register(Movie)
class MovieAdmin(admin.ModelAdmin):

    list_display = ['name', 'rating', 'genre', 'language', 'has_trailer_display']
    search_fields = ['name', 'cast', 'description']
    list_filter = ['genre', 'language']

    fieldsets = (
        ('Basic Info', {
            'fields': ('name', 'image', 'rating', 'description')
        }),
        ('Movie Details', {
            'fields': ('cast', 'genre', 'language', 'duration', 'release_date')
        }),
        ('Trailer - Task 1', {
            'fields': ('trailer_url',),
            'description': 'Paste YouTube URL: https://www.youtube.com/watch?v=VIDEO_ID',
        }),
    )

    def has_trailer_display(self, obj):
        return obj.has_valid_trailer()
    has_trailer_display.boolean = True
    has_trailer_display.short_description = 'Has Trailer'


@admin.register(Theater)
class TheaterAdmin(admin.ModelAdmin):
    list_display = ['name', 'movie', 'time', 'location']
    list_filter = ['movie']


@admin.register(Seat)
class SeatAdmin(admin.ModelAdmin):
    list_display = ['theater', 'seat_number', 'category', 'is_booked']
    list_filter = ['is_booked', 'theater']


@admin.register(Booking)
class BookingAdmin(admin.ModelAdmin):
    list_display = ['user', 'movie', 'theater', 'seat', 'booked_at']