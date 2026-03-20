from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.conf import settings


class EmailService:

    @staticmethod
    def send(to, subject, template, context):

        html = render_to_string(template, context)

        msg = EmailMultiAlternatives(
            subject=subject,
            body=html,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[to]
        )

        msg.attach_alternative(html, "text/html")

        msg.send()
