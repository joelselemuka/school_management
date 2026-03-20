"""
Mixins pour filtrage automatique des données selon le rôle de l'utilisateur.

Ces mixins implémentent le principe "l'utilisateur ne voit que ce qu'il doit voir":
- Admin/Staff/Director: tout
- Teacher: ses classes et cours
- Accountant: données financières
- Secretary: données administratives
- Parent: données de ses enfants
- Student: ses propres données
"""

from django.db.models import Q
from common.role_services import RoleService


class RoleBasedQuerysetMixin:
    """
    Mixin pour filtrer automatiquement les querysets selon le rôle.
    
    Usage:
        class MyViewSet(RoleBasedQuerysetMixin, viewsets.ModelViewSet):
            queryset = MyModel.objects.all()
            ...
    """
    
    def get_queryset(self):
        """Filtre le queryset selon le rôle de l'utilisateur."""
        queryset = super().get_queryset()
        user = self.request.user
        
        if not user or not user.is_authenticated:
            return queryset.none()
        
        # Admin, Staff, Director: accès complet
        if user.is_staff or user.is_superuser:
            return queryset
        
        user_groups = list(user.groups.values_list('name', flat=True))

        if any(role in ['STAFF', 'DIRECTOR'] for role in user_groups):
            return queryset

        # Filtrage par rôle réel (fonction du personnel)
        if RoleService.is_teacher(user):
            return self._filter_for_teacher(queryset, user)

        elif RoleService.is_accountant(user):
            return self._filter_for_accountant(queryset, user)

        elif RoleService.is_secretary(user):
            return self._filter_for_secretary(queryset, user)

        elif hasattr(user, 'parent_profile'):
            return self._filter_for_parent(queryset, user)

        elif hasattr(user, 'eleve_profile'):
            return self._filter_for_student(queryset, user)
        
        return queryset.none()
    
    def _filter_for_teacher(self, queryset, user):
        """Filtre pour les enseignants: leurs classes uniquement."""
        # Par défaut, retourner tout (sera affiné dans les ViewSets spécifiques)
        return queryset
    
    def _filter_for_accountant(self, queryset, user):
        """Filtre pour les comptables: données financières uniquement."""
        # Les comptables voient toutes les données financières
        return queryset
    
    def _filter_for_secretary(self, queryset, user):
        """Filtre pour les secrétaires: données administratives."""
        # Les secrétaires voient toutes les données administratives
        return queryset
    
    def _filter_for_parent(self, queryset, user):
        """Filtre pour les parents: données de leurs enfants uniquement."""
        # Par défaut, retourner vide (sera affiné dans les ViewSets spécifiques)
        return queryset.none()
    
    def _filter_for_student(self, queryset, user):
        """Filtre pour les élèves: leurs propres données uniquement."""
        # Par défaut, retourner vide (sera affiné dans les ViewSets spécifiques)
        return queryset.none()


class StudentDataFilterMixin(RoleBasedQuerysetMixin):
    """
    Mixin pour filtrer les données liées aux élèves.
    
    Usage pour modèles avec champ 'eleve':
        class NoteViewSet(StudentDataFilterMixin, viewsets.ModelViewSet):
            queryset = Note.objects.all()
    """
    
    def _filter_for_teacher(self, queryset, user):
        """Enseignants: élèves de leurs classes."""
        if not RoleService.is_teacher(user):
            return queryset.none()

        from academics.models import AffectationEnseignant
        from admission.models import Inscription

        # Classes où l'enseignant enseigne
        teacher_classes = AffectationEnseignant.objects.filter(
            teacher=user.personnel_profile
        ).values_list('cours__classe', flat=True)

        # Élèves inscrits dans ces classes
        eleves = Inscription.objects.filter(
            classe_id__in=teacher_classes
        ).values_list('eleve_id', flat=True)

        return queryset.filter(eleve_id__in=eleves)
    
    def _filter_for_parent(self, queryset, user):
        """Parents: données de leurs enfants."""
        if hasattr(user, 'parent_profile'):
            from users.models import ParentEleve
            
            enfants_ids = ParentEleve.objects.filter(
                parent=user.parent_profile
            ).values_list('eleve_id', flat=True)
            
            queryset = queryset.filter(eleve_id__in=enfants_ids)
            
            # Filtrer par données publiées si applicable
            if hasattr(queryset.model, 'published'):
                queryset = queryset.filter(published=True)
            
            return queryset
        
        return queryset.none()
    
    def _filter_for_student(self, queryset, user):
        """Élèves: leurs propres données."""
        if hasattr(user, 'eleve_profile'):
            queryset = queryset.filter(eleve=user.eleve_profile)
            
            # Filtrer par données publiées si applicable
            if hasattr(queryset.model, 'published'):
                queryset = queryset.filter(published=True)
            
            return queryset
        
        return queryset.none()


