import phonenumbers
from django.conf import settings
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from rest_framework.exceptions import ValidationError, PermissionDenied
from rest_framework_simplejwt.tokens import RefreshToken
from apps.users.models import Utilisateur


class UnverifiedUserException(ValidationError):
    """Exception métier pour les comptes non vérifiés."""
    pass


class LoginService:
    """
    Service métier responsable de l'authentification Client,
    normalisation de l'identifiant (Email / Téléphone E.164),
    vérification des accès, mise à jour de la dernière connexion et génération des tokens JWT.
    """

    @classmethod
    def normalize_identifier(cls, identifier: str) -> tuple[str, str]:
        """
        Détermine si l'identifiant est un email ou un numéro de téléphone,
        et applique la normalisation appropriée.
        """
        raw_val = identifier.strip()
        default_region = getattr(settings, 'DEFAULT_COUNTRY_CODE', 'SN')

        # 1. Si l'identifiant contient '@', il s'agit d'un email
        if '@' in raw_val:
            return 'email', raw_val.lower()

        # 2. Sinon, essayer de parser comme numéro de téléphone via phonenumbers
        try:
            parsed_phone = phonenumbers.parse(raw_val, default_region)
            if phonenumbers.is_valid_number(parsed_phone):
                formatted_phone = phonenumbers.format_number(
                    parsed_phone,
                    phonenumbers.PhoneNumberFormat.E164
                )
                return 'phone', formatted_phone
        except phonenumbers.NumberParseException:
            pass

        # 3. Fallback : renvoyer tel quel si le format n'est pas reconnu
        return 'unknown', raw_val

    @classmethod
    def authenticate_client(cls, identifier: str, password: str) -> dict:
        """
        Authentifie un utilisateur Client et génère la session JWT.
        """
        id_type, normalized_val = cls.normalize_identifier(identifier)

        # 1. Recherche de l'utilisateur par Email ou Téléphone
        user = None
        if id_type == 'email':
            user = Utilisateur.objects.filter(email=normalized_val).first()
        elif id_type == 'phone':
            user = Utilisateur.objects.filter(numero_telephone=normalized_val).first()
        else:
            # Essayer successivement email (si pertinent) ou téléphone
            user = Utilisateur.objects.filter(email=normalized_val.lower()).first()
            if not user:
                user = Utilisateur.objects.filter(numero_telephone=normalized_val).first()

        # 2. Vérifier l'existence et le mot de passe
        if not user or not user.check_password(password):
            raise ValidationError({"detail": _("Identifiants invalides.")})

        # 3. Vérifier si le compte est actif
        if not user.est_actif:
            raise ValidationError({"detail": _("Ce compte a été désactivé. Veuillez contacter le support.")})

        # 4. Vérifier si le compte est vérifié (est_verifie == True)
        if not user.est_verifie:
            raise ValidationError({
                "detail": _("Votre numéro de téléphone n'est pas encore vérifié."),
                "verification_required": True,
                "verification_type": "VERIFICATION_TELEPHONE"
            })

        # 5. Mettre à jour la date de dernière connexion proprement sans affecter les autres champs
        user.derniere_connexion = timezone.now()
        user.save(update_fields=['derniere_connexion'])

        # 6. Générer les tokens JWT SimpleJWT (Access + Refresh)
        refresh = RefreshToken.for_user(user)

        from apps.users.models import Role
        available_modes = [Utilisateur.MODE_CLIENT]
        has_driver = (
            hasattr(user, 'profil_livreur') and
            user.profil_livreur is not None and
            user.roles_attribues.filter(role__nom=Role.LIVREUR).exists()
        )
        if has_driver:
            available_modes.append(Utilisateur.MODE_LIVREUR)

        # 7. Construire la réponse structurée pour le frontend Angular
        return {
            "message": _("Connexion réussie."),
            "access": str(refresh.access_token),
            "refresh": str(refresh),
            "utilisateur": {
                "id": user.id,
                "prenom": user.prenom,
                "nom": user.nom,
                "email": user.email,
                "numero_telephone": user.numero_telephone,
                "est_verifie": user.est_verifie,
                "mode_actif": user.mode_actif,
                "available_modes": available_modes,
                "has_driver_profile": has_driver,
            }
        }

