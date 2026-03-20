from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from datetime import date

from academics.models import AffectationEnseignant, Evaluation
from attendance.models import HoraireCours
from common.role_services import RoleService

class TeacherDashboardView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        if not RoleService.is_enseignant(user):
            return Response({"detail": "Non autorisé. Accès réservé aux enseignants."}, status=403)

        personnel = user.personnel_profile
        today = date.today()

        # 1. Mes affectations actives
        affectations = AffectationEnseignant.objects.filter(
            teacher=personnel,
            end_date__isnull=True
        ).select_related('cours__classe')

        cours_list = []
        for aff in affectations:
            cours_list.append({
                "cours_nom": aff.cours.nom,
                "classe_nom": aff.cours.classe.nom,
                "role": aff.role
            })

        # 2. Evaluations à venir ou récentes
        evaluations = Evaluation.objects.filter(
            cours__in=[a.cours for a in affectations]
        ).order_by('-id')[:5]

        evaluations_ret = []
        for ev in evaluations:
            evaluations_ret.append({
                "nom": ev.nom,
                "type": ev.type_evaluation,
                "cours": ev.cours.nom,
                "classe": ev.cours.classe.nom,
            })

        return Response({
            "enseignant": personnel.full_name,
            "statistiques": {
                "nombre_classes": affectations.values('cours__classe').distinct().count(),
                "nombre_cours": affectations.count()
            },
            "cours_actuels": cours_list,
            "evaluations_recentes": evaluations_ret
        })
