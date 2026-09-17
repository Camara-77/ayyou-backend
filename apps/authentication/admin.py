from django.contrib import admin
from django.utils.translation import gettext_lazy as _
from .models import VerificationOTP


@admin.register(VerificationOTP)
class VerificationOTPAdmin(admin.ModelAdmin):
    """
    Administration de la table VerificationOTP.
    Masque le code OTP et protège les données sensibles en lecture seule.
    """
    list_display = ('utilisateur', 'type_verification', 'date_expiration', 'nombre_tentatives', 'est_utilise', 'date_creation')
    list_filter = ('type_verification', 'est_utilise', 'date_creation')
    search_fields = ('utilisateur__email', 'utilisateur__numero_telephone')
    readonly_fields = ('utilisateur', 'code_masque', 'type_verification', 'date_expiration', 'nombre_tentatives', 'est_utilise', 'date_creation')

    exclude = ('code',)

    def code_masque(self, obj):
        """Affiche un masque pour ne jamais exposer le code OTP en clair dans l'admin."""
        if obj.code:
            return f"***{obj.code[-2:]}"
        return "******"
    code_masque.short_description = _('Code OTP (Masqué)')