class ClassDataFilterMixin(RoleBasedQuerysetMixin):
    """
    Mixin pour filtrer les données liées aux classes.
    
    Usage pour modèles avec champ 'classe':
        class InscriptionViewSet(ClassDataFilterMixin, viewsets.ModelViewSet):
            queryset = Inscription.objects.all()
    """
    
    def _filter_for_teacher(self, queryset, user):
        """Enseignants: leurs classes."""
        if not RoleService.is_teacher(user):
            return queryset.none()

        from academics.models import AffectationEnseignant

        teacher_classes = AffectationEnseignant.objects.filter(
            teacher=user.personnel_profile
        ).values_list('cours__classe', flat=True)

        return queryset.filter(classe_id__in=teacher_classes)
    
    def _filter_for_parent(self, queryset, user):
        """Parents: classes de leurs enfants."""
        if hasattr(user, 'parent_profile'):
            from users.models import ParentEleve
            from admission.models import Inscription
            
            enfants_ids = ParentEleve.objects.filter(
                parent=user.parent_profile
            ).values_list('eleve_id', flat=True)
            
            classes_ids = Inscription.objects.filter(
                eleve_id__in=enfants_ids
            ).values_list('classe_id', flat=True)
            
            return queryset.filter(id__in=classes_ids)
        
        return queryset.none()
    
    def _filter_for_student(self, queryset, user):
        """Élèves: leur classe."""
        if hasattr(user, 'eleve_profile'):
            from admission.models import Inscription
            
            inscription = Inscription.objects.filter(
                eleve=user.eleve_profile
            ).order_by('-date_inscription').first()
            
            if inscription:
                return queryset.filter(id=inscription.classe_id)
        
        return queryset.none()


class FinanceDataFilterMixin(RoleBasedQuerysetMixin):
    """
    Mixin pour filtrer les données financières.
    
    Usage:
        class PaiementViewSet(FinanceDataFilterMixin, viewsets.ModelViewSet):
            queryset = Paiement.objects.all()
    """
    
    def _filter_for_accountant(self, queryset, user):
        """Comptables: toutes les données financières."""
        return queryset
    
    def _filter_for_secretary(self, queryset, user):
        """Secrétaires: toutes les données financières (lecture seule via permissions)."""
        return queryset
    
    def _filter_for_parent(self, queryset, user):
        """Parents: données financières de leurs enfants."""
        if hasattr(user, 'parent_profile'):
            from users.models import ParentEleve
            
            enfants_ids = ParentEleve.objects.filter(
                parent=user.parent_profile
            ).values_list('eleve_id', flat=True)
            
            return queryset.filter(eleve_id__in=enfants_ids)
        
        return queryset.none()
    
    def _filter_for_student(self, queryset, user):
        """Élèves: leurs propres données financières."""
        if hasattr(user, 'eleve_profile'):
            return queryset.filter(eleve=user.eleve_profile)
        
        return queryset.none()


class AttendanceDataFilterMixin(RoleBasedQuerysetMixin):
    """
    Mixin pour filtrer les données de présence.
    
    Usage:
        class PresenceViewSet(AttendanceDataFilterMixin, viewsets.ModelViewSet):
            queryset = Presence.objects.all()
    """
    
    def _filter_for_teacher(self, queryset, user):
        """Enseignants: présences de leurs cours."""
        if not RoleService.is_teacher(user):
            return queryset.none()

        from academics.models import AffectationEnseignant
        from attendance.models import SeanceCours

        # Cours de l'enseignant
        teacher_courses = AffectationEnseignant.objects.filter(
            teacher=user.personnel_profile
        ).values_list('cours_id', flat=True)

        # Séances de ces cours
        seances = SeanceCours.objects.filter(
            cours_id__in=teacher_courses
        ).values_list('id', flat=True)

        return queryset.filter(seance_id__in=seances)
    
    def _filter_for_secretary(self, queryset, user):
        """Secrétaires: toutes les présences."""
        return queryset
    
    def _filter_for_parent(self, queryset, user):
        """Parents: présences de leurs enfants."""
        if hasattr(user, 'parent_profile'):
            from users.models import ParentEleve
            
            enfants_ids = ParentEleve.objects.filter(
                parent=user.parent_profile
            ).values_list('eleve_id', flat=True)
            
            return queryset.filter(eleve_id__in=enfants_ids)
        
        return queryset.none()
    
    def _filter_for_student(self, queryset, user):
        """Élèves: leurs propres présences."""
        if hasattr(user, 'eleve_profile'):
            return queryset.filter(eleve=user.eleve_profile)
        
        return queryset.none()


