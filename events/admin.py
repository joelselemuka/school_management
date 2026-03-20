"""
Admin pour le module Events.
"""

from django.contrib import admin
from events.models import Event, Actualite, InscriptionEvenement


@admin.register(Event)
class EventAdmin(admin.ModelAdmin):
    """Admin pour les événements."""
    
    list_display = ['titre', 'type_evenement', 'date_debut', 'lieu', 'statut', 'organisateur', 'est_public']
    list_filter = ['type_evenement', 'statut', 'est_public', 'inscription_requise', 'annee_academique']
    search_fields = ['titre', 'description', 'lieu']
    date_hierarchy = 'date_debut'
    readonly_fields = ['created_at', 'updated_at']
    
    fieldsets = (
        ('Informations principales', {
            'fields': ('titre', 'description', 'type_evenement', 'statut')
        }),
        ('Dates et lieu', {
            'fields': ('date_debut', 'date_fin', 'lieu')
        }),
        ('Organisation', {
            'fields': ('organisateur', 'annee_academique', 'participants_attendus')
        }),
        ('Options', {
            'fields': ('est_public', 'inscription_requise', 'image')
        }),
        ('Métadonnées', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(Actualite)
class ActualiteAdmin(admin.ModelAdmin):
    """Admin pour les actualités."""
    
    list_display = ['titre', 'categorie', 'statut', 'auteur', 'date_publication', 'est_une_alerte', 'est_epingle', 'vues']
    list_filter = ['categorie', 'statut', 'est_une_alerte', 'est_epingle', 'annee_academique']
    search_fields = ['titre', 'sous_titre', 'contenu', 'tags']
    date_hierarchy = 'date_publication'
    readonly_fields = ['created_at', 'updated_at', 'vues']
    
    fieldsets = (
        ('Contenu', {
            'fields': ('titre', 'sous_titre', 'contenu', 'categorie')
        }),
        ('Publication', {
            'fields': ('statut', 'auteur', 'annee_academique', 'date_publication', 'date_expiration')
        }),
        ('Médias', {
            'fields': ('image_principale', 'fichier_joint')
        }),
        ('Options', {
            'fields': ('est_une_alerte', 'est_epingle', 'tags')
        }),
        ('Statistiques', {
            'fields': ('vues', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    actions = ['publier_actualites', 'archiver_actualites']
    
    def publier_actualites(self, request, queryset):
        """Action pour publier plusieurs actualités."""
        from django.utils import timezone
        updated = 0
        for actualite in queryset:
            if actualite.statut != 'publie':
                actualite.statut = 'publie'
                if not actualite.date_publication:
                    actualite.date_publication = timezone.now()
                actualite.save()
                updated += 1
        
        self.message_user(request, f"{updated} actualité(s) publiée(s) avec succès.")
    
    publier_actualites.short_description = "Publier les actualités sélectionnées"
    
    def archiver_actualites(self, request, queryset):
        """Action pour archiver plusieurs actualités."""
        updated = queryset.update(statut='archive')
        self.message_user(request, f"{updated} actualité(s) archivée(s) avec succès.")
    
    archiver_actualites.short_description = "Archiver les actualités sélectionnées"


@admin.register(InscriptionEvenement)
class InscriptionEvenementAdmin(admin.ModelAdmin):
    """Admin pour les inscriptions aux événements."""
    
    list_display = ['participant', 'evenement', 'statut', 'nombre_accompagnants', 'created_at']
    list_filter = ['statut', 'evenement__type_evenement', 'created_at']
    search_fields = ['participant__email', 'participant__first_name', 'participant__last_name', 'evenement__titre']
    date_hierarchy = 'created_at'
    readonly_fields = ['created_at', 'updated_at']
    
    fieldsets = (
        ('Inscription', {
            'fields': ('evenement', 'participant', 'statut')
        }),
        ('Détails', {
            'fields': ('nombre_accompagnants', 'commentaire')
        }),
        ('Métadonnées', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    actions = ['confirmer_inscriptions', 'annuler_inscriptions']
    
    def confirmer_inscriptions(self, request, queryset):
        """Action pour confirmer plusieurs inscriptions."""
        updated = queryset.update(statut='confirme')
        self.message_user(request, f"{updated} inscription(s) confirmée(s) avec succès.")
    
    confirmer_inscriptions.short_description = "Confirmer les inscriptions sélectionnées"
    
    def annuler_inscriptions(self, request, queryset):
        """Action pour annuler plusieurs inscriptions."""
        updated = queryset.update(statut='annule')
        self.message_user(request, f"{updated} inscription(s) annulée(s) avec succès.")
    
    annuler_inscriptions.short_description = "Annuler les inscriptions sélectionnées"
