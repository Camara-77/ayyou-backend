from django.test import TestCase
from django.core.exceptions import ValidationError
from django.db.utils import IntegrityError
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


class CatalogModelsTestCase(TestCase):

    def setUp(self):
        # Créer un utilisateur test
        self.user = Utilisateur.objects.create_user(
            email="client.test@ayyou.sn",
            numero_telephone="+221771112233",
            prenom="Modou",
            nom="Fall",
            password="Password123!"
        )

        # Créer une catégorie
        self.categorie = Categorie.objects.create(
            nom="Plats Nationaux",
            slug="plats-nationaux",
            icone="utensils"
        )

        # Créer un établissement de type RESTAURANT
        self.restaurant = Etablissement.objects.create(
            nom="Chez Loutcha",
            type_etablissement=Etablissement.TYPE_RESTAURANT,
            adresse="Plateau, Dakar",
            latitude=14.6698000,
            longitude=-17.4381000,
            statut=Etablissement.STATUT_OUVERT,
            est_verifie=True
        )

        # Créer un établissement de type VENDEUR à domicile
        self.vendeur = Etablissement.objects.create(
            nom="Chef Alexandre",
            type_etablissement=Etablissement.TYPE_VENDEUR,
            adresse="Point E, Dakar",
            specialite="Pâtisserie Fine",
            statut=Etablissement.STATUT_OUVERT,
            est_verifie=True
        )

        # Créer un produit
        self.produit = Produit.objects.create(
            etablissement=self.restaurant,
            categorie=self.categorie,
            nom="Thiéboudienne Penda Mbaye",
            description="Riz au poisson rouge traditionnel",
            prix_base=4500.00,
            image_url="https://images.unsplash.com/photo-1546069901-ba9599a7e63c",
            stock_disponible=100,
            stock_ayyou_reserve=40,
            temps_preparation="25-30 min"
        )

    def test_categorie_creation(self):
        self.assertEqual(str(self.categorie), "Plats Nationaux")
        self.assertTrue(self.categorie.est_active)

    def test_etablissement_types_differentiation(self):
        self.assertEqual(self.restaurant.type_etablissement, Etablissement.TYPE_RESTAURANT)
        self.assertEqual(self.vendeur.type_etablissement, Etablissement.TYPE_VENDEUR)
        self.assertIn("Chez Loutcha", str(self.restaurant))
        self.assertIn("Chef Alexandre", str(self.vendeur))

    def test_produit_stock_allocation(self):
        self.assertEqual(self.produit.prix_base, 4500.00)
        self.assertEqual(self.produit.stock_disponible, 100)
        self.assertEqual(self.produit.stock_ayyou_reserve, 40)
        self.assertTrue(self.produit.est_disponible)

    def test_variante_produit_surcout(self):
        variante = VarianteProduit.objects.create(
            produit=self.produit,
            titre="Gourmand Tiof XL",
            sous_titre="Double darne de Tiof",
            surcout_prix=1500.00,
            est_requis=False
        )
        self.assertEqual(variante.surcout_prix, 1500.00)
        self.assertIn("Gourmand Tiof XL", str(variante))

    def test_option_produit_sauce_et_supplement(self):
        sauce = OptionProduit.objects.create(
            produit=self.produit,
            type_option=OptionProduit.TYPE_SAUCE,
            titre="Sauce Beugueul",
            surcout_prix=0.00,
            est_inclus=True
        )
        supplement = OptionProduit.objects.create(
            produit=self.produit,
            type_option=OptionProduit.TYPE_SUPPLEMENT,
            titre="Croûte de riz chaud (Xoogn)",
            surcout_prix=500.00,
            est_inclus=False
        )
        self.assertTrue(sauce.est_inclus)
        self.assertEqual(supplement.surcout_prix, 500.00)

    def test_publication_feed_creation(self):
        publication = PublicationFeed.objects.create(
            etablissement=self.restaurant,
            produit=self.produit,
            media_url="https://ayyou.sn/video1.mp4",
            type_media=PublicationFeed.TYPE_MEDIA_VIDEO,
            duree_video="2:30"
        )
        self.assertEqual(publication.type_media, PublicationFeed.TYPE_MEDIA_VIDEO)
        self.assertEqual(publication.produit, self.produit)

    def test_like_produit_unicite(self):
        like1 = LikeProduit.objects.create(
            utilisateur=self.user,
            produit=self.produit
        )
        self.assertIsNotNone(like1.id)

        # Doublon de Like sur le même produit par le même utilisateur -> doit lever une erreur d'unicité
        with self.assertRaises(IntegrityError):
            LikeProduit.objects.create(
                utilisateur=self.user,
                produit=self.produit
            )

    def test_like_validation_requiert_cible(self):
        # Tenter d'enregistrer un Like sans produit ni publication -> doit lever ValidationError
        like_vide = LikeProduit(utilisateur=self.user)
        with self.assertRaises(ValidationError):
            like_vide.full_clean()
