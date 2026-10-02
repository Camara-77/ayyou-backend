from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from apps.users.models import Utilisateur, Role, UtilisateurRole
from apps.catalog.models import Categorie, Etablissement, Produit
from apps.admin_panel.serializers import AdminCategorySerializer


class CategorySystemTestCase(APITestCase):

    def setUp(self):
        # Super Admin User
        self.user_admin = Utilisateur.objects.create_user(
            email='superadmin@ayyou.com',
            password='Password123!',
            numero_telephone='+221779998877',
            prenom='Super',
            nom='Admin',
            is_staff=True,
            is_superuser=True,
            est_actif=True,
            est_verifie=True
        )
        self.role_admin, _ = Role.objects.get_or_create(nom=Role.ADMINISTRATEUR)
        UtilisateurRole.objects.get_or_create(utilisateur=self.user_admin, role=self.role_admin)

        from datetime import timedelta
        from django.utils import timezone
        # Merchant Establishment with active subscription
        self.etablissement = Etablissement.objects.create(
            nom='Boulangerie Dakar',
            type_etablissement=Etablissement.TYPE_RESTAURANT,
            est_verifie=True,
            statut_abonnement=Etablissement.STATUT_ABONNEMENT_ACTIF,
            date_expiration_abonnement=timezone.now() + timedelta(days=30)
        )

    def test_A_creation_categorie_active(self):
        """TEST A — Créer 'Nouvelle Catégorie' (est_active=True) via Super Admin et vérifier sa présence en BDD et API publique."""
        self.client.force_authenticate(user=self.user_admin)
        url_admin = reverse('admin_panel:catalog_category-list')

        payload = {
            'nom': 'Nouvelle Catégorie',
            'est_active': True,
            'ordre': 1
        }
        res_admin = self.client.post(url_admin, payload)
        self.assertEqual(res_admin.status_code, status.HTTP_201_CREATED)

        cat_id = res_admin.data['id']
        cat_db = Categorie.objects.get(pk=cat_id)
        self.assertTrue(cat_db.est_active)
        self.assertEqual(cat_db.nom, 'Nouvelle Catégorie')

        # Vérifier API publique sans authentification
        self.client.logout()
        url_public = reverse('catalog:categorie-list')
        res_public = self.client.get(url_public)
        self.assertEqual(res_public.status_code, status.HTTP_200_OK)

        cat_ids_public = [c['id'] for c in res_public.data]
        self.assertIn(cat_id, cat_ids_public)

    def test_B_desactivation_categorie(self):
        """TEST B — Désactiver une catégorie active et vérifier qu'elle disparaît de l'API client publique."""
        cat = Categorie.objects.create(nom='Catégorie Temporaire', est_active=True, ordre=10)

        # Vérifier présence avant désactivation
        self.client.logout()
        res1 = self.client.get(reverse('catalog:categorie-list'))
        self.assertIn(cat.id, [c['id'] for c in res1.data])

        # Désactivation Super Admin
        self.client.force_authenticate(user=self.user_admin)
        url_patch = reverse('admin_panel:catalog_category-detail', kwargs={'pk': cat.id})
        res_patch = self.client.patch(url_patch, {'est_active': False})
        self.assertEqual(res_patch.status_code, status.HTTP_200_OK)

        cat.refresh_from_db()
        self.assertFalse(cat.est_active)

        # Vérification API publique client
        self.client.logout()
        res2 = self.client.get(reverse('catalog:categorie-list'))
        self.assertNotIn(cat.id, [c['id'] for c in res2.data])

    def test_C_categorie_active_sans_produit(self):
        """TEST C — Une catégorie active sans produit (0 produits) doit être retournée par l'API publique."""
        cat = Categorie.objects.create(nom='Boulangerie Pâtisserie', est_active=True, ordre=5)
        self.assertEqual(cat.produits.count(), 0)

        self.client.logout()
        res = self.client.get(reverse('catalog:categorie-list'))
        self.assertEqual(res.status_code, status.HTTP_200_OK)

        cat_ids = [c['id'] for c in res.data]
        self.assertIn(cat.id, cat_ids)

    def test_D_ajout_produit_a_categorie(self):
        """TEST D — Ajouter un plat à une catégorie et vérifier l'association produit -> catégorie."""
        cat = Categorie.objects.create(nom='Grillades Spéciales', est_active=True, ordre=3)

        produit = Produit.objects.create(
            etablissement=self.etablissement,
            categorie=cat,
            nom='Dibi d Agneau Grillé',
            prix_base=5000,
            est_disponible=True
        )

        self.assertEqual(cat.produits.count(), 1)
        self.assertEqual(produit.categorie, cat)

        # Vérification API produits
        self.client.logout()
        url_prods = f"{reverse('catalog:produit-list')}?categorie={cat.id}"
        res = self.client.get(url_prods)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        prods = res.data.get('results', res.data)
        self.assertEqual(len(prods), 1)
        self.assertEqual(prods[0]['nom'], 'Dibi d Agneau Grillé')

    def test_E_mode_visiteur(self):
        """TEST E — Accès visiteur non connecté aux catégories et au catalogue public."""
        self.client.logout()

        res_cats = self.client.get(reverse('catalog:categorie-list'))
        self.assertEqual(res_cats.status_code, status.HTTP_200_OK)

        res_prods = self.client.get(reverse('catalog:produit-list'))
        self.assertEqual(res_prods.status_code, status.HTTP_200_OK)
