from django.contrib import admin
from apps.deliveries.models import Livraison


@admin.register(Livraison)
class LivraisonAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'commande',
        'livreur',
        'statut',
        'est_validee',
        'methode_validation',
        'date_validation',
        'created_at'
    )
    list_filter = ('statut', 'est_validee', 'methode_validation', 'created_at')
    search_fields = (
        'commande__numero_commande',
        'livreur__utilisateur__email',
        'livreur__utilisateur__numero_telephone',
        'code_validation',
        'token_qr'
    )
    readonly_fields = (
        'created_at',
        'updated_at',
        'date_validation',
        'token_qr',
        'code_validation'
    )
