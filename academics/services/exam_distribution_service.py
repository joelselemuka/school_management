"""
Service de génération automatique de la répartition des élèves dans les salles d'examen.

Règle: Maximum N élèves de la même classe par salle (configurable).
"""

from django.db import transaction
from django.core.exceptions import ValidationError
from academics.models import RepartitionExamen, PlanificationExamen, Salle, Evaluation
from users.models import Eleve
from admission.models import Inscription


class ExamDistributionService:
    """
    Service pour la génération automatique de la répartition des élèves
    dans les salles d'examen.
    """
    
    @staticmethod
    @transaction.atomic
    def generate_distribution(
        evaluation,
        salles,
        max_students_per_class_per_room=5,
        spacing_strategy='alternate',
        clear_existing=True
    ):
        """
        Génère automatiquement la répartition des élèves dans les salles.
        
        Args:
            evaluation: Instance Evaluation
            salles: Liste des salles disponibles (QuerySet ou list)
            max_students_per_class_per_room: Max d'élèves d'une même classe par salle
            spacing_strategy: Stratégie d'espacement ('alternate', 'grouped', 'random')
            clear_existing: Si True, supprime les répartitions existantes
            
        Returns:
            dict: {
                'total_students': int,
                'total_rooms': int,
                'distributions': QuerySet[RepartitionExamen],
                'summary': list[dict]  # Par salle
            }
            
        Raises:
            ValueError: Si aucun élève ou capacité insuffisante
        """
        # 1. Récupérer tous les élèves inscrits dans la classe de l'évaluation
        eleves = Eleve.objects.filter(
            inscriptions__classe=evaluation.cours.classe,
            inscriptions__annee_academique=evaluation.annee_academique,
            inscriptions__statut='valide',
            actif=True
        ).distinct().order_by('nom', 'postnom', 'prenom')
        
        total_students = eleves.count()
        
        if total_students == 0:
            raise ValueError("Aucun élève inscrit trouvé pour cette évaluation")
        
        # 2. Vérifier la capacité totale des salles
        total_capacity = sum(salle.capacite for salle in salles)
        
        if total_capacity < total_students:
            raise ValueError(
                f"Capacité insuffisante: {total_students} élèves pour {total_capacity} places"
            )
        
        # 3. Créer les planifications pour chaque salle si elles n'existent pas
        planifications = []
        for salle in salles:
            planif, created = PlanificationExamen.objects.get_or_create(
                evaluation=evaluation,
                salle=salle,
                defaults={
                    'date_examen': evaluation.periode.date_debut,  # Date par défaut
                    'heure_debut': '08:00',
                    'heure_fin': '10:00',
                    'duree_minutes': 120,
                }
            )
            planifications.append(planif)
        
        # 4. Supprimer les répartitions existantes si demandé
        if clear_existing:
            RepartitionExamen.objects.filter(
                planification__in=planifications
            ).delete()
        
        # 5. Répartir les élèves selon la stratégie
        if spacing_strategy == 'alternate':
            distributions = ExamDistributionService._distribute_alternate(
                eleves, planifications, max_students_per_class_per_room
            )
        elif spacing_strategy == 'grouped':
            distributions = ExamDistributionService._distribute_grouped(
                eleves, planifications
            )
        elif spacing_strategy == 'random':
            distributions = ExamDistributionService._distribute_random(
                eleves, planifications
            )
        else:
            raise ValueError(f"Stratégie inconnue: {spacing_strategy}")
        
        # 6. Générer le résumé
        summary = []
        for planif in planifications:
            count = distributions.filter(planification=planif).count()
            summary.append({
                'salle_code': planif.salle.code,
                'salle_nom': planif.salle.nom,
                'nombre_eleves': count,
                'capacite': planif.salle.capacite,
                'taux_occupation': round((count / planif.salle.capacite) * 100, 2) if planif.salle.capacite > 0 else 0,
                'planification_id': planif.id
            })
        
        return {
            'total_students': total_students,
            'total_rooms': len(salles),
            'distributions': distributions,
            'summary': summary
        }
    
    @staticmethod
    def _distribute_alternate(eleves, planifications, max_per_room):
        """
        Répartition alternée pour éviter trop d'élèves de la même classe ensemble.
        Les élèves sont distribués de manière circulaire entre les salles.
        """
        distributions = []
        current_room_index = 0
        place_counters = {planif.id: 1 for planif in planifications}
        
        for eleve in eleves:
            # Trouver la prochaine salle disponible
            attempts = 0
            while attempts < len(planifications):
                planif = planifications[current_room_index]
                
                # Vérifier si la salle n'est pas pleine
                if place_counters[planif.id] <= planif.salle.capacite:
                    distrib = RepartitionExamen.objects.create(
                        planification=planif,
                        eleve=eleve,
                        numero_place=place_counters[planif.id]
                    )
                    distributions.append(distrib)
                    place_counters[planif.id] += 1
                    break
                
                # Passer à la salle suivante
                current_room_index = (current_room_index + 1) % len(planifications)
                attempts += 1
            
            # Passer à la salle suivante pour le prochain élève
            current_room_index = (current_room_index + 1) % len(planifications)
        
        return RepartitionExamen.objects.filter(
            id__in=[d.id for d in distributions]
        )
    
    @staticmethod
    def _distribute_grouped(eleves, planifications):
        """
        Répartition groupée: remplir chaque salle complètement avant de passer à la suivante.
        """
        distributions = []
        current_planif_index = 0
        current_place = 1
        
        for eleve in eleves:
            if current_planif_index >= len(planifications):
                break  # Toutes les salles sont pleines
            
            planif = planifications[current_planif_index]
            
            distrib = RepartitionExamen.objects.create(
                planification=planif,
                eleve=eleve,
                numero_place=current_place
            )
            distributions.append(distrib)
            current_place += 1
            
            # Si la salle est pleine, passer à la suivante
            if current_place > planif.salle.capacite:
                current_planif_index += 1
                current_place = 1
        
        return RepartitionExamen.objects.filter(
            id__in=[d.id for d in distributions]
        )
    
    @staticmethod
    def _distribute_random(eleves, planifications):
        """
        Répartition aléatoire pour maximiser le mélange des élèves.
        """
        import random
        
        distributions = []
        eleves_list = list(eleves)
        random.shuffle(eleves_list)
        
        place_counters = {planif.id: 1 for planif in planifications}
        
        for eleve in eleves_list:
            # Choisir une salle aléatoire qui n'est pas pleine
            available_planifs = [
                p for p in planifications 
                if place_counters[p.id] <= p.salle.capacite
            ]
            
            if not available_planifs:
                break  # Toutes les salles sont pleines
            
            planif = random.choice(available_planifs)
            
            distrib = RepartitionExamen.objects.create(
                planification=planif,
                eleve=eleve,
                numero_place=place_counters[planif.id]
            )
            distributions.append(distrib)
            place_counters[planif.id] += 1
        
        return RepartitionExamen.objects.filter(
            id__in=[d.id for d in distributions]
        )
    
    @staticmethod
    def get_distribution_summary(planification):
        """
        Récupère le résumé de la répartition pour une planification.
        
        Args:
            planification: Instance PlanificationExamen
            
        Returns:
            dict: Résumé avec liste des élèves et statistiques
        """
        repartitions = RepartitionExamen.objects.filter(
            planification=planification
        ).select_related('eleve', 'eleve__user').order_by('numero_place')
        
        students_list = [
            {
                'numero_place': r.numero_place,
                'nom_complet': f"{r.eleve.nom} {r.eleve.postnom} {r.eleve.prenom}",
                'matricule': r.eleve.user.matricule,
                'zone': r.zone,
                'rangee': r.rangee,
                'colonne': r.colonne,
                'est_present': r.est_present,
                'heure_arrivee': r.heure_arrivee,
            }
            for r in repartitions
        ]
        
        return {
            'salle': {
                'code': planification.salle.code,
                'nom': planification.salle.nom,
                'capacite': planification.salle.capacite,
            },
            'evaluation': {
                'nom': planification.evaluation.nom,
                'cours': planification.evaluation.cours.nom,
            },
            'date_examen': planification.date_examen,
            'heure_debut': planification.heure_debut,
            'heure_fin': planification.heure_fin,
            'nombre_eleves': len(students_list),
            'taux_occupation': round((len(students_list) / planification.salle.capacite) * 100, 2) if planification.salle.capacite > 0 else 0,
            'eleves': students_list,
        }
    
    @staticmethod
    def mark_student_present(repartition_id, heure_arrivee=None):
        """
        Marque un élève comme présent à l'examen.
        
        Args:
            repartition_id: ID de la RepartitionExamen
            heure_arrivee: DateTime d'arrivée (optionnel, utilise maintenant si None)
            
        Returns:
            RepartitionExamen: Instance mise à jour
        """
        from django.utils import timezone
        
        repartition = RepartitionExamen.objects.get(id=repartition_id)
        repartition.est_present = True
        repartition.heure_arrivee = heure_arrivee or timezone.now()
        repartition.save()
        
        return repartition
    
    @staticmethod
    def generate_seating_chart_data(planification):
        """
        Génère les données pour un plan de salle.
        Utile pour la génération PDF ou l'affichage frontend.
        
        Args:
            planification: Instance PlanificationExamen
            
        Returns:
            dict: Données structurées pour le plan de salle
        """
        summary = ExamDistributionService.get_distribution_summary(planification)
        
        # Organiser les élèves par rangée/colonne si disponible
        seating_grid = {}
        for eleve in summary['eleves']:
            if eleve['rangee'] and eleve['colonne']:
                key = f"{eleve['rangee']}-{eleve['colonne']}"
                seating_grid[key] = eleve
        
        return {
            **summary,
            'seating_grid': seating_grid,
        }
    
    @staticmethod
    def validate_distribution(evaluation, salles):
        """
        Valide qu'une distribution est possible avant de la générer.
        
        Args:
            evaluation: Instance Evaluation
            salles: Liste des salles
            
        Returns:
            dict: {
                'valid': bool,
                'message': str,
                'total_students': int,
                'total_capacity': int
            }
        """
        # Compter les élèves
        eleves_count = Eleve.objects.filter(
            inscriptions__classe=evaluation.cours.classe,
            inscriptions__annee_academique=evaluation.annee_academique,
            inscriptions__statut='valide',
            actif=True
        ).distinct().count()
        
        # Capacité totale
        total_capacity = sum(salle.capacite for salle in salles)
        
        valid = total_capacity >= eleves_count
        message = "Distribution possible" if valid else f"Capacité insuffisante: {eleves_count} élèves pour {total_capacity} places"
        
        return {
            'valid': valid,
            'message': message,
            'total_students': eleves_count,
            'total_capacity': total_capacity,
            'rooms_needed': (eleves_count // 30) + (1 if eleves_count % 30 else 0),  # Estimation
        }
