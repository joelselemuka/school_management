"""
Système de permissions RBAC (Role-Based Access Control).

Ce module implémente les permissions granulaires basées sur les rôles
selon la matrice RBAC définie dans la documentation.
"""

from rest_framework.permissions import BasePermission, SAFE_METHODS
from django.contrib.auth import get_user_model
from common.role_services import RoleService

User = get_user_model()


class IsAdmin(BasePermission):
    """Permission: Administrateur uniquement."""
    
    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated and request.user.is_staff


class IsAdminUser(BasePermission):
    """Permission: Utilisateur administrateur (alias pour IsAdmin)."""
    
    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated and request.user.is_staff


class IsDirector(BasePermission):
    """Permission: Directeur uniquement."""
    
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        
        user_groups = request.user.groups.values_list('name', flat=True)
        return 'DIRECTOR' in user_groups or request.user.is_staff


class IsStaffOrDirector(BasePermission):
    """Permission: Staff ou Directeur."""
    
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        
        user_groups = request.user.groups.values_list('name', flat=True)
        return any(group in ['STAFF', 'DIRECTOR', 'ADMIN'] for group in user_groups)


class IsTeacher(BasePermission):
    """Permission: Enseignant."""
    
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        
        return 'TEACHER' in request.user.groups.values_list('name', flat=True)


class IsAccountant(BasePermission):
    """Permission: Comptable."""
    
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        
        return 'ACCOUNTANT' in request.user.groups.values_list('name', flat=True)


class IsSecretary(BasePermission):
    """Permission: Secrétaire."""
    
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        
        return 'SECRETARY' in request.user.groups.values_list('name', flat=True)


class IsParent(BasePermission):
    """Permission: Parent."""
    
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        
        return hasattr(request.user, 'parent')


class IsStudent(BasePermission):
    """Permission: Élève."""
    
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        
        return hasattr(request.user, 'eleve')


