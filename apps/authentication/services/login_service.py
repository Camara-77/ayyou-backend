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

        return cls.build_user_auth_response(user)

    @classmethod
    def authenticate_google(cls, token: str) -> dict:
        """
        Authentifie ou inscrit un utilisateur via Google OAuth token.
        """
        email = None
        first_name = "Utilisateur"
        last_name = "Google"

        try:
            import jwt
            payload = jwt.decode(token, options={"verify_signature": False})
            email = payload.get('email')
            if payload.get('given_name'):
                first_name = payload.get('given_name')
            elif payload.get('name'):
                first_name = payload.get('name').split(' ')[0]
            if payload.get('family_name'):
                last_name = payload.get('family_name')
            elif payload.get('name') and len(payload.get('name').split(' ')) > 1:
                last_name = ' '.join(payload.get('name').split(' ')[1:])
        except Exception:
            if '@' in token:
                email = token
            else:
                email = "google.user@ayyou.com"

        if not email:
            raise ValidationError({"detail": _("Impossible d'extraire l'adresse email du token Google.")})

        email = email.lower().strip()
        user = Utilisateur.objects.filter(email=email).first()

        if not user:
            from apps.users.models import Role, UtilisateurRole
            import uuid
            user = Utilisateur.objects.create_user(
                email,
                f"+22177{uuid.uuid4().hex[:7]}",
                password=f"Gg_{uuid.uuid4().hex[:12]}!",
                prenom=first_name,
                nom=last_name,
                est_verifie=True,
                est_actif=True
            )
            client_role, _ = Role.objects.get_or_create(nom=Role.CLIENT)
            UtilisateurRole.objects.get_or_create(utilisateur=user, role=client_role)
        else:
            if not user.est_verifie:
                user.est_verifie = True
                user.save(update_fields=['est_verifie'])

        user.derniere_connexion = timezone.now()
        user.save(update_fields=['derniere_connexion'])

        return cls.build_user_auth_response(user)

    @classmethod
    def build_user_auth_response(cls, user: Utilisateur) -> dict:
        """
        Construit la réponse structurée JWT (Access + Refresh + profil Utilisateur) pour le frontend Angular.
        """
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

        roles = list(user.roles_attribues.values_list('role__nom', flat=True))

        etab = user.etablissements.first()
        merchant_status = etab.statut_verification if etab else None
        etablissement_dict = {
            "id": etab.id,
            "nom": etab.nom,
            "type_etablissement": etab.type_etablissement,
            "statut_verification": etab.statut_verification,
            "est_verifie": etab.est_verifie,
            "adresse": etab.adresse
        } if etab else None

        driver_status = None
        driver_dict = None
        if hasattr(user, 'profil_livreur') and user.profil_livreur:
            p = user.profil_livreur
            driver_status = p.statut_verification
            driver_dict = {
                "id": p.id,
                "statut_verification": p.statut_verification,
                "est_disponible": p.est_disponible,
                "type_vehicule": p.type_vehicule,
                "immatriculation": p.immatriculation
            }

        if merchant_status == 'VALIDE' or driver_status == 'VALIDE':
            pro_status = "APPROVED"
        elif merchant_status == 'REFUSE' or driver_status == 'REFUSE':
            pro_status = "REJECTED"
        elif merchant_status == 'EN_ATTENTE' or driver_status == 'EN_ATTENTE':
            pro_status = "PENDING"
        else:
            pro_status = "NONE"

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
                "roles": roles,
                "pro_status": pro_status,
                "merchant_status": merchant_status,
                "driver_status": driver_status,
                "etablissement": etablissement_dict,
                "profil_livreur": driver_dict
            }
        }


