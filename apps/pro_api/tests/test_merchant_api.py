from rest_framework.test import APITestCase
from rest_framework import status
from django.urls import reverse
from apps.users.models import Utilisateur, Role, UtilisateurRole
from apps.catalog.models import Etablissement, Produit, Categorie, VarianteProduit, OptionProduit
from apps.orders.models import Commande, SousCommande, LigneCommande
from apps.deliveries.models import Livraison
from apps.deliveries.services import DeliveryService


class MerchantAPITestCase(APITestCase):

    def setUp(self):
        # Création des rôles
        self.role_restaurant, _ = Role.objects.get_or_create(nom=Role.RESTAURANT)
        self.role_vendeur, _ = Role.objects.get_or_create(nom=Role.VENDEUR)
        self.role_client, _ = Role.objects.get_or_create(nom=Role.CLIENT)

        # Catégorie globale
        self.categorie = Categorie.objects.create(
            nom="Plats Nationaux",
            slug="plats-nationaux",
            est_active=True
        )

        # 1. Utilisateur Marchand A (Validé - Restaurant)
        self.user_a = Utilisateur.objects.create_user(
            numero_telephone="+221770000001",
            email="restau_a@ayyou.sn",
            nom="Diop",
            prenom="Amadou",
            est_actif=True
        )
        UtilisateurRole.objects.create(utilisateur=self.user_a, role=self.role_restaurant)
        self.etab_a = Etablissement.objects.create(
            nom="Restaurant Teranga A",
            type_etablissement=Etablissement.TYPE_RESTAURANT,
            proprietaire=self.user_a,
            statut_verification=Etablissement.STATUT_VALIDE
        )

        # 2. Utilisateur Marchand B (Validé - Vendeur)
        self.user_b = Utilisateur.objects.create_user(
            numero_telephone="+221770000002",
            email="vendeur_b@ayyou.sn",
            nom="Fall",
            prenom="Fatou",
            est_actif=True
        )
        UtilisateurRole.objects.create(utilisateur=self.user_b, role=self.role_vendeur)
        self.etab_b = Etablissement.objects.create(
            nom="Délices de Fatou B",
            type_etablissement=Etablissement.TYPE_VENDEUR,
            proprietaire=self.user_b,
            statut_verification=Etablissement.STATUT_VALIDE
        )

        # 3. Utilisateur Candidat EN_ATTENTE
        self.user_pending = Utilisateur.objects.create_user(
            numero_telephone="+221770000003",
            email="pending@ayyou.sn",
            nom="Ndiaye",
            prenom="Ousmane",
            est_actif=True
        )
        UtilisateurRole.objects.create(utilisateur=self.user_pending, role=self.role_restaurant)
        etab_pending = Etablissement.objects.create(
            nom="Chez Ousmane",
            type_etablissement=Etablissement.TYPE_RESTAURANT,
            proprietaire=self.user_pending,
            statut_verification=Etablissement.STATUT_EN_ATTENTE
        )
        etab_pending.statut_abonnement = Etablissement.STATUT_ABONNEMENT_INACTIF
        etab_pending.date_expiration_abonnement = None
        etab_pending.save(update_fields=['statut_abonnement', 'date_expiration_abonnement'])

        # 4. Utilisateur Client standard
        self.user_client = Utilisateur.objects.create_user(
            numero_telephone="+221770000004",
            email="client@ayyou.sn",
            nom="Sow",
            prenom="Awa",
            est_actif=True
        )
        UtilisateurRole.objects.create(utilisateur=self.user_client, role=self.role_client)

        # Produits initiaux
        self.produit_a = Produit.objects.create(
            etablissement=self.etab_a,
            categorie=self.categorie,
            nom="Thiéboudienne Rouge A",
            prix_base=4500,
            image_url="https://example.com/thieb.jpg",
            est_disponible=True,
            stock_disponible=50,
            stock_ayyou_reserve=20
        )
        self.produit_b = Produit.objects.create(
            etablissement=self.etab_b,
            categorie=self.categorie,
            nom="Pastels au Thon B",
            prix_base=2500,
            image_url="https://example.com/pastels.jpg",
            est_disponible=True,
            stock_disponible=100,
            stock_ayyou_reserve=40
        )

        # Commande globale
        self.cmd = Commande.objects.create(
            utilisateur=self.user_client,
            numero_commande="AYY-20260918-0001",
            statut=Commande.STATUT_PAYEE,
            adresse_livraison="Dakar Plateau, Rue 10",
            nom_destinataire="Awa Sow",
            telephone_destinataire="+221770000004",
            sous_total=7000,
            frais_livraison=1000,
            total=8000
        )

        # Sous-commande pour Etablissement A
        self.sc_a = SousCommande.objects.create(
            commande=self.cmd,
            etablissement=self.etab_a,
            statut=Commande.STATUT_PAYEE,
            sous_total=4500,
            frais_livraison=500,
            total=5000
        )
        LigneCommande.objects.create(
            sous_commande=self.sc_a,
            produit=self.produit_a,
            nom_produit_snapshot="Thiéboudienne Rouge A",
            quantite=1,
            prix_unitaire=4500,
            total_ligne=4500
        )

        # Sous-commande pour Etablissement B
        self.sc_b = SousCommande.objects.create(
            commande=self.cmd,
            etablissement=self.etab_b,
            statut=Commande.STATUT_PAYEE,
            sous_total=2500,
            frais_livraison=500,
            total=3000
        )
        LigneCommande.objects.create(
            sous_commande=self.sc_b,
            produit=self.produit_b,
            nom_produit_snapshot="Pastels au Thon B",
            quantite=1,
            prix_unitaire=2500,
            total_ligne=2500
        )

        # Fiche de livraison rattachée à la commande globale
        self.livraison = DeliveryService.creer_livraison(self.cmd)

    def test_merchant_profile_get_and_patch(self):

        self.client.force_authenticate(user=self.user_a)
        url = reverse('pro_api:merchant_profile')

        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['nom'], "Restaurant Teranga A")

        response_patch = self.client.patch(url, {'slogan': 'Le meilleur de Dakar'})
        self.assertEqual(response_patch.status_code, status.HTTP_200_OK)
        self.etab_a.refresh_from_db()
        self.assertEqual(self.etab_a.slogan, 'Le meilleur de Dakar')

    def test_merchant_products_list_and_create(self):
        self.client.force_authenticate(user=self.user_a)
        url = reverse('pro_api:merchant_products')

        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['nom'], "Thiéboudienne Rouge A")

        # Création d'un nouveau produit par Marchand A
        new_prod_data = {
            'nom': 'Yassa Poulet A',
            'description': 'Poulet mariné au citron',
            'prix_base': 3500,
            'image_url': 'https://example.com/yassa.jpg',
            'est_disponible': True,
            'stock_disponible': 30,
            'stock_ayyou_reserve': 15,
            'categorie': self.categorie.id
        }
        response_create = self.client.post(url, new_prod_data, format='json')
        self.assertEqual(response_create.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Produit.objects.filter(etablissement=self.etab_a).count(), 2)

    def test_cross_tenant_isolation_security(self):
        """
        Vérifie qu'un marchand A ne peut ni voir, ni modifier, ni supprimer un produit du marchand B.
        """
        self.client.force_authenticate(user=self.user_a)
        url_detail_b = reverse('pro_api:merchant_product_detail', kwargs={'pk': self.produit_b.id})

        # GET produit B par Marchand A -> 404
        response_get = self.client.get(url_detail_b)
        self.assertEqual(response_get.status_code, status.HTTP_404_NOT_FOUND)

        # PATCH produit B par Marchand A -> 404
        response_patch = self.client.patch(url_detail_b, {'nom': 'Piraté'})
        self.assertEqual(response_patch.status_code, status.HTTP_404_NOT_FOUND)

        # DELETE produit B par Marchand A -> 404
        response_delete = self.client.delete(url_detail_b)
        self.assertEqual(response_delete.status_code, status.HTTP_404_NOT_FOUND)

        # Vérification en base : le produit B est intact
        self.produit_b.refresh_from_db()
        self.assertEqual(self.produit_b.nom, "Pastels au Thon B")

    def test_unapproved_user_access_denied(self):
        """
        Vérifie qu'un candidat EN_ATTENTE ou un CLIENT ne peut pas accéder aux APIs PRO Merchant.
        """
        url = reverse('pro_api:merchant_products')

        # Candidat EN_ATTENTE -> 403
        self.client.force_authenticate(user=self.user_pending)
        response_pending = self.client.get(url)
        self.assertEqual(response_pending.status_code, status.HTTP_403_FORBIDDEN)

        # Client standard -> 403
        self.client.force_authenticate(user=self.user_client)
        response_client = self.client.get(url)
        self.assertEqual(response_client.status_code, status.HTTP_403_FORBIDDEN)

        # Non authentifié -> 401
        self.client.logout()
        response_anon = self.client.get(url)
        self.assertEqual(response_anon.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_toggle_product_disponibilite(self):
        self.client.force_authenticate(user=self.user_a)
        url_toggle = reverse('pro_api:merchant_product_toggle', kwargs={'pk': self.produit_a.id})

        self.assertTrue(self.produit_a.est_disponible)
        response = self.client.patch(url_toggle)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertFalse(response.data['est_disponible'])

        self.produit_a.refresh_from_db()
        self.assertFalse(self.produit_a.est_disponible)

    def test_merchant_stats_api(self):
        self.client.force_authenticate(user=self.user_a)
        url_stats = reverse('pro_api:merchant_stats')

        response = self.client.get(url_stats)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['activeProductsCount'], 1)
        self.assertEqual(response.data['etablissement_nom'], "Restaurant Teranga A")

    def test_merchant_orders_list_and_detail(self):
        """
        Vérifie qu'un marchand peut lister et consulter ses propres sous-commandes.
        """
        self.client.force_authenticate(user=self.user_a)
        url_list = reverse('pro_api:merchant_orders')

        response = self.client.get(url_list)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['id'], self.sc_a.id)
        self.assertEqual(response.data[0]['client_nom'], "Awa Sow")

        url_detail = reverse('pro_api:merchant_order_detail', kwargs={'pk': self.sc_a.id})
        response_detail = self.client.get(url_detail)
        self.assertEqual(response_detail.status_code, status.HTTP_200_OK)
        self.assertEqual(response_detail.data['id'], self.sc_a.id)
        self.assertEqual(len(response_detail.data['lignes']), 1)
        self.assertEqual(response_detail.data['lignes'][0]['nom_produit'], "Thiéboudienne Rouge A")

    def test_merchant_order_cross_tenant_isolation(self):
        """
        Vérifie l'isolation multi-tenant : un marchand A tentant d'accéder à la sous-commande B reçoit 404 NOT FOUND.
        """
        self.client.force_authenticate(user=self.user_a)
        url_detail_b = reverse('pro_api:merchant_order_detail', kwargs={'pk': self.sc_b.id})

        response_get = self.client.get(url_detail_b)
        self.assertEqual(response_get.status_code, status.HTTP_404_NOT_FOUND)

        url_status_b = reverse('pro_api:merchant_order_status_update', kwargs={'pk': self.sc_b.id})
        response_patch = self.client.patch(url_status_b, {'statut': Commande.STATUT_EN_PREPARATION})
        self.assertEqual(response_patch.status_code, status.HTTP_404_NOT_FOUND)

    def test_merchant_order_status_update(self):
        """
        Vérifie les transitions de statut autorisées et la synchronisation de la commande principale.
        """
        self.client.force_authenticate(user=self.user_a)
        url_status = reverse('pro_api:merchant_order_status_update', kwargs={'pk': self.sc_a.id})

        # Transition PAYEE -> EN_PREPARATION
        response = self.client.patch(url_status, {'statut': Commande.STATUT_EN_PREPARATION})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['statut'], Commande.STATUT_EN_PREPARATION)

        self.sc_a.refresh_from_db()
        self.assertEqual(self.sc_a.statut, Commande.STATUT_EN_PREPARATION)

        # Transition EN_PREPARATION -> PRETE
        response_prete = self.client.patch(url_status, {'statut': Commande.STATUT_PRETE})
        self.assertEqual(response_prete.status_code, status.HTTP_200_OK)
        self.assertEqual(response_prete.data['statut'], Commande.STATUT_PRETE)

        # Transition invalide PRETE -> EN_PREPARATION -> 400 Bad Request
        response_invalid = self.client.patch(url_status, {'statut': Commande.STATUT_EN_PREPARATION})
        self.assertEqual(response_invalid.status_code, status.HTTP_400_BAD_REQUEST)

    def test_merchant_order_status_sync_with_livraison_multi_etablissements(self):
        """
        Test complet Phase 13.5.1 :
        1. Passage d'une SousCommande à EN_PREPARATION -> Livraison et Commande deviennent EN_PREPARATION.
        2. Passage d'une seule SousCommande à PRETE -> Commande et Livraison ne deviennent PAS prématurément PRETE si autre SousCommande en attente.
        3. L'update du marchand A n'altère pas la SousCommande du marchand B.
        4. Passage de TOUTES les SousCommandes actives à PRETE -> Commande et Livraison deviennent PRETE.
        """
        # Vérification initiale
        self.livraison.refresh_from_db()
        self.assertEqual(self.livraison.statut, Livraison.STATUT_EN_ATTENTE)

        # 1. Marchand A passe SC_A à EN_PREPARATION
        self.client.force_authenticate(user=self.user_a)
        url_status_a = reverse('pro_api:merchant_order_status_update', kwargs={'pk': self.sc_a.id})
        res_a1 = self.client.patch(url_status_a, {'statut': Commande.STATUT_EN_PREPARATION})
        self.assertEqual(res_a1.status_code, status.HTTP_200_OK)

        self.sc_a.refresh_from_db()
        self.cmd.refresh_from_db()
        self.livraison.refresh_from_db()
        self.assertEqual(self.sc_a.statut, Commande.STATUT_EN_PREPARATION)
        self.assertEqual(self.cmd.statut, Commande.STATUT_EN_PREPARATION)
        self.assertEqual(self.livraison.statut, Livraison.STATUT_EN_PREPARATION)

        # 2. Marchand A passe SC_A à PRETE (alors que SC_B est toujours PAYEE)
        res_a2 = self.client.patch(url_status_a, {'statut': Commande.STATUT_PRETE})
        self.assertEqual(res_a2.status_code, status.HTTP_200_OK)

        self.sc_a.refresh_from_db()
        self.sc_b.refresh_from_db()
        self.cmd.refresh_from_db()
        self.livraison.refresh_from_db()

        self.assertEqual(self.sc_a.statut, Commande.STATUT_PRETE)
        self.assertEqual(self.sc_b.statut, Commande.STATUT_PAYEE) # Inchangée pour Marchand B
        self.assertEqual(self.cmd.statut, Commande.STATUT_EN_PREPARATION) # Pas prématurément PRETE !
        self.assertEqual(self.livraison.statut, Livraison.STATUT_EN_PREPARATION) # Pas prématurément PRETE !

        # 3. Marchand B passe SC_B à EN_PREPARATION
        self.client.force_authenticate(user=self.user_b)
        url_status_b = reverse('pro_api:merchant_order_status_update', kwargs={'pk': self.sc_b.id})
        res_b1 = self.client.patch(url_status_b, {'statut': Commande.STATUT_EN_PREPARATION})
        self.assertEqual(res_b1.status_code, status.HTTP_200_OK)

        self.sc_b.refresh_from_db()
        self.cmd.refresh_from_db()
        self.livraison.refresh_from_db()
        self.assertEqual(self.sc_b.statut, Commande.STATUT_EN_PREPARATION)
        self.assertEqual(self.cmd.statut, Commande.STATUT_EN_PREPARATION)
        self.assertEqual(self.livraison.statut, Livraison.STATUT_EN_PREPARATION)

        # 4. Marchand B passe SC_B à PRETE -> TOUTES les SousCommandes sont maintenant PRETE !
        res_b2 = self.client.patch(url_status_b, {'statut': Commande.STATUT_PRETE})
        self.assertEqual(res_b2.status_code, status.HTTP_200_OK)

        self.sc_b.refresh_from_db()
        self.cmd.refresh_from_db()
        self.livraison.refresh_from_db()

        self.assertEqual(self.sc_b.statut, Commande.STATUT_PRETE)
        self.assertEqual(self.cmd.statut, Commande.STATUT_PRETE) # Toutes prêtes !
        self.assertEqual(self.livraison.statut, Livraison.STATUT_PRETE) # Livraison Prête !


