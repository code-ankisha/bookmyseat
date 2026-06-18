from django.shortcuts import render, redirect, get_object_or_404
from .models import Movie, Theater, Seat, Booking
from django.contrib.auth.decorators import login_required
from django.db import IntegrityError, transaction
from django.contrib import messages
from urllib.parse import urlparse
from django.utils import timezone
from datetime import timedelta
from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings
from .models import Movie, Theater, Seat, Booking, Payment
from django.contrib.admin.views.decorators import staff_member_required
from django.core.cache import cache
from django.db.models import Count , Sum , Q
from django.db.models.functions import ExtractHour
from django.core.paginator import Paginator
from .tasks import send_booking_email
import razorpay
import re
import json

client = razorpay.Client(
    auth=(
        settings.RAZORPAY_KEY_ID,
        settings.RAZORPAY_KEY_SECRET
    )
)


# ── TASK 1: Secure YouTube video ID extractor ──
def extract_youtube_id(url):
    """
    Extracts video ID from any YouTube URL format.
    Returns None if URL is invalid or not from YouTube.
    """
    if not url:
        return None

    url = url.strip()

    # Security- only allow YouTube domains
    parsed = urlparse(url)
    allowed_hosts = [
        'www.youtube.com',
        'youtube.com',
        'youtu.be',
    ]

    if parsed.netloc not in allowed_hosts:
        return None

    patterns = [
        r'(?:youtube\.com\/watch\?v=)([a-zA-Z0-9_-]{11})',
        r'(?:youtu\.be\/)([a-zA-Z0-9_-]{11})',
        r'(?:youtube\.com\/embed\/)([a-zA-Z0-9_-]{11})',
        r'(?:youtube\.com\/v\/)([a-zA-Z0-9_-]{11})',
        r'(?:youtube-nocookie\.com\/embed\/)([a-zA-Z0-9_-]{11})',
    ]

    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            vid = match.group(1)
            if re.match(r'^[a-zA-Z0-9_-]{11}$', vid):
                return vid

    return None




def movie_list(request):

    search_query = request.GET.get('search', '')
    selected_genres = request.GET.getlist('genre')
    selected_languages = request.GET.getlist('language')
    sort_by = request.GET.get('sort', '')

    movies = Movie.objects.all()

    # Search
    if search_query:
        movies = movies.filter(
            name__icontains=search_query
        )
    filtered_for_counts = movies

    # multi Language Filter
    if selected_languages:
        movies = movies.filter(
            language__in=selected_languages
        )

        filtered_for_counts = filtered_for_counts.filter(
            language__in=selected_languages
        )

    # Genre counts based on search + language filters
    genre_counts = filtered_for_counts.values(
        'genre'
    ).annotate(
        total=Count('id')
    ).order_by('genre')

    # multi Genre Filter
    if selected_genres:
        movies = movies.filter(
            genre__in=selected_genres
        )

    # sorting
    if sort_by == 'rating_desc':
        movies = movies.order_by('-rating')
    elif sort_by == 'rating_asc':
        movies = movies.order_by('rating')
    elif sort_by == 'name_asc':
        movies = movies.order_by('name')
    elif sort_by == 'name_desc':
        movies = movies.order_by('-name')

    # Pagination
    paginator = Paginator(movies, 6)
    page_number = request.GET.get('page')
    movies = paginator.get_page(page_number)

    genres = Movie.objects.values_list(
        'genre',
        flat=True
    ).distinct()

    languages = Movie.objects.values_list(
        'language',
        flat=True
    ).distinct()

    return render(
        request,
        'movies/movie_list.html',
        {
            'movies': movies,
            'search_query': search_query,
            'selected_genres': selected_genres,
            'selected_languages': selected_languages,
            'sort_by': sort_by,
            'genres': genres,
            'languages': languages,
            'genre_counts': genre_counts,
        }
    )


