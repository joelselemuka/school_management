from django.core.mail import send_mail
from django.conf import settings


class AdmissionNotificationService:


    @staticmethod
    def send_admission_confirmation(eleve, parents):

        emails = [

            p.user.email

            for p in parents

            if p.user.email

        ]

        if not emails:
            return


        send_mail(

            subject="Confirmation inscription",

            message=f"""
Bonjour,

L'inscription de {eleve.nom} {eleve.prenom} est confirmée.

Matricule : {eleve.user.matricule}

""",

            from_email=settings.DEFAULT_FROM_EMAIL,

            recipient_list=emails,

            fail_silently=True

        )


    @staticmethod
    def send_admission_rejected(application):

        emails = [

            g.parent_email

            for g in application.guardians.all()

            if g.parent_email

        ]

        if not emails:
            return


        send_mail(

            subject="Admission rejetée",

            message="Votre demande d'admission a été rejetée",

            from_email=settings.DEFAULT_FROM_EMAIL,

            recipient_list=emails,

            fail_silently=True

        )
