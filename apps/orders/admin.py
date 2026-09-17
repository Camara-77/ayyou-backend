from django.contrib import admin
from apps.orders.models import (
    Panier, PanierItem, Commande, SousCommande,
    LigneCommande, LigneCommandeVariante, LigneCommandeOption, AdresseLivraison
)


class PanierItemInline(admin.TabularInline):
    model = PanierItem
    extra = 0


@admin.register(Panier)
class PanierAdmin(admin.ModelAdmin):
    list_display = ['id', 'utilisateur', 'actif', 'date_creation', 'date_modification']
    list_filter = ['actif', 'date_creation']
    search_fields = ['utilisateur__email', 'utilisateur__nom', 'utilisateur__prenom']
    inlines = [PanierItemInline]


class LigneCommandeInline(admin.TabularInline):
    model = LigneCommande
    extra = 0


class SousCommandeInline(admin.StackedInline):
    model = SousCommande
    extra = 0


@admin.register(Commande)
class CommandeAdmin(admin.ModelAdmin):
    list_display = ['numero_commande', 'utilisateur', 'statut', 'sous_total', 'frais_livraison', 'total', 'date_creation']
    list_filter = ['statut', 'date_creation']
    search_fields = ['numero_commande', 'utilisateur__email', 'utilisateur__nom', 'nom_destinataire']
    inlines = [SousCommandeInline]


@admin.register(SousCommande)
class SousCommandeAdmin(admin.ModelAdmin):
    list_display = ['id', 'commande', 'etablissement', 'statut', 'total', 'date_creation']
    list_filter = ['statut', 'date_creation']
    search_fields = ['commande__numero_commande', 'etablissement__nom']
    inlines = [LigneCommandeInline]


@admin.register(AdresseLivraison)
class AdresseLivraisonAdmin(admin.ModelAdmin):
    list_display = ['titre', 'utilisateur', 'adresse', 'est_defaut', 'date_creation']
    list_filter = ['est_defaut', 'date_creation']
    search_fields = ['utilisateur__email', 'adresse', 'titre']