class EvaluationDataFilterMixin(RoleBasedQuerysetMixin):
    """
    Mixin pour filtrer les évaluations et notes.
    
    Usage:
        class NoteViewSet(EvaluationDataFilterMixin, viewsets.ModelViewSet):
            queryset = Note.objects.all()
    """
    
    def _filter_for_teacher(self, queryset, user):
        """Enseignants: évaluations de leurs cours."""
        if not RoleService.is_teacher(user):
            return queryset.none()

        from academics.models import AffectationEnseignant, Evaluation

        # Cours de l'enseignant
        teacher_courses = AffectationEnseignant.objects.filter(
            teacher=user.personnel_profile
        ).values_list('cours_id', flat=True)

        # Si le modèle est Note
        if queryset.model.__name__ == 'Note':
            # Évaluations de ces cours
            evaluations = Evaluation.objects.filter(
                cours_id__in=teacher_courses
            ).values_list('id', flat=True)

            return queryset.filter(evaluation_id__in=evaluations)

        # Si le modèle est Evaluation
        elif queryset.model.__name__ == 'Evaluation':
            return queryset.filter(cours_id__in=teacher_courses)

        return queryset.none()
    
    def _filter_for_parent(self, queryset, user):
        """Parents: notes de leurs enfants (publiées uniquement)."""
        if hasattr(user, 'parent_profile'):
            from users.models import ParentEleve
            
            enfants_ids = ParentEleve.objects.filter(
                parent=user.parent_profile
            ).values_list('eleve_id', flat=True)
            
            # Filtrer par élève
            if queryset.model.__name__ == 'Note':
                queryset = queryset.filter(
                    eleve_id__in=enfants_ids,
                    evaluation__published=True  # Seulement les évaluations publiées
                )
            elif queryset.model.__name__ == 'Evaluation':
                # Parents voient les évaluations où leurs enfants ont des notes
                queryset = queryset.filter(
                    notes__eleve_id__in=enfants_ids,
                    published=True
                ).distinct()
            
            return queryset
        
        return queryset.none()
    
    def _filter_for_student(self, queryset, user):
        """Élèves: leurs propres notes (publiées uniquement)."""
        if hasattr(user, 'eleve_profile'):
            # Filtrer par élève
            if queryset.model.__name__ == 'Note':
                queryset = queryset.filter(
                    eleve=user.eleve_profile,
                    evaluation__published=True
                )
            elif queryset.model.__name__ == 'Evaluation':
                # Élèves voient les évaluations où ils ont des notes
                queryset = queryset.filter(
                    notes__eleve=user.eleve_profile,
                    published=True
                ).distinct()
            
            return queryset
        
        return queryset.none()


class AdmissionDataFilterMixin(RoleBasedQuerysetMixin):
    """
    Mixin pour filtrer les données d'admission et inscription.
    
    Usage:
        class InscriptionViewSet(AdmissionDataFilterMixin, viewsets.ModelViewSet):
            queryset = Inscription.objects.all()
    """
    
    def _filter_for_secretary(self, queryset, user):
        """Secrétaires: toutes les admissions/inscriptions."""
        return queryset
    
    def _filter_for_parent(self, queryset, user):
        """Parents: admissions/inscriptions de leurs enfants."""
        if hasattr(user, 'parent'):
            from users.models import ParentEleve
            
            # Si le modèle est AdmissionApplication
            if queryset.model.__name__ == 'AdmissionApplication':
                # Filtrer par email du parent (les demandes en ligne)
                return queryset.filter(
                    guardians__parent_email=user.email
                ).distinct()
            
            # Si le modèle est Inscription
            elif queryset.model.__name__ == 'Inscription':
                enfants_ids = ParentEleve.objects.filter(
                    parent=user.parent_profile
                ).values_list('eleve_id', flat=True)
                
                return queryset.filter(eleve_id__in=enfants_ids)
        
        return queryset.none()
    
    def _filter_for_student(self, queryset, user):
        """Élèves: leurs propres inscriptions."""
        if hasattr(user, 'eleve'):
            if queryset.model.__name__ == 'Inscription':
                return queryset.filter(eleve=user.eleve_profile)
        
        return queryset.none()


class PublicDataMixin:
    """
    Mixin pour les données publiques accessibles à tous.
    
    Usage pour les annonces, calendrier, etc.:
        class AnnonceViewSet(PublicDataMixin, viewsets.ModelViewSet):
            queryset = Annonce.objects.all()
    """
    
    def get_queryset(self):
        """Retourne toutes les données publiques."""
        queryset = super().get_queryset()
        
        # Filtrer par is_public si le champ existe
        if hasattr(queryset.model, 'is_public'):
            queryset = queryset.filter(is_public=True)
        
        return queryset


class AuditLogFilterMixin(RoleBasedQuerysetMixin):
    """
    Mixin spécial pour les logs d'audit.
    
    Usage:
        class AuditLogViewSet(AuditLogFilterMixin, viewsets.ReadOnlyModelViewSet):
            queryset = AuditLog.objects.all()
    """
    
    def _filter_for_teacher(self, queryset, user):
        """Enseignants: leurs propres actions."""
        return queryset.filter(user=user)
    
    def _filter_for_accountant(self, queryset, user):
        """Comptables: leurs propres actions."""
        return queryset.filter(user=user)
    
    def _filter_for_secretary(self, queryset, user):
        """Secrétaires: leurs propres actions."""
        return queryset.filter(user=user)
    
    def _filter_for_parent(self, queryset, user):
        """Parents: aucun accès aux logs."""
        return queryset.none()
    
    def _filter_for_student(self, queryset, user):
        """Élèves: aucun accès aux logs."""
        return queryset.none()

