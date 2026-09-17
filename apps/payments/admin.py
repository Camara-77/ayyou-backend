from django.contrib import admin
from apps.payments.models import Paiement, Facture


@admin.register(Paiement)
class PaiementAdmin(admin.ModelAdmin):
    list_display = [
        'reference', 'commande', 'montant', 'methode',
        'statut', 'transaction_externe', 'date_creation', 'date_paiement'
    ]
    list_filter = ['methode', 'statut', 'date_creation']
    search_fields = [
        'reference', 'transaction_externe',
        'commande__numero_commande', 'commande__utilisateur__numero_telephone'
    ]
    readonly_fields = ['reference', 'date_creation', 'date_paiement']
    ordering = ['-date_creation']


@admin.register(Facture)
class FactureAdmin(admin.ModelAdmin):
    list_display = [
        'numero_facture', 'commande', 'paiement', 'montant_total',
        'est_payee', 'date_emission', 'date_paiement'
    ]
    list_filter = ['est_payee', 'date_emission']
    search_fields = [
        'numero_facture', 'nom_client_snapshot',
        'telephone_client_snapshot', 'commande__numero_commande'
    ]
    readonly_fields = ['numero_facture', 'date_emission', 'date_paiement']
    ordering = ['-date_emission']
