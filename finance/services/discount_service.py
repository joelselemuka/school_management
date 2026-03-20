from decimal import Decimal

from core.models import SchoolConfiguration


class DiscountService:

    @staticmethod
    def calculate(eleve, montant):
        config = SchoolConfiguration.objects.filter(actif=True).first()
        if not config or not config.allow_discount:
            return montant

        total_discount = Decimal("0")

        for link in eleve.parent_links.all():
            parent = link.parent
            user = parent.user

            # Remise enseignant
            if hasattr(user, "personnel_profile") and user.personnel_profile.fonction == "enseignant":
                total_discount += montant * config.teacher_discount_percent / 100

            # Remise fratrie
            if parent.enfants.count() >= config.siblings_min_count:
                total_discount += montant * config.siblings_discount_percent / 100

        # Plafond 100%
        if total_discount > montant:
            total_discount = montant

        return montant - total_discount
