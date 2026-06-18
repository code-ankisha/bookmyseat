from celery import shared_task
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
import logging

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3)
def send_booking_email(
    self,
    user_email,
    username,
    movie_name,
    theater_name,
    seat_number,
    show_time,
    payment_id
):

    try:

        html_content = render_to_string(
            "emails/booking_confirmation.html",
            {
                "username": username,
                "movie_name": movie_name,
                "theater_name": theater_name,
                "seat_number": seat_number,
                "show_time": show_time,
                "payment_id": payment_id,
            }
        )

        email = EmailMultiAlternatives(
            subject="Booking Confirmation",
            body="Booking Confirmed",
            to=[user_email]
        )

        email.attach_alternative(
            html_content,
            "text/html"
        )

        print("Sending email to:", user_email)

        result = email.send()

        print("EMAIL RESULT =", result)

        email.send()

    except Exception as exc:

        logger.error(
            f"Email failed: {exc}"
        )

        raise self.retry(
            exc=exc,
            countdown=10
        )