import secrets
from datetime import timedelta
from django.utils import timezone
from django.conf import settings
from django.db import transaction
from rest_framework.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _
from apps.users.models import Utilisateur
from apps.authentication.models import VerificationOTP
from .sms_service import SmsService


class OtpService:
    """
    Service de gestion des codes OTP (Génération, Invalidation, Expiration, Vérification, Envoi).
    """

    @staticmethod
    def generate_code(length: int = 6) -> str:
        """Génère un code numérique aléatoire sécurisé de 6 chiffres."""
        digits = '0123456789'
        return ''.join(secrets.choice(digits) for _ in range(length))

    @classmethod
    def generate_and_send_otp(cls, utilisateur, type_verification=VerificationOTP.VERIFICATION_TELEPHONE) -> VerificationOTP:
        """
        Invalide les anciens OTP actifs du même type pour l'utilisateur,
        génère un nouvel OTP sécurisé et déclenche l'envoi du SMS.
        """
        # 1. Invalider les anciens OTP non utilisés du même type pour cet utilisateur
        VerificationOTP.objects.filter(
            utilisateur=utilisateur,
            type_verification=type_verification,
            est_utilise=False
        ).update(est_utilise=True)

        # 2. Calculer la date d'expiration à partir de la configuration
        expiration_minutes = getattr(settings, 'OTP_EXPIRATION_MINUTES', 10)
        date_expiration = timezone.now() + timedelta(minutes=expiration_minutes)

        # 3. Générer le code 6 chiffres
        code = cls.generate_code()

        # 4. Enregistrer la nouvelle VerificationOTP
        otp_entry = VerificationOTP.objects.create(
            utilisateur=utilisateur,
            code=code,
            type_verification=type_verification,
            date_expiration=date_expiration,
            nombre_tentatives=0,
            est_utilise=False
        )

        # 5. Déclencher l'envoi du SMS
        SmsService.send_otp_sms(utilisateur.numero_telephone, code)

        return otp_entry

    @classmethod
    def verify_otp_code(cls, numero_telephone: str, code: str):
        """
        Valide le code OTP SMS soumis par l'utilisateur.
        Les erreurs d'expiration ou de mauvais code persistent les tentatives en BDD.
        Le succès d'activation est garanti de manière atomique (transaction.atomic).
        """
        # 1. Rechercher l'utilisateur par numéro de téléphone E.164
        try:
            utilisateur = Utilisateur.objects.get(numero_telephone=numero_telephone)
        except Utilisateur.DoesNotExist:
            raise ValidationError({"detail": _("Code de vérification ou numéro de téléphone invalide.")})

        # 2. Récupérer le dernier OTP de type VERIFICATION_TELEPHONE
        otp = VerificationOTP.objects.filter(
            utilisateur=utilisateur,
            type_verification=VerificationOTP.VERIFICATION_TELEPHONE
        ).order_by('-date_creation', '-id').first()

        if not otp:
            raise ValidationError({"detail": _("Aucun code de vérification trouvé pour ce compte. Veuillez demander un nouveau code.")})

        # 3. Vérifier si l'OTP est déjà utilisé
        if otp.est_utilise:
            raise ValidationError({"detail": _("Ce code de vérification a déjà été utilisé. Veuillez demander un nouveau code.")})

        # 4. Vérifier si l'OTP est expiré
        if otp.est_expire():
            otp.est_utilise = True
            otp.save(update_fields=['est_utilise'])
            raise ValidationError({"detail": _("Le code de vérification a expiré. Veuillez demander un nouveau code.")})

        # 5. Vérifier le nombre de tentatives (max 3)
        if otp.nombre_tentatives >= 3:
            otp.est_utilise = True
            otp.save(update_fields=['est_utilise'])
            raise ValidationError({"detail": _("Nombre maximal de tentatives atteint. Veuillez demander un nouveau code.")})

        # 6. Vérifier la correspondance du code
        if otp.code != code:
            otp.incrementer_tentatives()
            if otp.nombre_tentatives >= 3:
                otp.est_utilise = True
                otp.save(update_fields=['est_utilise'])
                raise ValidationError({"detail": _("Nombre maximal de tentatives atteint. Veuillez demander un nouveau code.")})
            raise ValidationError({"detail": _("Code de vérification incorrect.")})

        # 7. Succès : Traitement atomique de l'activation du compte et d'invalidation de l'OTP
        with transaction.atomic():
            user_locked = Utilisateur.objects.select_for_update().get(pk=utilisateur.pk)
            otp_locked = VerificationOTP.objects.select_for_update().get(pk=otp.pk)

            otp_locked.est_utilise = True
            otp_locked.save(update_fields=['est_utilise'])

            # Invalider tout autre OTP de vérification de téléphone encore actif pour cet utilisateur
            VerificationOTP.objects.filter(
                utilisateur=user_locked,
                type_verification=VerificationOTP.VERIFICATION_TELEPHONE,
                est_utilise=False
            ).update(est_utilise=True)

            # Passer l'utilisateur en est_verifie = True
            user_locked.est_verifie = True
            user_locked.save(update_fields=['est_verifie'])

            return user_locked, otp_locked
