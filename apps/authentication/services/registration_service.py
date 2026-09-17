from django.db import transaction
from apps.users.models import Utilisateur, ProfilClient, Role, UtilisateurRole
from apps.authentication.models import VerificationOTP
from .otp_service import OtpService


class RegistrationService:
    """
    Service métier responsable du parcours complet d'inscription Client AYYOU.
    Exécuté dans une transaction atomique globale (transaction.atomic()).
    """

    @classmethod
    @transaction.atomic
    def register_client(cls, validated_data: dict) -> Utilisateur:
        """
        1. Création de l'Utilisateur (hachage mot de passe, email minuscules, telephone normalisé)
        2. Création du ProfilClient (Relation 1:1)
        3. Attribution du rôle CLIENT (Relation N:N via UtilisateurRole)
        4. Génération de l'OTP SMS de vérification (6 chiffres)
        5. Déclenchement du service d'envoi de SMS
        """
        prenom = validated_data['prenom']
        nom = validated_data['nom']
        email = validated_data['email']
        numero_telephone = validated_data['numero_telephone']
        password = validated_data['password']

        # 1. Création de l'Utilisateur avec statut non vérifié
        user = Utilisateur.objects.create_user(
            email=email,
            numero_telephone=numero_telephone,
            password=password,
            prenom=prenom,
            nom=nom,
            est_actif=True,
            est_verifie=False
        )

        # 2. Création du ProfilClient associé
        ProfilClient.objects.create(utilisateur=user)

        # 3. Récupération / Création du Rôle CLIENT et attribution
        role_client, _ = Role.objects.get_or_create(
            nom=Role.CLIENT,
            defaults={'description': 'Rôle Client acheteur AYYOU'}
        )
        UtilisateurRole.objects.create(utilisateur=user, role=role_client)

        # 4 & 5. Génération de l'OTP SMS et déclenchement de l'envoi
        OtpService.generate_and_send_otp(
            utilisateur=user,
            type_verification=VerificationOTP.VERIFICATION_TELEPHONE
        )

        return user

    @classmethod
    @transaction.atomic
    def register_livreur(cls, validated_data: dict) -> tuple[Utilisateur, any]:
        """
        Inscription idempotente pour Livreur :
        - S'assure qu'un SEUL Utilisateur existe (via email / telephone).
        - Crée / Récupère le ProfilClient.
        - Crée / Récupère le ProfilLivreur.
        - Attribue les rôles CLIENT et LIVREUR.
        """
        from apps.users.models import ProfilLivreur

        email = validated_data.get('email', '').strip().lower()
        numero_telephone = validated_data.get('numero_telephone', '').strip()
        prenom = validated_data.get('prenom', '').strip()
        nom = validated_data.get('nom', '').strip()
        password = validated_data.get('password')

        user = None
        if email:
            user = Utilisateur.objects.filter(email=email).first()
        if not user and numero_telephone:
            user = Utilisateur.objects.filter(numero_telephone=numero_telephone).first()

        if not user:
            user = Utilisateur.objects.create_user(
                email=email,
                numero_telephone=numero_telephone,
                password=password,
                prenom=prenom,
                nom=nom,
                est_actif=True,
                est_verifie=True
            )

        # Assurer la présence des deux profils (idempotent)
        ProfilClient.objects.get_or_create(utilisateur=user)
        
        type_vehicule = validated_data.get('type_vehicule', ProfilLivreur.VEHICULE_MOTO)
        immatriculation = validated_data.get('immatriculation', '')

        profil_livreur, _ = ProfilLivreur.objects.get_or_create(
            utilisateur=user,
            defaults={
                'type_vehicule': type_vehicule,
                'immatriculation': immatriculation,
                'statut_verification': ProfilLivreur.STATUT_EN_ATTENTE,
                'est_disponible': False
            }
        )

        # Attribuer les 2 rôles (CLIENT et LIVREUR)
        role_client, _ = Role.objects.get_or_create(
            nom=Role.CLIENT,
            defaults={'description': 'Rôle Client acheteur AYYOU'}
        )
        role_livreur, _ = Role.objects.get_or_create(
            nom=Role.LIVREUR,
            defaults={'description': 'Rôle Livreur AYYOU Pro'}
        )
        UtilisateurRole.objects.get_or_create(utilisateur=user, role=role_client)
        UtilisateurRole.objects.get_or_create(utilisateur=user, role=role_livreur)

        return user, profil_livreur

