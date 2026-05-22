from django.shortcuts import render, redirect, get_object_or_404
from .models import Movie, Theater, Seat, Booking
from django.contrib.auth.decorators import login_required
from django.db import IntegrityError
from django.contrib import messages


def movie_list(request):
    search_query = request.GET.get('search', '')
    genre_filter = request.GET.get('genre', '')
    language_filter = request.GET.get('language', '')

    movies = Movie.objects.all()

    if search_query:
        movies = movies.filter(name__icontains=search_query)
    if genre_filter:
        movies = movies.filter(genre__icontains=genre_filter)
    if language_filter:
        movies = movies.filter(language__icontains=language_filter)

    genres = Movie.objects.values_list('genre', flat=True).distinct()
    languages = Movie.objects.values_list('language', flat=True).distinct()

    context = {
        'movies': movies,
        'search_query': search_query,
        'genres': genres,
        'languages': languages,
        'genre_filter': genre_filter,
        'language_filter': language_filter,
    }
    return render(request, 'movies/movie_list.html', context)


def movie_detail(request, movie_id):
    movie = get_object_or_404(Movie, id=movie_id)
    theaters = Theater.objects.filter(movie=movie)
    return render(request, 'movies/movie_detail.html', {'movie': movie, 'theaters': theaters})


def theater_list(request, movie_id):
    movie = get_object_or_404(Movie, id=movie_id)
    theaters = Theater.objects.filter(movie=movie)
    return render(request, 'movies/theater_list.html', {'movie': movie, 'theaters': theaters})


@login_required(login_url='/login/')
def book_seats(request, theater_id):
    theater = get_object_or_404(Theater, id=theater_id)
    seats = Seat.objects.filter(theater=theater)

    if request.method == 'POST':
        selected_seats = request.POST.getlist('seats')

        if not selected_seats:
            messages.error(request, 'Please select at least one seat.')
            return render(request, 'movies/seat_selection.html', {'theater': theater, 'seats': seats})

        error_seats = []
        booked_count = 0

        for seat_id in selected_seats:
            seat = get_object_or_404(Seat, id=seat_id, theater=theater)
            if seat.is_booked:
                error_seats.append(seat.seat_number)
                continue
            try:
                Booking.objects.create(
                    user=request.user,
                    seat=seat,
                    movie=theater.movie,
                    theater=theater
                )
                seat.is_booked = True
                seat.save()
                booked_count += 1
            except IntegrityError:
                error_seats.append(seat.seat_number)

        if error_seats:
            messages.warning(request, f'Seats already booked: {", ".join(error_seats)}')

        if booked_count > 0:
            messages.success(request, f'Successfully booked {booked_count} seat(s)!')
            return redirect('profile')

        return render(request, 'movies/seat_selection.html', {'theater': theater, 'seats': seats})

    return render(request, 'movies/seat_selection.html', {'theater': theater, 'seats': seats})


@login_required(login_url='/login/')
def booking_confirmation(request, booking_id):
    booking = get_object_or_404(Booking, id=booking_id, user=request.user)
    return render(request, 'movies/booking_confirmation.html', {'booking': booking})
