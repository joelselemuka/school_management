import logging
from django.db.models import Sum, Count, Q
from django.utils import timezone
from rest_framework import views, status, permissions
from rest_framework.response import Response

from users.models import Eleve, Personnel
from academics.models import Classe, Bulletin
from finance.models import Facture, Paiement
from attendance.models import Presence
from core.models import AnneeAcademique, Ecole

logger = logging.getLogger(__name__)


class DashboardAnalyticsView(views.APIView):
    """
    Endpoint central pour le tableau de bord de l'application.
    Fournit des statistiques globales sur l'école.
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, *args, **kwargs):
        try:
            ecole = Ecole.get_configuration()
            annee_courante = AnneeAcademique.get_active()
            
            if not annee_courante:
                return Response(
                    {"detail": "Aucune année académique courante configurée."},
                    status=status.HTTP_400_BAD_REQUEST
                )

            # 1. Démographie
            nb_eleves = Eleve.objects.filter(is_active=True).count()
            nb_personnel = Personnel.objects.filter(is_active=True).count()
            nb_classes = Classe.objects.filter(annee_academique=annee_courante, actif=True).count()

            # 2. Finances (sur l'année courante)
            # Total facturé
            factures_annee = Facture.objects.filter(eleve__inscriptions__annee_academique=annee_courante)
            total_facture = factures_annee.aggregate(Total=Sum('montant_total'))['Total'] or 0
            
            # Total payé (paiements confirmés)
            paiements_annee = Paiement.objects.filter(
                statut='CONFIRMED',
                date_paiement__year=timezone.now().year # Ou lié à l'année académique
            )
            total_encaisse = paiements_annee.aggregate(Total=Sum('montant_total'))['Total'] or 0

            # 3. Académique
            # Bulletins générés
            nb_bulletins = Bulletin.objects.filter(
                eleve__inscriptions__annee_academique=annee_courante
            ).count()
            
            # Taux de présence du jour (Élèves)
            aujourdhui = timezone.now().date()
            presences_jour = Presence.objects.filter(
                seance__date=aujourdhui,
                seance__annee_academique=annee_courante
            )
            total_presences = presences_jour.count()
            presents_jour = presences_jour.filter(statut='present').count()
            taux_presence_jour = (presents_jour / total_presences * 100) if total_presences > 0 else 100.0

            data = {
                "annee_academique": {
                    "id": annee_courante.id,
                    "nom": annee_courante.nom
                },
                "demographie": {
                    "eleves_actifs": nb_eleves,
                    "personnel_actif": nb_personnel,
                    "classes_actives": nb_classes,
                },
                "finances": {
                    "total_facture": total_facture,
                    "total_encaisse": total_encaisse,
                    "taux_recouvrement": round((total_encaisse / total_facture * 100) if total_facture > 0 else 0, 2)
                },
                "academique": {
                    "bulletins_generes": nb_bulletins,
                    "taux_presence_jour_eleves": round(taux_presence_jour, 2)
                }
            }

            return Response(data, status=status.HTTP_200_OK)

        except Exception as e:
            logger.error(f"Erreur DashboardAnalyticsView : {e}")
            return Response(
                {"detail": "Erreur lors du calcul des statistiques."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
