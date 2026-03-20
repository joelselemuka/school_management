from django.contrib import admin
from paie.models import ContratEmploye, BulletinSalaire, PaiementSalaire


@admin.register(ContratEmploye)
class ContratEmployeAdmin(admin.ModelAdmin):
    list_display = ["personnel", "type_contrat", "poste", "salaire_base", "statut", "date_debut"]
    list_filter = ["statut", "type_contrat"]
    search_fields = ["personnel__nom", "personnel__postnom", "poste"]
    ordering = ["-created_at"]
    readonly_fields = ["created_by", "created_at", "updated_at"]


@admin.register(BulletinSalaire)
class BulletinSalaireAdmin(admin.ModelAdmin):
    list_display = ["personnel", "mois", "annee", "salaire_net", "statut"]
    list_filter = ["statut", "annee", "mois"]
    search_fields = ["personnel__nom", "personnel__postnom"]
    ordering = ["-annee", "-mois"]
    readonly_fields = ["created_by", "created_at", "updated_at", "paiement"]


@admin.register(PaiementSalaire)
class PaiementSalaireAdmin(admin.ModelAdmin):
    list_display = ["reference", "personnel", "mois", "annee", "montant", "mode", "statut"]
    list_filter = ["statut", "mode", "annee"]
    search_fields = ["reference", "personnel__nom", "personnel__postnom"]
    ordering = ["-created_at"]
    readonly_fields = ["reference", "created_by", "confirmed_by", "confirmed_at", "created_at"]