class HasRBACPermission(BasePermission):
    """
    Permission RBAC générique basée sur le rôle et l'action.
    
    Cette permission vérifie:
    1. L'utilisateur est authentifié
    2. L'utilisateur a le rôle approprié pour l'action
    3. Les conditions spéciales (propriété, hiérarchie, etc.)
    """
    
    # Mapping des méthodes HTTP vers actions RBAC
    ACTION_MAP = {
        'GET': 'read',
        'POST': 'create',
        'PUT': 'update',
        'PATCH': 'update',
        'DELETE': 'delete',
    }
    
    # Rôles avec accès complet (admin, staff, director)
    FULL_ACCESS_ROLES = ['ADMIN', 'STAFF', 'DIRECTOR']
    
    def has_permission(self, request, view):
        """Vérifie la permission au niveau de la vue."""
        if not request.user or not request.user.is_authenticated:
            return False
        
        # Les admins ont toujours accès
        if request.user.is_staff or request.user.is_superuser:
            return True
        
        user_groups = list(request.user.groups.values_list('name', flat=True))
        
        # Staff et Director ont accès complet
        if any(role in self.FULL_ACCESS_ROLES for role in user_groups):
            return True
        
        # Pour les autres rôles, vérification dans has_object_permission
        return True
    
    def has_object_permission(self, request, view, obj):
        """Vérifie la permission au niveau de l'objet."""
        if not request.user or not request.user.is_authenticated:
            return False
        
        # Les admins ont toujours accès
        if request.user.is_staff or request.user.is_superuser:
            return True
        
        user_groups = list(request.user.groups.values_list('name', flat=True))
        
        # Staff et Director ont accès complet
        if any(role in self.FULL_ACCESS_ROLES for role in user_groups):
            return True
        
        action = self.ACTION_MAP.get(request.method, 'read')
        
        # Vérifications spécifiques par rôle
        if 'TEACHER' in user_groups:
            return self._check_teacher_permission(request.user, action, obj)
        
        elif 'ACCOUNTANT' in user_groups:
            return self._check_accountant_permission(request.user, action, obj)
        
        elif 'SECRETARY' in user_groups:
            return self._check_secretary_permission(request.user, action, obj)
        
        elif hasattr(request.user, 'parent'):
            return self._check_parent_permission(request.user, action, obj)
        
        elif hasattr(request.user, 'eleve'):
            return self._check_student_permission(request.user, action, obj)
        
        return False
    
    def _check_teacher_permission(self, user, action, obj):
        """Vérifie les permissions pour un enseignant."""
        # Enseignants peuvent lire/modifier les données de leurs classes
        if action in ['read', 'update']:
            # Vérifier si l'objet est lié à une classe de l'enseignant
            if hasattr(obj, 'classe'):
                from academics.models import AffectationEnseignant
                return AffectationEnseignant.objects.filter(
                    teacher=user.personnel if hasattr(user, 'personnel') else None,
                    cours__classe=obj.classe
                ).exists()
            
            # Pour les notes et évaluations
            if hasattr(obj, 'evaluation'):
                from academics.models import AffectationEnseignant
                return AffectationEnseignant.objects.filter(
                    teacher=user.personnel if hasattr(user, 'personnel') else None,
                    cours=obj.evaluation.cours
                ).exists()
        
        return False
    
    def _check_accountant_permission(self, user, action, obj):
        """Vérifie les permissions pour un comptable."""
        # Comptables ont accès aux données financières
        financial_models = ['Frais', 'Paiement', 'DetteEleve', 'Facture', 'CompteEleve']
        return obj.__class__.__name__ in financial_models
    
    def _check_secretary_permission(self, user, action, obj):
        """Vérifie les permissions pour un secrétaire."""
        # Secrétaires ont accès aux données administratives
        admin_models = ['Inscription', 'AdmissionApplication', 'Classe', 'Horaire']
        return obj.__class__.__name__ in admin_models
    
    def _check_parent_permission(self, user, action, obj):
        """Vérifie les permissions pour un parent."""
        # Parents peuvent seulement lire (read)
        if action != 'read':
            return False
        
        # Vérifier si l'objet concerne un de leurs enfants
        if hasattr(obj, 'eleve'):
            from users.models import ParentEleve
            return ParentEleve.objects.filter(
                parent=user.parent,
                eleve=obj.eleve
            ).exists()
        
        # Pour les classes, vérifier si un de leurs enfants y est inscrit
        if obj.__class__.__name__ == 'Classe':
            from users.models import ParentEleve
            from admission.models import Inscription
            enfants_ids = ParentEleve.objects.filter(
                parent=user.parent
            ).values_list('eleve_id', flat=True)
            
            return Inscription.objects.filter(
                eleve_id__in=enfants_ids,
                classe=obj
            ).exists()
        
        # Pour les données publiées (notes, bulletins)
        if hasattr(obj, 'published'):
            if not obj.published:
                return False
        
        return False
    
    def _check_student_permission(self, user, action, obj):
        """Vérifie les permissions pour un élève."""
        # Élèves peuvent seulement lire (read)
        if action != 'read':
            return False
        
        # Vérifier si l'objet les concerne directement
        if hasattr(obj, 'eleve'):
            if obj.eleve != user.eleve:
                return False
        
        # Pour les classes
        if obj.__class__.__name__ == 'Classe':
            from admission.models import Inscription
            return Inscription.objects.filter(
                eleve=user.eleve,
                classe=obj
            ).exists()
        
        # Pour les données publiées (notes, bulletins)
        if hasattr(obj, 'published'):
            if not obj.published:
                return False
        
        return True


class CanManageFinance(BasePermission):
    """Permission: Gestion financière (Admin, Staff, Director, Accountant)."""
    
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        
        if request.user.is_staff or request.user.is_superuser:
            return True

        # Parents et élèves: lecture seule de leurs propres données financières
        if request.method in SAFE_METHODS:
            if hasattr(request.user, 'parent') or hasattr(request.user, 'eleve'):
                return True
        
        user_groups = request.user.groups.values_list('name', flat=True)
        return any(group in ['DIRECTOR', 'ACCOUNTANT'] for group in user_groups)


