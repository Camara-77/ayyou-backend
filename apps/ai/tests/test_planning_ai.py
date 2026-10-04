import io
from unittest.mock import patch
from PIL import Image
from django.test import TestCase
from django.urls import reverse
from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework.test import APIClient
from apps.catalog.models import Produit, Etablissement, Categorie


class AIPlanningParseViewTestCase(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.etablissement = Etablissement.objects.create(
            nom="Chez Fatou",
            type_etablissement="RESTAURANT",
            statut_verification="VALIDE",
            adresse="Dakar Plateau"
        )
        self.categorie = Categorie.objects.create(
            nom="Plats Traditionnels",
            slug="plats-traditionnels"
        )
        self.produit_thieb = Produit.objects.create(
            nom="Thiéboudienne Rouge Royale",
            description="Le véritable Thiéboudienne de Dakar",
            prix_base=4500.00,
            est_disponible=True,
            etablissement=self.etablissement,
            categorie=self.categorie
        )
        self.produit_burger = Produit.objects.create(
            nom="Classic Cheeseburger Pur Bœuf",
            description="Cheeseburger fondant avec cheddar",
            prix_base=4000.00,
            est_disponible=True,
            etablissement=self.etablissement
        )

    def test_00_bonjour_salutation_pas_de_planning(self):
        """TEST CRITIQUE : 'Bonjour' -> Salutation naturelle, ZÉRO mention de planning."""
        url = reverse('ai:planning-parse')
        res = self.client.post(url, {"prompt": "Bonjour"}, format='json')
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data.get('status'), 'greeting')
        self.assertEqual(data.get('intent'), 'GREETING')
        self.assertNotIn('proposition idéale pour votre planning', data.get('message', ''))
        self.assertNotIn('votre planning', data.get('message', '').lower())

    def test_00_que_peux_tu_faire_capabilities(self):
        """TEST CRITIQUE : 'Que peux-tu faire ?' -> Présentation des capacités, ZÉRO création de planning."""
        url = reverse('ai:planning-parse')
        res = self.client.post(url, {"prompt": "Que peux-tu faire ?"}, format='json')
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data.get('status'), 'capabilities')
        self.assertEqual(data.get('intent'), 'CAPABILITIES')
        self.assertIn('Découvrir des restaurants', data.get('message', ''))

    def test_00_jai_5000_fcfa_budget_standalone(self):
        """TEST CRITIQUE : 'J'ai 5 000 FCFA' -> Compréhension du budget, ZÉRO planning automatique."""
        url = reverse('ai:planning-parse')
        res = self.client.post(url, {"prompt": "J'ai 5 000 FCFA"}, format='json')
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data.get('status'), 'budget_discovery')
        self.assertEqual(data.get('intent'), 'BUDGET_DISCOVERY')
        self.assertNotIn('proposition idéale pour votre planning', data.get('message', ''))

    def test_01_texte_planification_clair(self):
        """TEST 1: Texte de planification clair -> CREATE_PLANNING."""
        url = reverse('ai:planning-parse')
        payload = {"prompt": "Planifie-moi du Thiéboudienne demain midi pour deux personnes."}
        res = self.client.post(url, payload, format='json')
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertIn(data.get('status'), ['success', 'missing_info'])
        self.assertEqual(data.get('intent'), 'CREATE_PLANNING')

    def test_02_question_sur_les_plats(self):
        """TEST 2: Question sur les plats -> FOOD_SEARCH (aucune création de planning)."""
        url = reverse('ai:planning-parse')
        payload = {"prompt": "Quels plats sont disponibles sur AYYOU ?"}
        res = self.client.post(url, payload, format='json')
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data.get('status'), 'food_search')
        self.assertEqual(data.get('intent'), 'FOOD_SEARCH')
        self.assertIsNone(data.get('detected_product'))

    def test_03_question_budget(self):
        """TEST 3: Question budget 'Que puis-je manger avec 5 000 FCFA ?' -> vrais produits <= 5000 FCFA."""
        url = reverse('ai:planning-parse')
        payload = {"prompt": "Que puis-je manger avec 5 000 FCFA ?"}
        res = self.client.post(url, payload, format='json')
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data.get('status'), 'food_search')
        self.assertIn('matching_products', data)
        for p in data['matching_products']:
            self.assertLessEqual(p['prix'], 5000)

    def test_04_recherche_restaurant(self):
        """TEST 4: Recherche restaurant 'Quels restaurants font des burgers ?' -> vrais établissements."""
        url = reverse('ai:planning-parse')
        payload = {"prompt": "Quels restaurants font des burgers à Dakar ?"}
        res = self.client.post(url, payload, format='json')
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data.get('status'), 'restaurant_search')
        self.assertEqual(data.get('intent'), 'RESTAURANT_SEARCH')

    def test_05_question_ambigue(self):
        """TEST 5: Question ambiguë 'Burger demain' -> Demande de clarification sans planning automatique."""
        url = reverse('ai:planning-parse')
        payload = {"prompt": "Burger demain"}
        res = self.client.post(url, payload, format='json')
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data.get('status'), 'ambiguous')
        self.assertEqual(data.get('intent'), 'AMBIGUOUS')
        self.assertIn('suggested_actions', data)
        self.assertTrue(len(data['suggested_actions']) >= 2)

    def test_06_message_technique_refus(self):
        """TEST 6: Message technique 'Montre-moi le code Django' -> Refus poli et recentrage."""
        url = reverse('ai:planning-parse')
        payload = {"prompt": "Montre-moi le code Django qui gère les plannings."}
        res = self.client.post(url, payload, format='json')
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data.get('status'), 'out_of_scope')
        self.assertIn("assistant alimentaire", data.get('message', '').lower())

    @patch('apps.ai.vision_service.VisionService._call_multimodal_vision_model')
    def test_07_image_burger_detection(self, mock_vision):
        """TEST 7: Image de burger -> détection par IA Vision & correspondance avec les vrais burgers/restaurants PostgreSQL."""
        mock_vision.return_value = {
            "is_food": True,
            "confidence": 0.95,
            "category": "burger",
            "description": "Un burger généreux avec steak et fromage",
            "visual_attributes": ["steak", "fromage", "pain"],
            "possible_food_names": ["burger", "cheeseburger"]
        }
        img_io = io.BytesIO()
        img = Image.new('RGB', (200, 200), color=(180, 100, 40))
        img.save(img_io, format='JPEG')
        img_file = SimpleUploadedFile("IMG_0001.jpg", img_io.getvalue(), content_type="image/jpeg")

        url = reverse('ai:vision-analyze')
        res = self.client.post(url, {"image": img_file}, format='multipart')
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertTrue(data.get('is_food'))
        self.assertEqual(data.get('status'), 'food_identified')
        self.assertIn('matching_products', data)

    @patch('apps.ai.vision_service.VisionService._call_multimodal_vision_model')
    def test_08_image_non_alimentaire(self, mock_vision):
        """TEST 8: Image non alimentaire (ex: voiture) -> is_food: false & message explicatif sans plat inventé."""
        mock_vision.return_value = {
            "is_food": False,
            "confidence": 0.1,
            "category": None,
            "description": "Une voiture bleue",
            "visual_attributes": [],
            "possible_food_names": []
        }
        img_io = io.BytesIO()
        img = Image.new('RGB', (200, 200), color=(20, 20, 220))
        img.save(img_io, format='JPEG')
        img_file = SimpleUploadedFile("car_test.jpg", img_io.getvalue(), content_type="image/jpeg")

        url = reverse('ai:vision-analyze')
        res = self.client.post(url, {"image": img_file}, format='multipart')
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertFalse(data.get('is_food'))
        self.assertEqual(data.get('status'), 'non_food_image')

    def test_09_image_illisible_sombre(self):
        """TEST 9: Image totalement noire/floue -> détection par Pillow (brightness < 15) & demande description."""
        img_io = io.BytesIO()
        img = Image.new('RGB', (100, 100), color=(0, 0, 0)) # Noire
        img.save(img_io, format='JPEG')
        img_file = SimpleUploadedFile("dark.jpg", img_io.getvalue(), content_type="image/jpeg")

        url = reverse('ai:vision-analyze')
        res = self.client.post(url, {"image": img_file}, format='multipart')
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertFalse(data.get('is_food'))
        self.assertEqual(data.get('status'), 'unclear_image')

    @patch('apps.ai.vision_service.VisionService._call_multimodal_vision_model')
    def test_10_image_vision_fallback_indisponible(self, mock_vision):
        """TEST 10: Modèle Vision temporairement indisponible -> fallback gracieux sans crash."""
        mock_vision.side_effect = Exception("Ollama Vision API offline")
        img_io = io.BytesIO()
        img = Image.new('RGB', (200, 200), color=(200, 150, 100))
        img.save(img_io, format='JPEG')
        img_file = SimpleUploadedFile("sample.jpg", img_io.getvalue(), content_type="image/jpeg")

        url = reverse('ai:vision-analyze')
        res = self.client.post(url, {"image": img_file}, format='multipart')
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data.get('status'), 'vision_service_error')

    def test_11_image_burger_clic_planifier(self):
        """TEST 11: Image burger + force_action 'CREATE_PLANNING' -> Ouverture workflow planning (demande date/heure si manquantes)."""
        url = reverse('ai:planning-parse')
        payload = {"prompt": "burger", "force_action": "CREATE_PLANNING"}
        res = self.client.post(url, payload, format='json')
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data.get('status'), 'missing_info')
        self.assertEqual(data.get('intent'), 'CREATE_PLANNING')

    def test_strict_a_planifie_ce_plat_sans_date_heure(self):
        """TEST A : 'Planifie ce plat' sans date/heure -> demande date + heure, AUCUNE écriture DB."""
        url = reverse('ai:planning-parse')
        res = self.client.post(url, {"prompt": "Planifie ce plat", "product_id": self.produit_thieb.id, "force_action": "CREATE_PLANNING"}, format='json')
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data.get('status'), 'missing_info')
        self.assertIn("Pour quelle date et à quelle heure", data.get('message', ''))

    def test_strict_b_oui_planifier_sans_date_heure(self):
        """TEST B : 'Oui, planifier' sans date/heure -> demande date + heure, AUCUNE écriture DB."""
        url = reverse('ai:planning-parse')
        res = self.client.post(url, {"prompt": "Oui, planifier", "force_action": "CONFIRM_PLANNING"}, format='json')
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data.get('status'), 'missing_info')

    def test_strict_c_date_seule_samedi(self):
        """TEST C : 'Samedi' avec produit sélectionné -> demande l'heure, AUCUNE écriture DB."""
        url = reverse('ai:planning-parse')
        res1 = self.client.post(url, {"prompt": "Thiéboudienne"}, format='json')
        conv_id = res1.json().get('conversation_id')
        res2 = self.client.post(url, {"prompt": "Samedi", "conversation_id": conv_id}, format='json')
        self.assertEqual(res2.status_code, 200)
        data = res2.json()
        self.assertEqual(data.get('status'), 'missing_info')
        self.assertIn("heure", data.get('message', '').lower())

    def test_strict_d_heure_seule_19h30(self):
        """TEST D : 'À 19h30' avec produit sélectionné -> demande la date, AUCUNE écriture DB."""
        url = reverse('ai:planning-parse')
        res1 = self.client.post(url, {"prompt": "Thiéboudienne"}, format='json')
        conv_id = res1.json().get('conversation_id')
        res2 = self.client.post(url, {"prompt": "À 19h30", "conversation_id": conv_id}, format='json')
        self.assertEqual(res2.status_code, 200)
        data = res2.json()
        self.assertEqual(data.get('status'), 'missing_info')
        self.assertIn("date", data.get('message', '').lower())

    def test_strict_e_samedi_a_19h30_proposition_sans_ecriture(self):
        """TEST E : 'Samedi à 19h30' -> résumé + demande de confirmation, AUCUNE écriture avant confirmation."""
        from apps.orders.models import RepasPlanifie
        url = reverse('ai:planning-parse')
        res = self.client.post(url, {"prompt": "Planifie du Thiéboudienne samedi à 19h30"}, format='json')
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data.get('status'), 'success')
        self.assertIn("Voulez-vous confirmer ?", data.get('message', ''))
        self.assertEqual(RepasPlanifie.objects.count(), 0)

    def test_strict_f_oui_confirme_apres_proposition(self):
        """TEST F : 'Oui, confirme' -> création réelle dans RepasPlanifie avec la date et l'heure fournies."""
        from apps.users.models import Utilisateur
        from apps.orders.models import RepasPlanifie
        user = Utilisateur.objects.create_user("test_f@ayyou.com", "+221773333333", password="Password123!")
        self.client.force_authenticate(user=user)

        url = reverse('ai:planning-parse')
        res1 = self.client.post(url, {"prompt": "Planifie du Thiéboudienne samedi à 19h30"}, format='json')
        conv_id = res1.json().get('conversation_id')

        res2 = self.client.post(url, {"prompt": "Oui, confirme", "conversation_id": conv_id, "force_action": "CONFIRM_PLANNING"}, format='json')
        self.assertEqual(res2.status_code, 200)
        data = res2.json()
        self.assertEqual(data.get('status'), 'planning_created')

        pl = RepasPlanifie.objects.filter(utilisateur=user).first()
        self.assertIsNotNone(pl)
        self.assertEqual(pl.produit.nom, "Thiéboudienne Rouge Royale")

    def test_strict_g_parcours_complet_multi_tours(self):
        """TEST G : Conversation multi-tours complète (Plat -> Le premier -> Je veux planifier -> Demain à 13h -> Oui)."""
        from apps.users.models import Utilisateur
        from apps.orders.models import RepasPlanifie
        user = Utilisateur.objects.create_user("test_g@ayyou.com", "+221774444444", password="Password123!")
        self.client.force_authenticate(user=user)
        url = reverse('ai:planning-parse')

        # 1. "Je veux du thiéboudienne"
        r1 = self.client.post(url, {"prompt": "Je veux du thiéboudienne"}, format='json')
        c_id = r1.json().get('conversation_id')

        # 2. "Le premier"
        r2 = self.client.post(url, {"prompt": "Le premier", "conversation_id": c_id}, format='json')
        self.assertEqual(r2.json().get('status'), 'food_selected')

        # 3. "Je veux planifier ce repas"
        r3 = self.client.post(url, {"prompt": "Je veux planifier ce repas", "conversation_id": c_id, "force_action": "CREATE_PLANNING"}, format='json')
        self.assertEqual(r3.json().get('status'), 'missing_info')
        self.assertIn("Pour quelle date et à quelle heure", r3.json().get('message', ''))

        # 4. "Demain à 13h"
        r4 = self.client.post(url, {"prompt": "Demain à 13h", "conversation_id": c_id}, format='json')
        self.assertEqual(r4.json().get('status'), 'success')
        self.assertIn("Voulez-vous confirmer ?", r4.json().get('message', ''))

        # 5. "Oui"
        r5 = self.client.post(url, {"prompt": "Oui", "conversation_id": c_id, "force_action": "CONFIRM_PLANNING"}, format='json')
        self.assertEqual(r5.json().get('status'), 'planning_created')

        pl = RepasPlanifie.objects.filter(utilisateur=user).first()
        self.assertIsNotNone(pl)
        self.assertEqual(pl.produit.nom, "Thiéboudienne Rouge Royale")

    def test_12_image_burger_clic_voir_restaurants(self):
        """TEST 12: Image burger + clic 'Voir les restaurants' -> Recherche uniquement, aucun planning."""
        url = reverse('ai:planning-parse')
        payload = {"prompt": "Quels restaurants font des burgers ?"}
        res = self.client.post(url, payload, format='json')
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data.get('status'), 'restaurant_search')

    def test_13_action_decale_mon_repas(self):
        """TEST 13: 'Décale mon repas' -> identification et réponse structurée."""
        url = reverse('ai:planning-parse')
        payload = {"prompt": "Décale mon repas de vendredi à samedi"}
        res = self.client.post(url, payload, format='json')
        self.assertEqual(res.status_code, 200)

    def test_14_produit_inexistant_zero_hallucination(self):
        """TEST 14: Produit inexistant 'Caviar' -> aucune hallucination, pas de Dibi Agneau."""
        url = reverse('ai:planning-parse')
        payload = {"prompt": "Planifie-moi du Caviar Sauvage demain", "force_action": "CREATE_PLANNING"}
        res = self.client.post(url, payload, format='json')
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data.get('status'), 'missing_info')
        self.assertIsNone(data.get('detected_product'))

    def test_15_restaurant_inexistant_zero_hallucination(self):
        """TEST 15: Restaurant inexistant -> aucune hallucination."""
        url = reverse('ai:planning-parse')
        payload = {"prompt": "Où trouver un repas chez Le Fast Food Inexistant ?"}
        res = self.client.post(url, payload, format='json')
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertIn(data.get('status'), ['restaurant_search', 'missing_info'])

    def test_16_parcours_complet_recherche_restaurants_contexte(self):
        """TEST 16: 'Je veux manger du thieboudienne aujourd'hui à 13h' -> 'Voir les restaurants' utilise le contexte."""
        url = reverse('ai:planning-parse')
        # Étape 1 : Demande initiale
        res1 = self.client.post(url, {"prompt": "Je veux manger du thieboudienne aujourd'hui à 13h"}, format='json')
        self.assertEqual(res1.status_code, 200)
        d1 = res1.json()
        conv_id = d1.get('conversation_id')
        self.assertIsNotNone(conv_id)

        # Étape 2 : Clic 'Voir les restaurants'
        res2 = self.client.post(url, {"prompt": "Voir les restaurants", "conversation_id": conv_id, "force_action": "RESTAURANT_SEARCH"}, format='json')
        self.assertEqual(res2.status_code, 200)
        d2 = res2.json()
        self.assertEqual(d2.get('status'), 'restaurant_search')
        self.assertIn('matching_establishments', d2)
        self.assertTrue(len(d2['matching_establishments']) >= 1)
        self.assertEqual(d2['matching_establishments'][0]['nom'], 'Chez Fatou')

    def test_17_selection_restaurant_message_confirmation(self):
        """TEST 17: Clic 'Sélectionner' un restaurant -> Message de confirmation avec boutons Oui / Non."""
        url = reverse('ai:planning-parse')
        # Demande initiale
        res1 = self.client.post(url, {"prompt": "Manger du thieboudienne aujourd'hui à 13h"}, format='json')
        conv_id = res1.json().get('conversation_id')

        # Sélection restaurant
        payload = {
            "prompt": "Je sélectionne Chez Fatou",
            "conversation_id": conv_id,
            "force_action": "SELECT_RESTAURANT",
            "product_id": self.produit_thieb.id,
            "establishment_id": self.etablissement.id
        }
        res2 = self.client.post(url, payload, format='json')
        self.assertEqual(res2.status_code, 200)
        d2 = res2.json()
        self.assertEqual(d2.get('status'), 'restaurant_selected')
        self.assertIn("Vous avez sélectionné Chez Fatou", d2.get('message', ''))
        self.assertIn('suggested_actions', d2)
        actions = [a['action'] for a in d2['suggested_actions']]
        self.assertIn('CONFIRM_PLANNING', actions)
        self.assertIn('DECLINE_PLANNING', actions)

    def test_18_confirmation_oui_creation_reelle_planning(self):
        """TEST 18: Clic 'Oui, planifier' -> Création réelle dans PostgreSQL orders_repasplanifie."""
        from apps.users.models import Utilisateur
        from apps.orders.models import RepasPlanifie

        user = Utilisateur.objects.create_user("test18@ayyou.com", "+221770000000", password="Password123!")
        self.client.force_authenticate(user=user)

        url = reverse('ai:planning-parse')
        # 1. Demande initiale
        res1 = self.client.post(url, {"prompt": "Thieboudienne aujourd'hui à 13h"}, format='json')
        conv_id = res1.json().get('conversation_id')

        # 2. Sélection
        self.client.post(url, {
            "prompt": "Sélectionner",
            "conversation_id": conv_id,
            "force_action": "SELECT_RESTAURANT",
            "product_id": self.produit_thieb.id,
            "establishment_id": self.etablissement.id
        }, format='json')

        # 3. Confirmation "Oui, planifier"
        res3 = self.client.post(url, {
            "prompt": "Oui, planifier",
            "conversation_id": conv_id,
            "force_action": "CONFIRM_PLANNING"
        }, format='json')

        self.assertEqual(res3.status_code, 200)
        d3 = res3.json()
        self.assertEqual(d3.get('status'), 'planning_created')

        # Vérification directe en base PostgreSQL
        plannings = RepasPlanifie.objects.filter(utilisateur=user, produit=self.produit_thieb)
        self.assertEqual(plannings.count(), 1)
        self.assertEqual(plannings.first().etablissement, self.etablissement)

    def test_19_protection_anti_double_submit(self):
        """TEST 19: Double clic rapide 'Oui, planifier' -> Un seul planning créé dans PostgreSQL."""
        from apps.users.models import Utilisateur
        from apps.orders.models import RepasPlanifie

        user = Utilisateur.objects.create_user("test19@ayyou.com", "+221771111111", password="Password123!")
        self.client.force_authenticate(user=user)

        url = reverse('ai:planning-parse')
        res1 = self.client.post(url, {"prompt": "Thieboudienne aujourd'hui à 13h"}, format='json')
        conv_id = res1.json().get('conversation_id')

        self.client.post(url, {
            "prompt": "Sélectionner",
            "conversation_id": conv_id,
            "force_action": "SELECT_RESTAURANT",
            "product_id": self.produit_thieb.id
        }, format='json')

        # Deux confirmations successives
        self.client.post(url, {"prompt": "Oui", "conversation_id": conv_id, "force_action": "CONFIRM_PLANNING"}, format='json')
        self.client.post(url, {"prompt": "Oui", "conversation_id": conv_id, "force_action": "CONFIRM_PLANNING"}, format='json')

        count = RepasPlanifie.objects.filter(utilisateur=user, produit=self.produit_thieb).count()
        self.assertEqual(count, 1)

    def test_20_refus_non_aucun_planning(self):
        """TEST 20: Clic 'Non' -> Aucun planning créé en base PostgreSQL."""
        from apps.users.models import Utilisateur
        from apps.orders.models import RepasPlanifie

        user = Utilisateur.objects.create_user("test20@ayyou.com", "+221772222222", password="Password123!")
        self.client.force_authenticate(user=user)

        url = reverse('ai:planning-parse')
        res1 = self.client.post(url, {"prompt": "Burger à 13h"}, format='json')
        conv_id = res1.json().get('conversation_id')

        self.client.post(url, {
            "prompt": "Sélectionner",
            "conversation_id": conv_id,
            "force_action": "SELECT_RESTAURANT",
            "product_id": self.produit_burger.id
        }, format='json')

        res3 = self.client.post(url, {"prompt": "Non", "conversation_id": conv_id, "force_action": "DECLINE_PLANNING"}, format='json')
        self.assertEqual(res3.status_code, 200)
        self.assertEqual(res3.json().get('status'), 'declined')

        count = RepasPlanifie.objects.filter(utilisateur=user, produit=self.produit_burger).count()
        self.assertEqual(count, 0)

    def test_21_decouverte_restaurants_categories(self):
        """TEST 21: 'Propose-moi des restaurants' -> RESTAURANT_DISCOVERY avec catégories réelles et établissements."""
        url = reverse('ai:planning-parse')
        res = self.client.post(url, {"prompt": "Propose-moi des restaurants"}, format='json')
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data.get('intent'), 'RESTAURANT_DISCOVERY')
        self.assertIn('suggested_categories', data)
        self.assertTrue(len(data['suggested_categories']) >= 1)

    def test_22_recherche_par_categorie(self):
        """TEST 22: 'Plats Traditionnels' -> CATEGORY_SEARCH avec produits de la catégorie."""
        url = reverse('ai:planning-parse')
        res = self.client.post(url, {"prompt": "Plats Traditionnels"}, format='json')
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data.get('intent'), 'CATEGORY_SEARCH')
        self.assertIn('matching_products', data)

    def test_23_trivia_culinaire_explication(self):
        """TEST 23: 'C'est quoi le thieboudienne ?' -> GENERAL_FOOD_HELP avec explication culinaire et produits réels."""
        url = reverse('ai:planning-parse')
        res = self.client.post(url, {"prompt": "C'est quoi le thieboudienne ?"}, format='json')
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data.get('intent'), 'GENERAL_FOOD_HELP')
        self.assertIn('Thiéboudienne', data.get('message', ''))
        self.assertIn('matching_products', data)

    def test_24_modifier_uniquement_date(self):
        """TEST 14-1: Modifier uniquement la date -> même ID, date modifiée, heure inchangée."""
        from apps.users.models import Utilisateur
        from apps.orders.models import RepasPlanifie
        user = Utilisateur.objects.create_user("moddate@ayyou.com", "+221773333333", password="Password123!")
        self.client.force_authenticate(user=user)

        repas = RepasPlanifie.objects.create(
            utilisateur=user,
            produit=self.produit_thieb,
            etablissement=self.etablissement,
            date_planifiee="2026-10-06",
            heure_planifiee="13:00",
            creneau="MIDI",
            prix_total=4500.0,
            quantite=1
        )
        old_id = repas.id

        url = reverse('orders:planning-detail', kwargs={'pk': old_id})
        resp = self.client.patch(url, {"date_planifiee": "2026-10-10"}, format='json')
        self.assertEqual(resp.status_code, 200)
        data = resp.json()

        self.assertEqual(data['id'], old_id)
        self.assertEqual(data['date_planifiee'], "2026-10-10")
        self.assertEqual(data['heure_planifiee'], "13:00:00")
        self.assertEqual(RepasPlanifie.objects.filter(utilisateur=user).count(), 1)

    def test_25_modifier_uniquement_heure(self):
        """TEST 14-2: Modifier uniquement l'heure -> même ID, heure modifiée, date inchangée."""
        from apps.users.models import Utilisateur
        from apps.orders.models import RepasPlanifie
        user = Utilisateur.objects.create_user("modheure@ayyou.com", "+221774444444", password="Password123!")
        self.client.force_authenticate(user=user)

        repas = RepasPlanifie.objects.create(
            utilisateur=user,
            produit=self.produit_thieb,
            etablissement=self.etablissement,
            date_planifiee="2026-10-06",
            heure_planifiee="12:30",
            creneau="MIDI",
            prix_total=4500.0,
            quantite=1
        )
        old_id = repas.id

        url = reverse('orders:planning-detail', kwargs={'pk': old_id})
        resp = self.client.patch(url, {"heure_planifiee": "14:00"}, format='json')
        self.assertEqual(resp.status_code, 200)
        data = resp.json()

        self.assertEqual(data['id'], old_id)
        self.assertEqual(data['heure_planifiee'], "14:00:00")
        self.assertEqual(data['date_planifiee'], "2026-10-06")
        self.assertEqual(RepasPlanifie.objects.filter(utilisateur=user).count(), 1)

    def test_26_modifier_restaurant_plat_incoherents_refus(self):
        """TEST 14-4: Restaurant et plat incohérents -> refus de modification (400 validation error)."""
        from apps.users.models import Utilisateur
        from apps.orders.models import RepasPlanifie
        user = Utilisateur.objects.create_user("modincoh@ayyou.com", "+221775555555", password="Password123!")
        self.client.force_authenticate(user=user)

        autre_etablissement = Etablissement.objects.create(
            nom="Autre Restaurant",
            type_etablissement="RESTAURANT",
            statut_verification="VALIDE",
            adresse="Fann Dakar"
        )

        repas = RepasPlanifie.objects.create(
            utilisateur=user,
            produit=self.produit_thieb,
            etablissement=self.etablissement,
            date_planifiee="2026-10-06",
            creneau="MIDI",
            prix_total=4500.0,
            quantite=1
        )

        url = reverse('orders:planning-detail', kwargs={'pk': repas.id})
        resp = self.client.patch(url, {"etablissement": autre_etablissement.id}, format='json')
        self.assertEqual(resp.status_code, 400)
        self.assertIn("produit", resp.json())

    def test_27_securite_utilisateur_b_ne_peut_pas_modifier_planning_a(self):
        """TEST 14-7: Utilisateur B tente de modifier le planning de A -> 404 refus sécurisé."""
        from apps.users.models import Utilisateur
        from apps.orders.models import RepasPlanifie

        user_a = Utilisateur.objects.create_user("usera@ayyou.com", "+221776666666", password="Password123!")
        user_b = Utilisateur.objects.create_user("userb@ayyou.com", "+221777777777", password="Password123!")

        repas = RepasPlanifie.objects.create(
            utilisateur=user_a,
            produit=self.produit_thieb,
            etablissement=self.etablissement,
            date_planifiee="2026-10-06",
            creneau="MIDI",
            prix_total=4500.0,
            quantite=1
        )

        self.client.force_authenticate(user=user_b)
        url = reverse('orders:planning-detail', kwargs={'pk': repas.id})
        resp_patch = self.client.patch(url, {"date_planifiee": "2026-10-10"}, format='json')
        self.assertEqual(resp_patch.status_code, 404)

        resp_get = self.client.get(url)
        self.assertEqual(resp_get.status_code, 404)

        resp_del = self.client.delete(url)
        self.assertEqual(resp_del.status_code, 404)

    def test_28_copilot_modification_heure(self):
        """TEST 14-8: Copilot 'change seulement l'heure à 14h' -> seule l'heure change, même ID."""
        from apps.users.models import Utilisateur
        from apps.orders.models import RepasPlanifie

        user = Utilisateur.objects.create_user("copilotmod@ayyou.com", "+221778888888", password="Password123!")
        self.client.force_authenticate(user=user)

        repas = RepasPlanifie.objects.create(
            utilisateur=user,
            produit=self.produit_thieb,
            etablissement=self.etablissement,
            date_planifiee="2026-10-06",
            heure_planifiee="12:30",
            creneau="MIDI",
            prix_total=4500.0,
            quantite=1
        )
        old_id = repas.id

        url = reverse('ai:planning-parse')
        res1 = self.client.post(url, {"prompt": "Change seulement l'heure à 14h", "planning_id": old_id}, format='json')
        self.assertEqual(res1.status_code, 200)
        data1 = res1.json()
        self.assertEqual(data1['status'], 'success')
        conv_id = data1['conversation_id']

        res2 = self.client.post(url, {"prompt": "Oui, modifier", "conversation_id": conv_id, "force_action": "CONFIRM_UPDATE_PLANNING"}, format='json')
        self.assertEqual(res2.status_code, 200)
        data2 = res2.json()
        self.assertEqual(data2['status'], 'planning_updated')
        self.assertEqual(data2['planning_id'], old_id)

        repas.refresh_from_db()
        self.assertEqual(repas.id, old_id)
        self.assertEqual(str(repas.heure_planifiee)[:5], "14:00")
        self.assertEqual(repas.date_planifiee.strftime('%Y-%m-%d'), "2026-10-06")
        self.assertEqual(RepasPlanifie.objects.filter(utilisateur=user).count(), 1)

    def test_29_copilot_annulation_modification(self):
        """TEST 14-6: Clic/Mot 'Annuler' lors de la modification -> 0 modif DB, status declined."""
        from apps.users.models import Utilisateur
        from apps.orders.models import RepasPlanifie

        user = Utilisateur.objects.create_user("cancelmod@ayyou.com", "+221779999999", password="Password123!")
        self.client.force_authenticate(user=user)

        repas = RepasPlanifie.objects.create(
            utilisateur=user,
            produit=self.produit_thieb,
            etablissement=self.etablissement,
            date_planifiee="2026-10-06",
            heure_planifiee="12:30",
            creneau="MIDI",
            prix_total=4500.0,
            quantite=1
        )
        old_id = repas.id

        url = reverse('ai:planning-parse')
        res1 = self.client.post(url, {"prompt": "Change l'heure à 14h", "planning_id": old_id}, format='json')
        conv_id = res1.json().get('conversation_id')

        res2 = self.client.post(url, {"prompt": "Annuler", "conversation_id": conv_id, "force_action": "DECLINE_PLANNING"}, format='json')
        self.assertEqual(res2.status_code, 200)
        self.assertEqual(res2.json().get('status'), 'declined')
        self.assertIn("annulé", res2.json().get('message', ''))

        repas.refresh_from_db()
        self.assertEqual(str(repas.heure_planifiee)[:5], "12:30")
        self.assertEqual(RepasPlanifie.objects.filter(utilisateur=user).count(), 1)

    def test_30_suppression_manuelle_detail_view(self):
        """TEST Phase 3-1: Suppression manuelle (DELETE /api/orders/planning/{id}/) par le propriétaire."""
        from apps.users.models import Utilisateur
        from apps.orders.models import RepasPlanifie
        user = Utilisateur.objects.create_user("delman@ayyou.com", "+221771010101", password="Password123!")
        self.client.force_authenticate(user=user)

        repas = RepasPlanifie.objects.create(
            utilisateur=user,
            produit=self.produit_thieb,
            etablissement=self.etablissement,
            date_planifiee="2026-10-10",
            heure_planifiee="12:30",
            creneau="MIDI",
            prix_total=4500.0,
            quantite=1
        )
        url = reverse('orders:planning-detail', kwargs={'pk': repas.id})
        res = self.client.delete(url)
        self.assertEqual(res.status_code, 240 - 36) # 204 NO CONTENT

        repas.refresh_from_db()
        self.assertEqual(repas.statut, RepasPlanifie.STATUT_ANNULE)
        self.assertFalse(repas.rappel_valide)
        self.assertFalse(repas.rappel_reporte)

    def test_31_refus_suppression_repas_commande_validee(self):
        """TEST Phase 3-2: Refus de suppression pour un repas déjà transformé en commande."""
        from apps.users.models import Utilisateur
        from apps.orders.models import RepasPlanifie
        user = Utilisateur.objects.create_user("delpaid@ayyou.com", "+221772020202", password="Password123!")
        self.client.force_authenticate(user=user)

        repas = RepasPlanifie.objects.create(
            utilisateur=user,
            produit=self.produit_thieb,
            etablissement=self.etablissement,
            date_planifiee="2026-10-10",
            heure_planifiee="12:30",
            creneau="MIDI",
            prix_total=4500.0,
            quantite=1,
            statut=RepasPlanifie.STATUT_COMMANDE
        )

        # 1. API direct DELETE -> 400 Bad Request
        url_api = reverse('orders:planning-detail', kwargs={'pk': repas.id})
        res_api = self.client.delete(url_api)
        self.assertEqual(res_api.status_code, 400)
        self.assertIn("déjà été transformé en commande", res_api.json().get('detail', ''))

        # 2. Copilot AI suppression -> refus et explication
        url_ai = reverse('ai:planning-parse')
        res_ai = self.client.post(url_ai, {"prompt": "Supprime mon repas de thiéboudienne", "planning_id": repas.id}, format='json')
        self.assertEqual(res_ai.status_code, 200)
        self.assertEqual(res_ai.json().get('status'), 'cannot_delete_converted')

    def test_32_copilot_suppression_intention_et_proposition(self):
        """TEST Phase 3-3: Intention 'Supprime mon repas de demain' -> proposition confirm_delete_proposal sans suppression avant confirmation."""
        from apps.users.models import Utilisateur
        from apps.orders.models import RepasPlanifie
        import datetime
        from django.utils import timezone
        user = Utilisateur.objects.create_user("delaiprop@ayyou.com", "+221773030303", password="Password123!")
        self.client.force_authenticate(user=user)

        demain = timezone.now().date() + datetime.timedelta(days=1)
        repas = RepasPlanifie.objects.create(
            utilisateur=user,
            produit=self.produit_thieb,
            etablissement=self.etablissement,
            date_planifiee=demain,
            heure_planifiee="12:30",
            creneau="MIDI",
            prix_total=4500.0,
            quantite=1
        )

        url = reverse('ai:planning-parse')
        res = self.client.post(url, {"prompt": "Supprime mon repas de demain midi"}, format='json')
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data.get('status'), 'confirm_delete_proposal')
        self.assertEqual(data.get('intent'), 'DELETE_PLANNING')
        self.assertIn("Voulez-vous vraiment supprimer le repas planifié", data.get('message', ''))

        repas.refresh_from_db()
        self.assertEqual(repas.statut, RepasPlanifie.STATUT_PLANIFIE)

    def test_33_copilot_suppression_confirmation_oui(self):
        """TEST Phase 3-4: Confirmation 'Oui, supprimer' -> passage au statut ANNULE."""
        from apps.users.models import Utilisateur
        from apps.orders.models import RepasPlanifie
        user = Utilisateur.objects.create_user("delaiyes@ayyou.com", "+221774040404", password="Password123!")
        self.client.force_authenticate(user=user)

        repas = RepasPlanifie.objects.create(
            utilisateur=user,
            produit=self.produit_thieb,
            etablissement=self.etablissement,
            date_planifiee="2026-10-12",
            heure_planifiee="12:30",
            creneau="MIDI",
            prix_total=4500.0,
            quantite=1
        )

        url = reverse('ai:planning-parse')
        res1 = self.client.post(url, {"prompt": "Supprime mon repas de thiéboudienne", "planning_id": repas.id}, format='json')
        conv_id = res1.json().get('conversation_id')

        res2 = self.client.post(url, {"prompt": "Oui, supprimer", "conversation_id": conv_id, "force_action": "CONFIRM_DELETE_PLANNING"}, format='json')
        self.assertEqual(res2.status_code, 200)
        data2 = res2.json()
        self.assertEqual(data2.get('status'), 'planning_deleted')

        repas.refresh_from_db()
        self.assertEqual(repas.statut, RepasPlanifie.STATUT_ANNULE)

    def test_34_copilot_suppression_annulation_non(self):
        """TEST Phase 3-5: Refus 'Non' -> suppression annulée, repas conservé."""
        from apps.users.models import Utilisateur
        from apps.orders.models import RepasPlanifie
        user = Utilisateur.objects.create_user("delainon@ayyou.com", "+221775050505", password="Password123!")
        self.client.force_authenticate(user=user)

        repas = RepasPlanifie.objects.create(
            utilisateur=user,
            produit=self.produit_thieb,
            etablissement=self.etablissement,
            date_planifiee="2026-10-12",
            heure_planifiee="12:30",
            creneau="MIDI",
            prix_total=4500.0,
            quantite=1
        )

        url = reverse('ai:planning-parse')
        res1 = self.client.post(url, {"prompt": "Supprime mon repas de thiéboudienne", "planning_id": repas.id}, format='json')
        conv_id = res1.json().get('conversation_id')

        res2 = self.client.post(url, {"prompt": "Non", "conversation_id": conv_id, "force_action": "DECLINE_PLANNING"}, format='json')
        self.assertEqual(res2.status_code, 200)
        data2 = res2.json()
        self.assertEqual(data2.get('status'), 'declined')
        self.assertIn("La suppression a été annulée", data2.get('message', ''))

        repas.refresh_from_db()
        self.assertEqual(repas.statut, RepasPlanifie.STATUT_PLANIFIE)

    def test_35_securite_utilisateur_b_ne_peut_pas_supprimer_planning_a(self):
        """TEST Phase 3-6: Utilisateur B ne peut pas supprimer le repas de l'Utilisateur A (404 / no_planning_found)."""
        from apps.users.models import Utilisateur
        from apps.orders.models import RepasPlanifie
        user_a = Utilisateur.objects.create_user("user_a_del@ayyou.com", "+221776060606", password="Password123!")
        user_b = Utilisateur.objects.create_user("user_b_del@ayyou.com", "+221777070707", password="Password123!")

        repas = RepasPlanifie.objects.create(
            utilisateur=user_a,
            produit=self.produit_thieb,
            etablissement=self.etablissement,
            date_planifiee="2026-10-12",
            heure_planifiee="12:30",
            creneau="MIDI",
            prix_total=4500.0,
            quantite=1
        )

        self.client.force_authenticate(user=user_b)
        url_api = reverse('orders:planning-detail', kwargs={'pk': repas.id})
        res_api = self.client.delete(url_api)
        self.assertEqual(res_api.status_code, 404)

        url_ai = reverse('ai:planning-parse')
        res_ai = self.client.post(url_ai, {"prompt": "Supprime le repas", "planning_id": repas.id}, format='json')
        self.assertEqual(res_ai.status_code, 404)