def movie_detail(request, movie_id):
    """Task 1: Movie detail with secure trailer embedding."""
    movie = get_object_or_404(Movie, id=movie_id)
    theaters = Theater.objects.filter(movie=movie)

    # Task 1: Extract video ID securely from stored URL

    video_id = extract_youtube_id(movie.trailer_url)

    # Task 1: Build safe embed URL only if video_id is valid

    embed_url = None
    if video_id:
        # Use standard youtube.com embed - more reliable than nocookie

        embed_url = f'https://www.youtube.com/embed/{video_id}?rel=0&modestbranding=1&enablejsapi=1'

    return render(request, 'movies/movie_detail.html', {
        'movie': movie,
        'theaters': theaters,
        'embed_url': embed_url,
        'video_id': video_id,
        'has_trailer': embed_url is not None,
    })


def theater_list(request, movie_id):
    movie = get_object_or_404(Movie, id=movie_id)
    theaters = Theater.objects.filter(movie=movie)
    return render(request, 'movies/theater_list.html', {
        'movie': movie,
        'theaters': theaters,
    })


def release_expired_locks():

    expiry_time = timezone.now() - timedelta(minutes=2)

    Seat.objects.filter(
        is_locked=True,
        lock_time__lt=expiry_time
    ).update(
        is_locked=False,
        locked_by=None,
        lock_time=None,
    )

    # Payment timeout cleanup
    expired_payments = Payment.objects.filter(
        status="PENDING",
        created_at__lt=timezone.now() - timedelta(minutes=15)
    )

    expired_payments.update(
        status="FAILED"
    )

@login_required(login_url='/login/')
def lock_seat(request, seat_id):

    release_expired_locks()

    try:
        with transaction.atomic():

            seat = Seat.objects.select_for_update().get(id=seat_id)

            if seat.is_booked:
                return JsonResponse({
                    "success": False,
                    "message": "Seat already booked"
                })

            if seat.is_locked and seat.locked_by != request.user:
                return JsonResponse({
                    "success": False,
                    "message": "Seat already locked"
                })

            seat.is_locked = True
            seat.locked_by = request.user
            seat.lock_time = timezone.now()
            seat.save()

            return JsonResponse({
                "success": True
            })

    except Seat.DoesNotExist:
        return JsonResponse({
            "success": False
        })
    
@login_required(login_url='/login/')
def unlock_seat(request, seat_id):

    try:
        seat = Seat.objects.get(id=seat_id)

        if seat.locked_by == request.user:

            seat.is_locked = False
            seat.locked_by = None
            seat.lock_time = None
            seat.save()

        return JsonResponse({"success": True})

    except Seat.DoesNotExist:

        return JsonResponse({"success": False})


@login_required(login_url='/login/')
def book_seats(request, theater_id):

    theater = get_object_or_404(Theater, id=theater_id)

    release_expired_locks()

    seats = Seat.objects.filter(theater=theater)

    if request.method == 'POST':

        selected_seats = request.POST.getlist('seats')

        if not selected_seats:
            messages.error(request, 'Please select at least one seat.')

            return render(
                request,
                'movies/seat_selection.html',
                {
                    'theater': theater,
                    'seats': seats
                }
            )

        booked_count = len(selected_seats)

        request.session['selected_seats'] = selected_seats
        request.session['theater_id'] = theater.id

        return redirect('create_payment')

    return render(
        request,
        'movies/seat_selection.html',
        {
            'theater': theater,
            'seats': seats
        }
    )

    booked_count = 0
    error_seats = []

    for seat_id in selected_seats:
            try:
                with transaction.atomic():
                    seat = Seat.objects.select_for_update().get(
                        id=seat_id,
                        theater=theater,
                    )

                    if seat.is_booked:
                        error_seats.append(seat.seat_number)
                        continue

                    booked_count += 1

            except IntegrityError:
                error_seats.append(seat.seat_number)

    if error_seats:
            messages.warning(request, f'Already booked: {", ".join(error_seats)}')

    if booked_count > 0:

          request.session['selected_seats'] = selected_seats
          request.session['theater_id'] = theater.id

          return redirect('create_payment')

    return render(
           request,
           'movies/seat_selection.html',
         {
        'theater': theater,
        'seats': seats
         }
)

