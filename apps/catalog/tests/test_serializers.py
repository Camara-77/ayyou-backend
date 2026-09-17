from django.test import TestCase, RequestFactory
from django.contrib.auth.models import AnonymousUser
from apps.users.models import Utilisateur
from apps.catalog.models import (
    Categorie,
    Etablissement,
    Produit,
    VarianteProduit,
    OptionProduit,
    PublicationFeed,
    LikeProduit
)
from apps.catalog.serializers import (
    CategorieSerializer,
    EtablissementSimplifieSerializer,
    EtablissementSerializer,
    VarianteProduitSerializer,
    OptionProduitSerializer,
    ProduitListSerializer,
    ProduitDetailSerializer,
    PublicationFeedSerializer,
    LikeProduitSerializer
)


class CatalogSerializersTestCase(TestCase):

    def setUp(self):
        self.rf = RequestFactory()

        # Créer un utilisateur client test
        self.user = Utilisateur.objects.create_user(
            email="client.serializer@ayyou.sn",
            numero_telephone="+221772223344",
            prenom="Awa",
            nom="Diop",
            password="Password123!"
        )

        # Créer un utilisateur proprietaire
        self.proprietaire = Utilisateur.objects.create_user(
            email="resto.owner@ayyou.sn",
            numero_telephone="+221773334455",
            prenom="Ousmane",
            nom="Sow",
            password="OwnerPassword123!"
        )

        # Categorie
        self.categorie = Categorie.objects.create(
            nom="Fast Food Sénégalais",
            slug="fast-food-senegalais",
            icone="burger"
        )

        # Etablissement
        self.etablissement = Etablissement.objects.create(
            nom="Chez Ousmane Grill",
            type_etablissement=Etablissement.TYPE_RESTAURANT,
            proprietaire=self.proprietaire,
            adresse="Fann Résidence, Dakar",
            latitude=14.6937,
            longitude=-17.4716,
            telephone="+221338000000",
            statut=Etablissement.STATUT_OUVERT,
            est_verifie=True
        )

        # Produit
        self.produit = Produit.objects.create(
            etablissement=self.etablissement,
            categorie=self.categorie,
            nom="Dibi Agneau Suya",
            description="Grillade d'agneau épicée servie avec oignons",
            prix_base=5000.00,
            image_url="https://ayyou.sn/images/dibi.jpg",
            stock_disponible=50,
            stock_ayyou_reserve=15,
            temps_preparation="15-20 min"
        )

        # Variante
        self.variante = VarianteProduit.objects.create(
            produit=self.produit,
            titre="Portion Familiale 1kg",
            sous_titre="Avec supplément oignons grillés",
            surcout_prix=4000.00,
            est_requis=False
        )

        # Option Sauce
        self.sauce = OptionProduit.objects.create(
            produit=self.produit,
            type_option=OptionProduit.TYPE_SAUCE,
            titre="Sauce Piment Kanou",
            surcout_prix=0.00,
            est_inclus=True
        )

        # Option Supplement
        self.supplement = OptionProduit.objects.create(
            produit=self.produit,
            type_option=OptionProduit.TYPE_SUPPLEMENT,
            titre="Alloco (Bananes Aloko)",
            surcout_prix=1000.00,
            est_inclus=False
        )

        # Publication Feed
        self.publication = PublicationFeed.objects.create(
            etablissement=self.etablissement,
            produit=self.produit,
            media_url="https://ayyou.sn/videos/dibi_prep.mp4",
            type_media=PublicationFeed.TYPE_MEDIA_VIDEO,
            duree_video="0:45"
        )

    def test_categorie_serializer(self):
        serializer = CategorieSerializer(instance=self.categorie)
        data = serializer.data
        self.assertEqual(data['nom'], "Fast Food Sénégalais")
        self.assertEqual(data['slug'], "fast-food-senegalais")
        self.assertEqual(data['icone'], "burger")
        self.assertTrue(data['est_active'])

    def test_etablissement_simplifie_serializer(self):
        serializer = EtablissementSimplifieSerializer(instance=self.etablissement)
        data = serializer.data
        self.assertEqual(data['id'], self.etablissement.id)
        self.assertEqual(data['nom'], "Chez Ousmane Grill")
        self.assertEqual(data['type_etablissement'], Etablissement.TYPE_RESTAURANT)
        self.assertNotIn('proprietaire', data)
        self.assertNotIn('latitude', data)

    def test_etablissement_serializer_masks_sensitive_data(self):
        serializer = EtablissementSerializer(instance=self.etablissement)
        data = serializer.data
        self.assertEqual(data['proprietaire_nom'], "Ousmane Sow")
        # S'assurer qu'aucun mot de passe ou hash n'est exposé
        self.assertNotIn('password', data)
        self.assertNotIn('user_password', data)

    def test_etablissement_serializer_lat_lng_validation(self):
        invalid_lat_data = {
            'nom': 'Test Resto Invalid Lat',
            'type_etablissement': 'RESTAURANT',
            'latitude': 105.0,  # Invalid (>90)
            'longitude': -17.4
        }
        serializer = EtablissementSerializer(data=invalid_lat_data)
        self.assertFalse(serializer.is_valid())
        self.assertIn('latitude', serializer.errors)

        invalid_lng_data = {
            'nom': 'Test Resto Invalid Lng',
            'type_etablissement': 'RESTAURANT',
            'latitude': 14.6,
            'longitude': -200.0  # Invalid (<-180)
        }
        serializer_lng = EtablissementSerializer(data=invalid_lng_data)
        self.assertFalse(serializer_lng.is_valid())
        self.assertIn('longitude', serializer_lng.errors)

    def test_variante_produit_serializer_validation(self):
        serializer = VarianteProduitSerializer(instance=self.variante)
        self.assertEqual(serializer.data['surcout_prix'], '4000.00')

        invalid_data = {
            'produit': str(self.produit.id),
            'titre': 'Portion Négative',
            'surcout_prix': -500.00
        }
        val_serializer = VarianteProduitSerializer(data=invalid_data)
        self.assertFalse(val_serializer.is_valid())
        self.assertIn('surcout_prix', val_serializer.errors)

    def test_option_produit_serializer_validation(self):
        invalid_data = {
            'produit': str(self.produit.id),
            'type_option': 'SAUCE',
            'titre': 'Sauce Négative',
            'surcout_prix': -200.00
        }
        serializer = OptionProduitSerializer(data=invalid_data)
        self.assertFalse(serializer.is_valid())
        self.assertIn('surcout_prix', serializer.errors)

    def test_produit_list_serializer_hides_internal_stocks(self):
        serializer = ProduitListSerializer(instance=self.produit)
        data = serializer.data
        self.assertEqual(data['nom'], "Dibi Agneau Suya")
        self.assertEqual(data['prix_base'], '5000.00')
        # Vérification qu'aucun champ de stock n'est exposé aux clients
        self.assertNotIn('stock_disponible', data)
        self.assertNotIn('stock_ayyou_reserve', data)

    def test_produit_detail_serializer_nested_elements(self):
        serializer = ProduitDetailSerializer(instance=self.produit)
        data = serializer.data
        self.assertEqual(data['nom'], "Dibi Agneau Suya")
        self.assertEqual(len(data['variantes']), 1)
        self.assertEqual(data['variantes'][0]['titre'], "Portion Familiale 1kg")
        self.assertEqual(len(data['sauces']), 1)
        self.assertEqual(data['sauces'][0]['titre'], "Sauce Piment Kanou")
        self.assertEqual(len(data['supplements']), 1)
        self.assertEqual(data['supplements'][0]['titre'], "Alloco (Bananes Aloko)")
        # Stocks masqués également dans le détail client
        self.assertNotIn('stock_disponible', data)
        self.assertNotIn('stock_ayyou_reserve', data)

    def test_produit_detail_serializer_prix_base_negative_validation(self):
        invalid_data = {
            'nom': 'Produit Gratuit Invalide',
            'prix_base': -1000.00
        }
        serializer = ProduitDetailSerializer(data=invalid_data)
        self.assertFalse(serializer.is_valid())
        self.assertIn('prix_base', serializer.errors)

    def test_publication_feed_serializer_structure(self):
        serializer = PublicationFeedSerializer(instance=self.publication)
        data = serializer.data
        self.assertEqual(data['media_url'], "https://ayyou.sn/videos/dibi_prep.mp4")
        self.assertEqual(data['type_media'], "video")
        self.assertEqual(data['duree_video'], "0:45")
        self.assertFalse(data['is_liked'])

    def test_publication_feed_serializer_is_liked_with_auth_context(self):
        # Like de la publication par le client
        LikeProduit.objects.create(utilisateur=self.user, publication=self.publication)

        # Context sans authentification
        req_anon = self.rf.get('/api/catalog/feed/')
        req_anon.user = AnonymousUser()
        ser_anon = PublicationFeedSerializer(instance=self.publication, context={'request': req_anon})
        self.assertFalse(ser_anon.data['is_liked'])

        # Context avec utilisateur authentifié
        req_auth = self.rf.get('/api/catalog/feed/')
        req_auth.user = self.user
        ser_auth = PublicationFeedSerializer(instance=self.publication, context={'request': req_auth})
        self.assertTrue(ser_auth.data['is_liked'])

    def test_like_produit_serializer_requires_target(self):
        request = self.rf.post('/api/catalog/likes/')
        request.user = self.user

        # Essai sans produit ni publication
        serializer = LikeProduitSerializer(data={}, context={'request': request})
        self.assertFalse(serializer.is_valid())
        self.assertIn('non_field_errors', serializer.errors)

    def test_like_produit_serializer_prevents_duplicate_produit_like(self):
        # Créer déjà un like sur le produit
        LikeProduit.objects.create(utilisateur=self.user, produit=self.produit)

        request = self.rf.post('/api/catalog/likes/')
        request.user = self.user

        serializer = LikeProduitSerializer(
            data={'produit': str(self.produit.id)},
            context={'request': request}
        )
        self.assertFalse(serializer.is_valid())
        self.assertIn('non_field_errors', serializer.errors)

    def test_like_produit_serializer_prevents_duplicate_publication_like(self):
        # Créer déjà un like sur la publication
        LikeProduit.objects.create(utilisateur=self.user, publication=self.publication)

        request = self.rf.post('/api/catalog/likes/')
        request.user = self.user

        serializer = LikeProduitSerializer(
            data={'publication': str(self.publication.id)},
            context={'request': request}
        )
        self.assertFalse(serializer.is_valid())
        self.assertIn('non_field_errors', serializer.errors)
