import datetime
from django.core.management.base import BaseCommand
from django.utils import timezone
from apps.users.models import Utilisateur, Role, UtilisateurRole
from apps.catalog.models import Etablissement, Produit, Categorie
from apps.orders.models import RepasPlanifie


class Command(BaseCommand):
    help = "Initialise des données réelles de repas planifiés en base PostgreSQL pour tester le Mon Planning Client."

    def handle(self, *args, **options):
        self.stdout.write(self.style.NOTICE("Initialisation du jeu de données réelles pour le Planning..."))

        # 1. Catégorie & Établissements
        cat, _ = Categorie.objects.get_or_create(
            slug='plats-nationaux',
            defaults={'nom': 'Plats Nationaux', 'est_active': True}
        )

        owner_user, _ = Utilisateur.objects.get_or_create(
            email='pro.owner@ayyou.sn',
            defaults={
                'numero_telephone': '+221771112233',
                'prenom': 'Fatou',
                'nom': 'Sow',
                'est_actif': True
            }
        )
        role_resto, _ = Role.objects.get_or_create(nom=Role.RESTAURANT)
        UtilisateurRole.objects.get_or_create(utilisateur=owner_user, role=role_resto)

        etab_fatou, _ = Etablissement.objects.get_or_create(
            nom='Chez Fatou',
            defaults={
                'type_etablissement': Etablissement.TYPE_RESTAURANT,
                'proprietaire': owner_user,
                'adresse': 'Dakar Plateau',
                'statut_verification': Etablissement.STATUT_VALIDE
            }
        )

        etab_loutcha, _ = Etablissement.objects.get_or_create(
            nom='Chez Loutcha',
            defaults={
                'type_etablissement': Etablissement.TYPE_RESTAURANT,
                'proprietaire': owner_user,
                'adresse': 'Ngor Almadies',
                'statut_verification': Etablissement.STATUT_VALIDE
            }
        )

        # 2. Produits
        prod1, _ = Produit.objects.get_or_create(
            nom='Thiéboudienne Rouge Royale',
            etablissement=etab_fatou,
            defaults={
                'categorie': cat,
                'prix_base': 4500,
                'description': 'Riz rouge avec mérou frais et légumes mijotés',
                'image_url': 'https://images.unsplash.com/photo-1546069901-ba9599a7e63c?auto=format&fit=crop&w=600&q=80',
                'est_disponible': True
            }
        )

        prod2, _ = Produit.objects.get_or_create(
            nom='Dibi Agneau & Aloco',
            etablissement=etab_loutcha,
            defaults={
                'categorie': cat,
                'prix_base': 5000,
                'description': 'Grillade d agneau tendre accompagnée de bananes aloco frites',
                'image_url': 'https://images.unsplash.com/photo-1555939594-58d7cb561ad1?auto=format&fit=crop&w=600&q=80',
                'est_disponible': True
            }
        )

        # 3. Client principal (restaurant.test@ayyou.test ou client)
        client_user = Utilisateur.objects.filter(email='restaurant.test@ayyou.test').first()
        if not client_user:
            client_user = Utilisateur.objects.filter(email='client@ayyou.sn').first()
        if not client_user:
            client_user = Utilisateur.objects.create_user(
                email='client.test@ayyou.sn',
                numero_telephone='+221779998877',
                password='Password123!',
                prenom='Client',
                nom='Test',
                est_actif=True
            )
            role_client, _ = Role.objects.get_or_create(nom=Role.CLIENT)
            UtilisateurRole.objects.get_or_create(utilisateur=client_user, role=role_client)

        # 4. Dates planifiées réelles
        today = timezone.now().date()
        target_day_1 = today  # Aujourd'hui
        target_day_2 = today + datetime.timedelta(days=2)
        target_day_3 = today + datetime.timedelta(days=5)

        # Nettoyage précédent pour ce test user
        RepasPlanifie.objects.filter(utilisateur=client_user).delete()

        repas1 = RepasPlanifie.objects.create(
            utilisateur=client_user,
            produit=prod1,
            etablissement=etab_fatou,
            date_planifiee=target_day_1,
            creneau=RepasPlanifie.CRENEAU_MIDI,
            prix_total=prod1.prix_base,
            statut=RepasPlanifie.STATUT_PLANIFIE,
            instructions='Sans piment'
        )

        repas2 = RepasPlanifie.objects.create(
            utilisateur=client_user,
            produit=prod2,
            etablissement=etab_loutcha,
            date_planifiee=target_day_1,
            creneau=RepasPlanifie.CRENEAU_SOIR,
            prix_total=prod2.prix_base,
            statut=RepasPlanifie.STATUT_PLANIFIE,
            instructions='Sauce oignon séparée'
        )

        repas3 = RepasPlanifie.objects.create(
            utilisateur=client_user,
            produit=prod1,
            etablissement=etab_fatou,
            date_planifiee=target_day_2,
            creneau=RepasPlanifie.CRENEAU_MIDI,
            prix_total=prod1.prix_base,
            statut=RepasPlanifie.STATUT_PLANIFIE
        )

        repas4 = RepasPlanifie.objects.create(
            utilisateur=client_user,
            produit=prod2,
            etablissement=etab_loutcha,
            date_planifiee=target_day_3,
            creneau=RepasPlanifie.CRENEAU_SOIR,
            prix_total=prod2.prix_base,
            statut=RepasPlanifie.STATUT_PLANIFIE
        )

        self.stdout.write(self.style.SUCCESS("=========================================="))
        self.stdout.write(self.style.SUCCESS("   REPAS PLANIFIÉS EN POSTGRESQL CRÉÉS   "))
        self.stdout.write(self.style.SUCCESS("=========================================="))
        self.stdout.write(f"Utilisateur Client : {client_user.email}")
        self.stdout.write(f"Repas #1 : {repas1.produit.nom} ({repas1.date_planifiee} - {repas1.get_creneau_display()})")
        self.stdout.write(f"Repas #2 : {repas2.produit.nom} ({repas2.date_planifiee} - {repas2.get_creneau_display()})")
        self.stdout.write(f"Repas #3 : {repas3.produit.nom} ({repas3.date_planifiee} - {repas3.get_creneau_display()})")
        self.stdout.write(f"Repas #4 : {repas4.produit.nom} ({repas4.date_planifiee} - {repas4.get_creneau_display()})")
        self.stdout.write(self.style.SUCCESS("=========================================="))