@login_required(login_url='/login/')
def create_payment(request):

    selected_seats = request.session.get('selected_seats', [])
    theater_id = request.session.get('theater_id')

    theater = get_object_or_404(Theater, id=theater_id)

    seat_objects = Seat.objects.filter(id__in=selected_seats)

    seat_numbers = ", ".join(
        seat.seat_number for seat in seat_objects
    )

    amount = len(selected_seats) * 200   # ₹200 per seat

    razorpay_order = client.order.create({
        "amount": amount * 100,
        "currency": "INR",
        "payment_capture": 1
    })
    print("KEY =", settings.RAZORPAY_KEY_ID)
    print("AMOUNT =", amount * 100)
    print("ORDER =", razorpay_order)

    payment = Payment.objects.create(
        user=request.user,
        razorpay_order_id=razorpay_order["id"],
        amount=amount,
        status="PENDING"
    )

    return render(
        request,
        "movies/payment.html",
        {
            "payment": payment,
            "razorpay_order_id": razorpay_order["id"],
            "razorpay_key": settings.RAZORPAY_KEY_ID,
            "amount": amount * 100,
            "display_amount": amount,
            "theater": theater,
            "seat_numbers": seat_numbers,
        }
    )

@login_required(login_url='/login/')
def booking_confirmation(request, booking_id):
    booking = get_object_or_404(Booking, id=booking_id, user=request.user)
    return render(request, 'movies/booking_confirmation.html', {'booking': booking})

@login_required
def payment_success(request):

    payment_id = request.GET.get("payment_id")
    order_id = request.GET.get("order_id")
    signature = request.GET.get("signature")

    params_dict = {
        "razorpay_order_id": order_id,
        "razorpay_payment_id": payment_id,
        "razorpay_signature": signature
    }

    try:
        client.utility.verify_payment_signature(params_dict)
        print("PAYMENT VERIFIED")

        messages.success(
            request,
            "Payment verified successfully!"
        )

        print(" Signature Verification Successful")

    except Exception as e:

        print(" Signature Verification Failed")

        messages.error(
            request,
            "Payment verification failed"
        )

        return redirect("movie_list")

    payment = Payment.objects.get(
        razorpay_order_id=order_id
    )

    # Idempotency Protection
    if payment.status == "SUCCESS":
        messages.info(
            request,
            "Payment already processed."
        )
        return redirect("profile")

    payment.razorpay_payment_id = payment_id
    payment.status = "SUCCESS"
    payment.save()

    # Get data from session
    selected_seats = request.session.get("selected_seats", [])
    theater_id = request.session.get("theater_id")

    theater = Theater.objects.get(id=theater_id)

    seats = Seat.objects.filter(id__in=selected_seats)

    # Create bookings
    for seat in seats:

        seat.is_booked = True
        seat.is_locked = False
        seat.locked_by = None
        seat.lock_time = None
        seat.save()

        booking = Booking.objects.create(
            user=request.user,
            seat=seat,
            movie=theater.movie,
            theater=theater
        )

        payment.booking = booking

        send_booking_email.delay(
            user_email=request.user.email,
            username=request.user.username,
            movie_name=theater.movie.name,
            theater_name=theater.name,
            seat_number=seat.seat_number,
            show_time=str(theater.time),
            payment_id=payment_id
        )

    payment.save()

    # Clear session
    request.session.pop("selected_seats", None)
    request.session.pop("theater_id", None)

    messages.success(
        request,
        "Demo Payment Successful! Booking Confirmed."
    )

    return redirect("profile")

@login_required
def payment_failed(request):

    messages.error(
        request,
        "Payment failed."
    )

    return redirect("movie_list")

@login_required
def payment_cancelled(request):

    messages.warning(
        request,
        "Payment cancelled."
    )

    return redirect("movie_list")

@csrf_exempt
def razorpay_webhook(request):

    return HttpResponse(
        "Webhook received",
        status=200
    )

