"""
Tâches Celery pour la finance (rappels, génération documents).
"""

from celery import shared_task
from django.utils import timezone
from datetime import timedelta


@shared_task
def send_payment_reminders():
    """
    Tâche planifiée: Envoie des rappels de paiement aux parents.
    
    Exécutée chaque lundi à 9h via Celery Beat.
    """
    from finance.models import DetteEleve
    from communication.tasks import send_email_notification
    
    # Récupérer les dettes impayées
    dettes_impayees = DetteEleve.objects.filter(
        statut__in=['IMPAYE', 'PARTIEL']
    ).select_related('eleve__user', 'frais')
    
    # Grouper par élève
    eleves_avec_dettes = {}
    for dette in dettes_impayees:
        eleve_id = dette.eleve.id
        if eleve_id not in eleves_avec_dettes:
            eleves_avec_dettes[eleve_id] = {
                'eleve': dette.eleve,
                'dettes': [],
                'total': 0
            }
        eleves_avec_dettes[eleve_id]['dettes'].append(dette)
        eleves_avec_dettes[eleve_id]['total'] += float(dette.montant_du)
    
    # Envoyer un email à chaque parent
    emails_sent = 0
    for eleve_id, data in eleves_avec_dettes.items():
        eleve = data['eleve']
        total = data['total']
        
        # Récupérer le parent (si lié)
        try:
            from users.models import ParentEleve
            parent_link = ParentEleve.objects.filter(eleve=eleve).first()
            if parent_link and parent_link.parent.user:
                send_email_notification.delay(
                    parent_link.parent.user.id,
                    f"Rappel de paiement - {eleve.prenom} {eleve.nom}",
                    f"Bonjour,\n\n"
                    f"Nous vous informons que votre enfant {eleve.prenom} {eleve.nom} "
                    f"a un solde impayé de {total} FC.\n\n"
                    f"Merci de régulariser cette situation.\n\n"
                    f"Cordialement,\nLe service financier"
                )
                emails_sent += 1
        except Exception as e:
            print(f"Erreur envoi rappel pour élève {eleve_id}: {e}")
    
    return f"{emails_sent} rappels de paiement envoyés"


@shared_task(bind=True)
def generate_invoices_batch(self, eleve_ids):
    """
    Génère les factures pour plusieurs élèves.
    
    Args:
        eleve_ids: Liste des IDs d'élèves
    """
    from finance.services.facture_service import FactureService
    
    generated = 0
    for eleve_id in eleve_ids:
        try:
            FactureService.generate_for_eleve(eleve_id)
            generated += 1
            
            # Mettre à jour la progression
            self.update_state(
                state='PROGRESS',
                meta={'current': generated, 'total': len(eleve_ids)}
            )
        except Exception as e:
            print(f"Erreur génération facture pour élève {eleve_id}: {e}")
    
    return f"{generated}/{len(eleve_ids)} factures générées"


@shared_task
def calculate_monthly_reports():
    """
    Tâche planifiée: Calcule les rapports financiers mensuels.
    
    Exécutée le premier jour de chaque mois.
    """
    from finance.services.finance_services import FinanceService
    from core.models import AnneeAcademique
    
    # Récupérer l'année académique active
    annee = AnneeAcademique.objects.filter(actif=True).first()
    if not annee:
        return "Aucune année académique active"
    
    # Générer le rapport
    rapport = FinanceService.generate_global_report(annee.id)
    
    # Sauvegarder ou envoyer le rapport
    # TODO: Implémenter la sauvegarde/envoi du rapport
    
    return f"Rapport mensuel généré pour {annee.nom}"

@shared_task(bind=True, max_retries=3)
def generate_and_send_facture(self, paiement_id):
    """
    G�n�re la facture d'un paiement et envoie l'email en asynchrone.
    """
    from finance.models import Paiement
    from finance.services.facture_service import FactureService

    paiement = Paiement.objects.select_related("eleve__user").get(id=paiement_id)
    facture = FactureService.create_from_paiement(paiement)
    FactureService.send_invoice(paiement)
    return {"facture_id": facture.id}
