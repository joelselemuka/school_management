"""
ViewSets pour la gestion des présences, horaires et configurations.

Nouveaux ViewSets:
  - HoraireViewSet: ajout actions generate_for_classe, generate_all, time_slots
  - ClasseHoraireConfigViewSet: CRUD config max-heures par classe
  - HoraireEnseignantViewSet: lecture + génération horaires enseignants

Actions:
  POST /horaires/generate_for_classe/?classe_id=X   → régénère une classe
  POST /horaires/generate_all/                       → génère toutes les classes
  GET  /horaires/time_slots/                         → plages horaires calculées
  GET  /horaires/conflicts/                          → détection de conflits

  POST /horaires-enseignants/generate/               → génère horaires profs
  GET  /horaires-enseignants/by_enseignant/?id=X     → horaire d'un prof
  GET  /horaires-enseignants/weekly_summary/?id=X    → résumé hebdomadaire
"""

from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.db.models import Q, Count
from django.utils import timezone

from attendance.models import (
    HoraireCours, Presence, SeanceCours,
    ClasseHoraireConfig, HoraireEnseignant,
)
from attendance.serializers import (
    HoraireSerializer, PresenceSerializer, SeanceSerializer,
    ClasseHoraireConfigSerializer, HoraireEnseignantSerializer,
)
from attendance.services.presence_service import PresenceService
from attendance.services.statistics_service import AttendanceStatisticsService
from attendance.services.horaire_generation_service import HoraireGenerationService
from attendance.services.teacher_schedule_service import TeacherScheduleService
from attendance.services.schedule_config_service import ScheduleConfigService
from common.models import AuditLog
from common.permissions import CanManageAttendance, IsStaffOrDirector
from common.mixins import AttendanceDataFilterMixin, RoleBasedQuerysetMixin


# ─────────────────────────────────────────────────────────────────────────────
# HORAIRES DE COURS
# ─────────────────────────────────────────────────────────────────────────────