@staff_member_required
def admin_dashboard(request):

    today = timezone.now()

    total_bookings = Booking.objects.filter(
    status="BOOKED"
).count()

    cancelled_bookings = Booking.objects.filter(
        status="CANCELLED"
    ).count()

    cancellation_rate = 0

    if total_bookings:
        cancellation_rate = round(
            (cancelled_bookings / total_bookings) * 100,
            2
        )

    daily_revenue = Payment.objects.filter(
        status="SUCCESS",
        created_at__date=today.date()
    ).aggregate(
        total=Sum("amount")
    )["total"] or 0

    weekly_revenue = Payment.objects.filter(
        status="SUCCESS",
        created_at__gte=today - timedelta(days=7)
    ).aggregate(
        total=Sum("amount")
    )["total"] or 0

    monthly_revenue = Payment.objects.filter(
        status="SUCCESS",
        created_at__gte=today - timedelta(days=30)
    ).aggregate(
        total=Sum("amount")
    )["total"] or 0

    popular_movies = (
    Movie.objects
    .annotate(
        total_bookings=Count(
            "booking",
            filter=Q(booking__status="BOOKED")
        )
    )
    .order_by("-total_bookings")
)

    busiest_theaters = (
    Theater.objects
    .annotate(
        total_bookings=Count(
            "booking",
            filter=Q(booking__status="BOOKED")
        )
    )
    .order_by("-total_bookings")
)

    peak_hours = (
        Booking.objects
        .annotate(hour=ExtractHour("booked_at"))
        .values("hour")
        .annotate(total=Count("id"))
        .order_by("-total")
    )

    theater_occupancy = []

    for theater in Theater.objects.all():

        total_seats = theater.seats.count()

        booked_seats = theater.seats.filter(
            is_booked=True
        ).count()

        occupancy = 0

        if total_seats:
            occupancy = round(
                (booked_seats / total_seats) * 100,
                2
            )

        theater_occupancy.append({
            "name": theater.name,
            "occupancy": occupancy
        })

    theater_occupancy.sort(
        key=lambda x: x["occupancy"],
        reverse=True
    )

    dashboard_data = {
        "total_bookings": total_bookings,
        "daily_revenue": daily_revenue,
        "weekly_revenue": weekly_revenue,
        "monthly_revenue": monthly_revenue,
        "popular_movies": popular_movies,
        "busiest_theaters": busiest_theaters,
        "peak_hours": peak_hours,
        "theater_occupancy": theater_occupancy[:5],
        "cancelled_bookings": cancelled_bookings,
        "cancellation_rate": cancellation_rate,
    }

    

    return render(
        request,
        "movies/admin_dashboard.html",
        dashboard_data
    )

@login_required
def cancel_booking(request, booking_id):

    booking = get_object_or_404(
        Booking,
        id=booking_id,
        user=request.user
    )

    booking.status = "CANCELLED"
    booking.save()

    booking.seat.is_booked = False
    booking.seat.save()

    Payment.objects.filter(
        user=request.user,
        status="SUCCESS"
    ).update(
        status="CANCELLED"
    )

    cache.delete("dashboard_data")

    messages.success(
        request,
        "Booking cancelled successfully."
    )

    return redirect("profile")

@login_required
def payment_success_demo(request):

    selected_seats = request.session.get("selected_seats", [])
    theater_id = request.session.get("theater_id")

    payment = Payment.objects.create(
    user=request.user,
    razorpay_order_id=f"DEMO_{timezone.now().timestamp()}",
    razorpay_payment_id="DEMO_PAYMENT",
    amount=len(selected_seats) * 200,
    status="SUCCESS"
)

    if not selected_seats or not theater_id:
        messages.error(
            request,
            "No seats selected."
        )
        return redirect("movie_list")

    theater = Theater.objects.get(id=theater_id)

    seats = Seat.objects.filter(id__in=selected_seats)

    for seat in seats:

        seat.is_booked = True
        seat.is_locked = False
        seat.locked_by = None
        seat.lock_time = None
        seat.save()

        Booking.objects.create(
            user=request.user,
            seat=seat,
            movie=theater.movie,
            theater=theater,
            status="BOOKED"
        )

        print("EMAIL =", request.user.email)

        send_booking_email.delay(
            user_email=request.user.email,
            username=request.user.username,
            movie_name=theater.movie.name,
            theater_name=theater.name,
            seat_number=seat.seat_number,
            show_time=str(theater.time),
            payment_id="DEMO_PAYMENT"
        )

    request.session.pop("selected_seats", None)
    request.session.pop("theater_id", None)

    cache.delete("dashboard_data")

    messages.success(
        request,
        "Demo Payment Successful! Booking Confirmed."
    )

    return redirect("profile")