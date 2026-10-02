from django.core.management.base import BaseCommand
from django.utils import timezone
from apps.users.models import Utilisateur, Role, UtilisateurRole
from apps.catalog.models import Etablissement
from apps.payments.services import PaymentService


class Command(BaseCommand):
    help = "Initialise ou réactive l'unique compte Restaurant de Test avec essai gratuit de 1 mois."

    def handle(self, *args, **options):
        email = "restaurant.test@ayyou.test"
        password = "AyyouTest@2026"
        phone = "+221770000099"
        nom_etab = "Chez Loutcha (Test)"

        now = timezone.now()

        # 1. User
        user, user_created = Utilisateur.objects.get_or_create(
            email=email,
            defaults={
                'numero_telephone': phone,
                'prenom': 'Test',
                'nom': 'Restaurant',
                'est_actif': True,
                'est_verifie': True,
            }
        )

        if user_created or not user.check_password(password):
            user.set_password(password)
            user.est_actif = True
            user.est_verifie = True
            user.save()

        # 2. Role RESTAURANT
        role_resto, _ = Role.objects.get_or_create(
            nom=Role.RESTAURANT,
            defaults={'description': 'Gestionnaire de Restaurant'}
        )
        UtilisateurRole.objects.get_or_create(utilisateur=user, role=role_resto)

        # 3. Etablissement
        etab = Etablissement.objects.filter(proprietaire=user).first()
        if not etab:
            etab = Etablissement.objects.create(
                nom=nom_etab,
                type_etablissement=Etablissement.TYPE_RESTAURANT,
                proprietaire=user,
                adresse="Plateau, Dakar",
                telephone="+221770000099",
                specialite="Thiéboudienne & Cuisine Sénégalaise",
                statut_verification=Etablissement.STATUT_VALIDE,
                est_verifie=True,
                statut_abonnement=Etablissement.STATUT_ABONNEMENT_ACTIF,
                date_debut_abonnement=now,
                date_expiration_abonnement=PaymentService.ajouter_un_mois_calendaire(now)
            )
        else:
            # Réactiver & renouveler la période d'essai 1 mois si besoin
            etab.statut_verification = Etablissement.STATUT_VALIDE
            etab.est_verifie = True
            etab.statut_abonnement = Etablissement.STATUT_ABONNEMENT_ACTIF
            etab.date_debut_abonnement = now
            etab.date_expiration_abonnement = PaymentService.ajouter_un_mois_calendaire(now)
            etab.save()

        self.stdout.write(self.style.SUCCESS("=========================================="))
        self.stdout.write(self.style.SUCCESS("   COMPTE RESTAURANT DE TEST CONFIGURÉ   "))
        self.stdout.write(self.style.SUCCESS("=========================================="))
        self.stdout.write(f"Email : {email}")
        self.stdout.write(f"Mot de passe : {password}")
        self.stdout.write(f"ID Établissement : {etab.id}")
        self.stdout.write(f"Nom Établissement : {etab.nom}")
        self.stdout.write(f"Statut Vérification : {etab.get_statut_verification_display()}")
        self.stdout.write(f"Statut Abonnement : {etab.get_statut_abonnement_display()}")
        self.stdout.write(f"Date de début de l'essai : {etab.date_debut_abonnement.strftime('%d/%m/%Y à %H:%M:%S')}")
        self.stdout.write(f"Date de fin de l'essai : {etab.date_expiration_abonnement.strftime('%d/%m/%Y à %H:%M:%S')}")
        self.stdout.write(self.style.SUCCESS("=========================================="))
