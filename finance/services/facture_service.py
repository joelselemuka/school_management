import io

from click import File
from reportlab.pdfgen import canvas

from django.core.mail import EmailMessage
from django.db import transaction
from django.utils import timezone


from finance.models import Facture
from finance.services.reference_service import ReferenceService




class FactureService:

    @staticmethod
    @transaction.atomic
    def create_from_paiement(paiement):

        if hasattr(paiement, "facture"):
            return paiement.facture

        numero = ReferenceService.generate("FACT")

        facture = Facture.objects.create(
            numero=numero,
            paiement=paiement,
            eleve=paiement.eleve,
            montant=paiement.montant,
            date_emission=timezone.now(),
            statut="PAID"
        )
        pdf_buffer = FactureService.generate_pdf(paiement)

        facture.pdf.save(
            f"{numero}.pdf",
            File(pdf_buffer),
            save=True
        )

        return facture
    
    
    @staticmethod
    def generate_pdf(paiement):

        buffer = io.BytesIO()

        pdf = canvas.Canvas(buffer)


        pdf.drawString(

            100,

            800,

            f"FACTURE : {paiement.reference}"

        )


        pdf.drawString(

            100,

            770,

            f"Eleve : {paiement.eleve}"

        )


        pdf.drawString(

            100,

            740,

            f"Montant : {paiement.montant}"

        )


        pdf.save()

        buffer.seek(0)

        return buffer


    @staticmethod
    def send_invoice(paiement):

        parent = paiement.eleve.parents.first()


        if not parent or not parent.user.email:

            return


        pdf = FactureService.generate_pdf(paiement)


        email = EmailMessage(

            subject="Facture paiement",

            body="Voir facture",

            to=[parent.user.email]

        )


        email.attach(

            f"{paiement.reference}.pdf",

            pdf.read(),

            "application/pdf"

        )


        email.send()