class CanManagePayroll(BasePermission):
    """Permission: Gestion de la paie (Admin, Staff, Director, Accountant, DRH)."""

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False

        if request.user.is_staff or request.user.is_superuser:
            return True

        user_groups = request.user.groups.values_list("name", flat=True)
        if any(group in ["DIRECTOR", "STAFF", "ADMIN", "ACCOUNTANT", "DRH"] for group in user_groups):
            return True

        if RoleService.is_accountant(request.user):
            return True

        if RoleService.is_personnel(request.user):
            return request.user.personnel_profile.fonction == "drh"

        return False


class CanManageAdmissions(BasePermission):
    """Permission: Gestion des admissions (Admin, Staff, Director, Secretary)."""
    
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        
        if request.user.is_staff or request.user.is_superuser:
            return True
        
        user_groups = request.user.groups.values_list('name', flat=True)
        return any(group in ['DIRECTOR', 'SECRETARY'] for group in user_groups)


class CanManageAttendance(BasePermission):
    """Permission: Gestion des présences (Admin, Staff, Director, Teacher)."""
    
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        
        if request.user.is_staff or request.user.is_superuser:
            return True
        
        user_groups = request.user.groups.values_list('name', flat=True)
        return any(group in ['STAFF', 'DIRECTOR', 'TEACHER'] for group in user_groups)


class CanManageGrades(BasePermission):
    """Permission: Gestion des notes (Admin, Staff, Director, Teacher)."""
    
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        
        if request.user.is_staff or request.user.is_superuser:
            return True
        
        user_groups = request.user.groups.values_list('name', flat=True)
        return any(group in ['STAFF', 'DIRECTOR', 'TEACHER'] for group in user_groups)


class IsOwnerOrReadOnly(BasePermission):
    """
    Permission: Propriétaire peut modifier, autres peuvent seulement lire.
    Utilisé pour les profils utilisateurs.
    """
    
    def has_object_permission(self, request, view, obj):
        # Lecture autorisée pour tous
        if request.method in ['GET', 'HEAD', 'OPTIONS']:
            return True
        
        # Écriture autorisée seulement pour le propriétaire
        if hasattr(obj, 'user'):
            return obj.user == request.user
        
        return obj == request.user


class IsOwnProfileOrAdmin(BasePermission):
    """
    Permission: Utilisateur peut modifier son propre profil, admin peut tout modifier.
    """
    
    def has_object_permission(self, request, view, obj):
        # Admins ont accès complet
        if request.user.is_staff or request.user.is_superuser:
            return True
        
        # Utilisateur peut modifier son propre profil
        if hasattr(obj, 'user'):
            return obj.user == request.user
        
        return obj == request.user

class CanManageLibrary(BasePermission):
    """Permission: Gestion de la bibliothèque (Admin, Staff, Director, Bibliothécaire)."""
    
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
            
        if request.user.is_staff or request.user.is_superuser:
            return True
            
        user_groups = request.user.groups.values_list('name', flat=True)
        if any(group in ['DIRECTOR', 'STAFF', 'ADMIN'] for group in user_groups):
            return True
            
        if RoleService.is_librarian(request.user):
            return True
            
        return False


class CanManageTransport(BasePermission):
    """Permission: Gestion du transport scolaire (Admin, Staff, Director, Responsable Transport)."""
    
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
            
        if request.user.is_staff or request.user.is_superuser:
            return True
            
        user_groups = request.user.groups.values_list('name', flat=True)
        if any(group in ['DIRECTOR', 'STAFF', 'ADMIN'] for group in user_groups):
            return True
            
        if RoleService.is_transport_manager(request.user):
            return True
            
        return False


class IsDriver(BasePermission):
    """Permission: Chauffeur uniquement."""
    
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
            
        if RoleService.is_driver(request.user):
            return True
            
        return False