class HoraireViewSet(RoleBasedQuerysetMixin, viewsets.ModelViewSet):
    """
    ViewSet pour la gestion des horaires de cours.

    Actions:
    - list, create, retrieve, update, destroy
    - by_classe: horaires d'une classe
    - by_enseignant: horaires d'un enseignant
    - conflicts: détecte les conflits d'horaire
    - generate_for_classe: génère (ou régénère) l'horaire d'une classe
    - generate_all: génère les horaires pour toutes les classes
    - time_slots: retourne les plages horaires calculées depuis la config école
    """

    queryset = HoraireCours.objects.all()
    serializer_class = HoraireSerializer
    permission_classes = [CanManageAttendance]
    filterset_fields = ['classe', 'cours', 'jour', 'actif', 'numero_heure']
    ordering = ['jour', 'numero_heure', 'heure_debut']

    def get_queryset(self):
        return super().get_queryset().select_related(
            'classe', 'cours', 'annee_academique'
        )

    def perform_create(self, serializer):
        horaire = serializer.save()
        AuditLog.log(
            user=self.request.user,
            action='create',
            description=f'Création horaire: {horaire.cours.nom} - {horaire.jour} H{horaire.numero_heure}',
            content_object=horaire,
            request=self.request
        )

    # ── Actions de lecture ────────────────────────────────────────────────────

    @action(detail=False, methods=['get'])
    def by_classe(self, request):
        """Horaires d'une classe groupés par jour."""
        classe_id = request.query_params.get('classe_id')
        if not classe_id:
            return Response({'error': 'classe_id requis'}, status=400)

        horaires = self.get_queryset().filter(
            classe_id=classe_id, actif=True
        ).order_by('jour', 'numero_heure')
        serializer = self.get_serializer(horaires, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def by_enseignant(self, request):
        """Horaires d'un enseignant (via ses affectations)."""
        enseignant_id = request.query_params.get('enseignant_id')
        if not enseignant_id:
            return Response({'error': 'enseignant_id requis'}, status=400)

        horaires = self.get_queryset().filter(
            cours__affectations__teacher_id=enseignant_id,
            actif=True
        ).distinct().order_by('jour', 'numero_heure')
        serializer = self.get_serializer(horaires, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def time_slots(self, request):
        """
        Retourne les plages horaires calculées depuis la config de l'école.

        Query params:
            nb_heures (int, défaut=8): nombre d'heures à calculer
        """
        try:
            nb_heures = int(request.query_params.get('nb_heures', 8))
            nb_heures = max(1, min(nb_heures, 12))
            slots = ScheduleConfigService.get_slots_as_schedule_display(nb_heures=nb_heures)
            return Response({'nb_heures': nb_heures, 'slots': slots})
        except Exception as e:
            return Response({'error': str(e)}, status=400)

    @action(detail=False, methods=['get'])
    def conflicts(self, request):
        """Détecte les conflits d'horaire (même classe, même jour, même heure)."""
        classe_id = request.query_params.get('classe_id')
        annee_id = request.query_params.get('annee_academique_id')

        try:
            from academics.models import Classe
            from core.models import AnneeAcademique

            classe = Classe.objects.get(pk=classe_id) if classe_id else None
            annee = AnneeAcademique.objects.get(pk=annee_id) if annee_id else None

            conflits = HoraireGenerationService.detect_conflicts(
                classe=classe,
                annee_academique=annee,
            )
            return Response({
                'nb_conflits': len(conflits),
                'conflits': conflits,
            })
        except Exception as e:
            return Response({'error': str(e)}, status=400)

    # ── Actions de génération ─────────────────────────────────────────────────

    @action(detail=False, methods=['post'])
    def generate_for_classe(self, request):
        """
        Génère (ou régénère) les horaires d'une seule classe basé sur le volume horaire.

        Body JSON:
            classe_id (int, requis)
            annee_academique_id (int, requis)
            replace_existing (bool, défaut=true): soft-delete les anciens horaires

        Returns:
            {created, skipped, errors, allocations}
        """
        classe_id = request.data.get('classe_id')
        annee_id = request.data.get('annee_academique_id')
        replace = request.data.get('replace_existing', True)

        if not classe_id or not annee_id:
            return Response(
                {'error': 'classe_id et annee_academique_id sont requis'},
                status=400
            )

        try:
            from academics.models import Classe
            from core.models import AnneeAcademique

            classe = Classe.objects.get(pk=classe_id)
            annee = AnneeAcademique.objects.get(pk=annee_id)

            result = HoraireGenerationService.generate_for_classe(
                classe, annee, replace_existing=replace
            )

            AuditLog.log(
                user=request.user,
                action='create',
                description=(
                    f"Génération horaires classe {classe.nom}: "
                    f"{result.get('created', 0)} créneaux créés"
                ),
                request=request
            )
            return Response(result, status=status.HTTP_201_CREATED)

        except Exception as e:
            return Response({'error': str(e)}, status=400)

    @action(detail=False, methods=['post'])
    def generate_all(self, request):
        """
        Génère les horaires pour toutes les classes d'une année académique.

        Body JSON:
            annee_academique_id (int, requis)
            replace_existing (bool, défaut=true)

        Returns:
            {classe_nom: {created, skipped, errors}, ...}
        """
        annee_id = request.data.get('annee_academique_id')
        replace = request.data.get('replace_existing', True)

        if not annee_id:
            return Response({'error': 'annee_academique_id requis'}, status=400)

        try:
            from core.models import AnneeAcademique

            annee = AnneeAcademique.objects.get(pk=annee_id)
            resultats = HoraireGenerationService.generate_for_all_classes(
                annee, replace_existing=replace
            )

            total_created = sum(
                r.get('created', 0) for r in resultats.values()
            )
            AuditLog.log(
                user=request.user,
                action='create',
                description=(
                    f"Génération horaires toutes classes ({annee.nom}): "
                    f"{total_created} créneaux au total"
                ),
                request=request
            )
            return Response({
                'annee_academique': annee.nom,
                'total_created': total_created,
                'par_classe': resultats,
            }, status=status.HTTP_201_CREATED)

        except Exception as e:
            return Response({'error': str(e)}, status=400)


# ─────────────────────────────────────────────────────────────────────────────
# CONFIGURATION HORAIRE PAR CLASSE
# ─────────────────────────────────────────────────────────────────────────────

class ClasseHoraireConfigViewSet(viewsets.ModelViewSet):
    """
    ViewSet pour configurer le nombre d'heures max par jour pour chaque classe.

    Permet de spécifier:
    - heures_max_par_jour: ex: 6 ou 8
    - jours_prolonges: ex: ["LUNDI", "MERCREDI"] (si heures_max > 6)
    """
    queryset = ClasseHoraireConfig.objects.all()
    serializer_class = ClasseHoraireConfigSerializer
    permission_classes = [IsStaffOrDirector]
    filterset_fields = ['classe', 'annee_academique']
    ordering = ['classe__nom']

    def get_queryset(self):
        return super().get_queryset().select_related('classe', 'annee_academique')

    @action(detail=False, methods=['get'])
    def by_classe(self, request):
        """Config horaire d'une classe spécifique."""
        classe_id = request.query_params.get('classe_id')
        annee_id = request.query_params.get('annee_academique_id')

        if not classe_id:
            return Response({'error': 'classe_id requis'}, status=400)

        qs = self.get_queryset().filter(classe_id=classe_id)
        if annee_id:
            qs = qs.filter(annee_academique_id=annee_id)

        config = qs.first()
        if not config:
            return Response(
                {'detail': 'Aucune configuration trouvée. Défaut: 6h/jour.'},
                status=404
            )
        serializer = self.get_serializer(config)
        return Response(serializer.data)


# ─────────────────────────────────────────────────────────────────────────────
# HORAIRES ENSEIGNANTS
# ─────────────────────────────────────────────────────────────────────────────

class HoraireEnseignantViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet pour les horaires enseignants (lecture + génération).

    Actions:
    - list, retrieve
    - generate: génère les horaires pour tous les profs d'une année
    - by_enseignant: horaire d'un prof groupé par jour
    - weekly_summary: résumé du nombre d'heures par cours/classe
    - conflicts: conflits d'un enseignant
    """
    queryset = HoraireEnseignant.objects.all()
    serializer_class = HoraireEnseignantSerializer
    permission_classes = [CanManageAttendance]
    filterset_fields = ['enseignant', 'annee_academique']
    ordering = ['horaire_cours__jour', 'horaire_cours__numero_heure']

    def get_queryset(self):
        return super().get_queryset().select_related(
            'enseignant', 'horaire_cours__cours', 'horaire_cours__classe',
            'annee_academique'
        )

    @action(detail=False, methods=['post'], permission_classes=[IsStaffOrDirector])
    def generate(self, request):
        """
        Génère les horaires enseignants pour tous les profs d'une année.
        Se base sur HoraireCours + AffectationEnseignant.

        Body JSON:
            annee_academique_id (int, requis)
            replace_existing (bool, défaut=true)
        """
        annee_id = request.data.get('annee_academique_id')
        replace = request.data.get('replace_existing', True)

        if not annee_id:
            return Response({'error': 'annee_academique_id requis'}, status=400)

        try:
            from core.models import AnneeAcademique
            annee = AnneeAcademique.objects.get(pk=annee_id)

            result = TeacherScheduleService.generate_teacher_schedules(
                annee, replace_existing=replace
            )

            AuditLog.log(
                user=request.user,
                action='create',
                description=(
                    f"Génération horaires enseignants ({annee.nom}): "
                    f"{result.get('created', 0)} créés"
                ),
                request=request
            )
            return Response(result, status=status.HTTP_201_CREATED)
        except Exception as e:
            return Response({'error': str(e)}, status=400)

    @action(detail=False, methods=['get'])
    def by_enseignant(self, request):
        """
        Horaire d'un enseignant groupé par jour.

        Query params:
            enseignant_id (int, requis)
            annee_academique_id (int, requis)
        """
        enseignant_id = request.query_params.get('enseignant_id')
        annee_id = request.query_params.get('annee_academique_id')

        if not enseignant_id or not annee_id:
            return Response(
                {'error': 'enseignant_id et annee_academique_id requis'},
                status=400
            )

        try:
            from users.models import Personnel
            from core.models import AnneeAcademique

            enseignant = Personnel.objects.get(pk=enseignant_id)
            annee = AnneeAcademique.objects.get(pk=annee_id)

            schedule = TeacherScheduleService.get_schedule_for_teacher(
                enseignant, annee
            )
            return Response({
                'enseignant_id': enseignant.pk,
                'enseignant': str(enseignant),
                'annee_academique': annee.nom,
                'horaire': schedule,
            })
        except Exception as e:
            return Response({'error': str(e)}, status=400)

    @action(detail=False, methods=['get'])
    def weekly_summary(self, request):
        """
        Résumé du nombre d'heures hebdomadaires d'un enseignant par cours/classe.

        Query params:
            enseignant_id (int, requis)
            annee_academique_id (int, requis)
        """
        enseignant_id = request.query_params.get('enseignant_id')
        annee_id = request.query_params.get('annee_academique_id')

        if not enseignant_id or not annee_id:
            return Response(
                {'error': 'enseignant_id et annee_academique_id requis'},
                status=400
            )

        try:
            from users.models import Personnel
            from core.models import AnneeAcademique

            enseignant = Personnel.objects.get(pk=enseignant_id)
            annee = AnneeAcademique.objects.get(pk=annee_id)

            summary = TeacherScheduleService.get_weekly_hours_for_teacher(
                enseignant, annee
            )
            return Response(summary)
        except Exception as e:
            return Response({'error': str(e)}, status=400)

    @action(detail=False, methods=['get'])
    def conflicts(self, request):
        """
        Détecte les conflits d'un enseignant (même créneau, deux cours différents).

        Query params:
            enseignant_id (int, requis)
            annee_academique_id (int, requis)
        """
        enseignant_id = request.query_params.get('enseignant_id')
        annee_id = request.query_params.get('annee_academique_id')

        if not enseignant_id or not annee_id:
            return Response(
                {'error': 'enseignant_id et annee_academique_id requis'},
                status=400
            )

        try:
            from users.models import Personnel
            from core.models import AnneeAcademique

            enseignant = Personnel.objects.get(pk=enseignant_id)
            annee = AnneeAcademique.objects.get(pk=annee_id)

            conflits = TeacherScheduleService.detect_conflicts_teacher(
                enseignant, annee
            )
            return Response({
                'enseignant': str(enseignant),
                'nb_conflits': len(conflits),
                'conflits': conflits,
            })
        except Exception as e:
            return Response({'error': str(e)}, status=400)


# ─────────────────────────────────────────────────────────────────────────────
# PRÉSENCES
# ─────────────────────────────────────────────────────────────────────────────

class PresenceViewSet(AttendanceDataFilterMixin, viewsets.ModelViewSet):
    """
    ViewSet pour la gestion des présences élèves.
    """
    queryset = Presence.objects.all()
    serializer_class = PresenceSerializer
    permission_classes = [CanManageAttendance]
    filterset_fields = ['eleve', 'seance', 'statut']
    ordering = ['-created_at']

    def get_queryset(self):
        return super().get_queryset().select_related('eleve__user', 'seance__cours')

    def perform_create(self, serializer):
        presence = serializer.save()
        AuditLog.log(
            user=self.request.user,
            action='create',
            description=f'Présence enregistrée: {presence.eleve} - {presence.statut}',
            content_object=presence,
            request=self.request
        )

    @action(detail=False, methods=['get'])
    def by_eleve(self, request):
        """Présences d'un élève."""
        eleve_id = request.query_params.get('eleve_id')
        if not eleve_id:
            return Response({'error': 'eleve_id requis'}, status=400)

        presences = self.get_queryset().filter(eleve_id=eleve_id)
        page = self.paginate_queryset(presences)
        if page:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(presences, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def by_seance(self, request):
        """Présences d'une séance."""
        seance_id = request.query_params.get('seance_id')
        if not seance_id:
            return Response({'error': 'seance_id requis'}, status=400)

        presences = self.get_queryset().filter(seance_id=seance_id)
        serializer = self.get_serializer(presences, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['post'])
    def mark_bulk(self, request):
        """Marque la présence de plusieurs élèves."""
        presences_data = request.data.get('presences', [])
        try:
            result = PresenceService.mark_bulk_presence(presences_data, request.user)
            return Response(result, status=201)
        except Exception as e:
            return Response({'error': str(e)}, status=400)

    @action(detail=False, methods=['get'])
    def statistics(self, request):
        """Statistiques de présence d'un élève."""
        eleve_id = request.query_params.get('eleve_id')
        periode_id = request.query_params.get('periode_id')
        try:
            from users.models import Eleve
            from core.models import Periode

            eleve = Eleve.objects.get(id=eleve_id)
            periode = Periode.objects.get(id=periode_id)
            stats = AttendanceStatisticsService.stats_eleve(eleve, periode)
            return Response(stats)
        except Exception as e:
            return Response({'error': str(e)}, status=400)


# ─────────────────────────────────────────────────────────────────────────────
# SÉANCES DE COURS
# ─────────────────────────────────────────────────────────────────────────────

class SeanceViewSet(RoleBasedQuerysetMixin, viewsets.ModelViewSet):
    """
    ViewSet pour la gestion des séances de cours.
    """
    queryset = SeanceCours.objects.all()
    serializer_class = SeanceSerializer
    permission_classes = [CanManageAttendance]
    filterset_fields = ['cours', 'date', 'classe', 'annee_academique']
    ordering = ['-date', 'horaire__heure_debut']

    def get_queryset(self):
        return (
            super().get_queryset()
            .select_related('cours__classe', 'horaire', 'classe')
            .annotate(
                nombre_presences=Count(
                    'presences',
                    filter=Q(presences__actif=True),
                    distinct=True
                )
            )
        )

    def perform_create(self, serializer):
        seance = serializer.save()
        AuditLog.log(
            user=self.request.user,
            action='create',
            description=f'Séance créée: {seance.cours.nom} - {seance.date}',
            content_object=seance,
            request=self.request
        )

    @action(detail=False, methods=['get'])
    def by_cours(self, request):
        """Séances d'un cours."""
        cours_id = request.query_params.get('cours_id')
        if not cours_id:
            return Response({'error': 'cours_id requis'}, status=400)

        seances = self.get_queryset().filter(cours_id=cours_id)
        serializer = self.get_serializer(seances, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def by_date(self, request):
        """Séances par date."""
        date = request.query_params.get('date')
        if not date:
            return Response({'error': 'date requis'}, status=400)

        seances = self.get_queryset().filter(date=date)
        serializer = self.get_serializer(seances, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['post'])
    def generate_seances(self, request):
        """
        Génère les séances pour une classe sur une plage de dates.

        Body JSON:
            classe_id (int, requis)
            annee_academique_id (int, requis)
            date_debut (date, optionnel)
            date_fin (date, optionnel)
        """
        from attendance.services.attendance_generation_service import SeanceGenerationService
        from academics.models import Classe
        from core.models import AnneeAcademique

        classe_id = request.data.get('classe_id')
        annee_id = request.data.get('annee_academique_id')

        if not classe_id or not annee_id:
            return Response({'error': 'classe_id et annee_academique_id requis'}, status=400)

        try:
            from datetime import date as date_type
            classe = Classe.objects.get(pk=classe_id)
            annee = AnneeAcademique.objects.get(pk=annee_id)

            date_debut_str = request.data.get('date_debut')
            date_fin_str = request.data.get('date_fin')
            date_debut = date_type.fromisoformat(date_debut_str) if date_debut_str else None
            date_fin = date_type.fromisoformat(date_fin_str) if date_fin_str else None

            result = SeanceGenerationService.generate_for_classe(
                classe, annee, date_debut=date_debut, date_fin=date_fin
            )
            return Response(result, status=status.HTTP_201_CREATED)
        except Exception as e:
            return Response({'error': str(e)}, status=400)
