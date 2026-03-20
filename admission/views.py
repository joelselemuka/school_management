from academics.models import Classe
from admission.models import AdmissionApplication, AdmissionGuardian
from admission.permissions.permissions import CanCreateBureauInscription, CanManageAdmission
from admission.serializers.admission_serializers import AdmissionApplicationSerializer
from admission.services.admission_service import AdmissionService
from admission.services.inscription_service import InscriptionService
from core.models import AnneeAcademique
from rest_framework.viewsets import ModelViewSet
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework import status
from django.db import transaction
from django.shortcuts import get_object_or_404


# class AdmissionApplicationViewSet(ModelViewSet):
#     """
#     CRUD des candidatures d'admission.
#     Actions custom : approve, reject.
#     """

#     queryset = AdmissionApplication.objects.all().prefetch_related("guardians")
#     serializer_class = AdmissionApplicationSerializer
#     permission_classes = [CanManageAdmission]

#     @action(detail=True, methods=["post"])
#     def approve(self, request, pk=None):
#         """Approuve une candidature et crée l'inscription."""
#         application = self.get_object()
#         inscription = AdmissionService.approve(application, request.user)
#         return Response({"inscription_id": inscription.id})

#     @action(detail=True, methods=["post"])
#     def reject(self, request, pk=None):
#         """Rejette une candidature."""
#         application = self.get_object()
#         AdmissionService.reject(application)
#         return Response({"status": "rejected"})


# class OnlineAdmissionView(APIView):
#     """
#     Candidature en ligne (pas d'authentification requise).
#     Crée une AdmissionApplication avec les guardians associés.
#     """
#     authentication_classes = []
#     permission_classes = []

#     @transaction.atomic
#     def post(self, request):
#         serializer = AdmissionApplicationSerializer(data=request.data)
#         serializer.is_valid(raise_exception=True)
#         application = serializer.save()

#         guardians = request.data.get("guardians", [])
#         required_fields = ["parent_nom", "parent_postnom", "parent_prenom", "parent_sexe", "lien"]

#         for g in guardians:
#             # Validation des champs obligatoires
#             missing = [f for f in required_fields if f not in g]
#             if missing:
#                 raise serializer.ValidationError(
#                     {f: "Ce champ est requis." for f in missing}
#                 )

#             AdmissionGuardian.objects.create(
#                 application=application,
#                 parent_nom=g["parent_nom"],
#                 parent_postnom=g["parent_postnom"],
#                 parent_prenom=g["parent_prenom"],
#                 parent_telephone=g.get("parent_telephone"),
#                 parent_email=g.get("parent_email"),
#                 parent_adresse=g.get("parent_adresse"),
#                 parent_sexe=g["parent_sexe"],
#                 lien=g["lien"]
#             )

#         return Response(
#             {"message": "Candidature envoyée avec succès"},
#             status=status.HTTP_201_CREATED
#         )


# class BureauInscriptionView(APIView):
#     """
#     Inscription directe au bureau (requiert CanCreateBureauInscription).
#     """
#     permission_classes = [CanCreateBureauInscription]

#     def post(self, request):
#         classe = get_object_or_404(Classe, id=request.data.get("classe"))
#         annee = get_object_or_404(AnneeAcademique, id=request.data.get("annee"))

#         inscription = InscriptionService.create_inscription_from_data(
#             eleve_data=request.data["eleve"],
#             guardians_data=request.data["guardians"],
#             classe=classe,
#             annee_academique=annee,
#             created_by=request.user,
#             source="BUREAU"
#         )

#         return Response({"inscription_id": inscription.id})
