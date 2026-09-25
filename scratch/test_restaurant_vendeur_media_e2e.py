import os
import sys
import json
import django
from decimal import Decimal
from django.core.files.uploadedfile import SimpleUploadedFile

# Setup Django Environment
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.base')
django.setup()

from django.conf import settings
if 'testserver' not in settings.ALLOWED_HOSTS:
    settings.ALLOWED_HOSTS.append('testserver')

from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from apps.catalog.models import Categorie, Produit, Etablissement, PublicationFeed
from apps.catalog.services import CloudinaryFeedService

from apps.users.models import Role, UtilisateurRole

Utilisateur = get_user_model()


def run_media_and_catalog_e2e_tests():
    print("=" * 80)
    print("EXECUTION DES TESTS RESTAURANT, VENDEUR, CLOUDINARY ET VISIBILITE CLIENT")
    print("=" * 80)

    # Récupérer ou créer les rôles en BD
    role_resto, _ = Role.objects.get_or_create(nom=Role.RESTAURANT)
    role_vendeur, _ = Role.objects.get_or_create(nom=Role.VENDEUR)

    results = {
        'restaurant_creation_produit': False,
        'restaurant_modification_prix': False,
        'restaurant_toggle_disponibilite': False,
        'restaurant_upload_image': False,
        'restaurant_upload_video': False,
        'restaurant_association_video_plat': False,
        'vendeur_creation_produit': False,
        'vendeur_upload_image': False,
        'vendeur_upload_video': False,
        'client_visibilite_produits': False,
        'client_visibilite_feed_video': False,
        'isolation_restaurant_a_b': False,
        'isolation_vendeur_a_b': False,
        'isolation_restaurant_vendeur': False,
        'cloudinary_real_image_test': False,
        'cloudinary_real_video_test': False,
    }

    client_rest_a = APIClient()
    client_rest_b = APIClient()
    client_vend_a = APIClient()
    client_vend_b = APIClient()
    client_public = APIClient()

    # 1. Création des Utilisateurs et Établissements
    user_resto_a, _ = Utilisateur.objects.get_or_create(
        email='owner_resto_a@ayyou.com',
        defaults={'numero_telephone': '+221771110001', 'prenom': 'Amadou', 'nom': 'Diallo', 'mode_actif': Utilisateur.MODE_CLIENT, 'est_actif': True}
    )
    user_resto_a.set_password('pass123')
    user_resto_a.save()
    UtilisateurRole.objects.get_or_create(utilisateur=user_resto_a, role=role_resto)

    resto_a, _ = Etablissement.objects.get_or_create(
        proprietaire=user_resto_a,
        defaults={'nom': 'Le Dakarois Gourmet', 'type_etablissement': Etablissement.TYPE_RESTAURANT, 'statut_verification': Etablissement.STATUT_VALIDE, 'adresse': 'Plateau, Dakar'}
    )

    user_resto_b, _ = Utilisateur.objects.get_or_create(
        email='owner_resto_b@ayyou.com',
        defaults={'numero_telephone': '+221771110002', 'prenom': 'Fatou', 'nom': 'Sow', 'mode_actif': Utilisateur.MODE_CLIENT, 'est_actif': True}
    )
    user_resto_b.set_password('pass123')
    user_resto_b.save()
    UtilisateurRole.objects.get_or_create(utilisateur=user_resto_b, role=role_resto)

    resto_b, _ = Etablissement.objects.get_or_create(
        proprietaire=user_resto_b,
        defaults={'nom': 'Le Ngor Seafood', 'type_etablissement': Etablissement.TYPE_RESTAURANT, 'statut_verification': Etablissement.STATUT_VALIDE, 'adresse': 'Almadies, Dakar'}
    )

    user_vend_a, _ = Utilisateur.objects.get_or_create(
        email='owner_vend_a@ayyou.com',
        defaults={'numero_telephone': '+221772220001', 'prenom': 'Awa', 'nom': 'Ndiaye', 'mode_actif': Utilisateur.MODE_CLIENT, 'est_actif': True}
    )
    user_vend_a.set_password('pass123')
    user_vend_a.save()
    UtilisateurRole.objects.get_or_create(utilisateur=user_vend_a, role=role_vendeur)

    vend_a, _ = Etablissement.objects.get_or_create(
        proprietaire=user_vend_a,
        defaults={'nom': 'Les Delices d Awa', 'type_etablissement': Etablissement.TYPE_VENDEUR, 'statut_verification': Etablissement.STATUT_VALIDE, 'adresse': 'Mermoz, Dakar'}
    )

    user_vend_b, _ = Utilisateur.objects.get_or_create(
        email='owner_vend_b@ayyou.com',
        defaults={'numero_telephone': '+221772220002', 'prenom': 'Ousmane', 'nom': 'Ba', 'mode_actif': Utilisateur.MODE_CLIENT, 'est_actif': True}
    )
    user_vend_b.set_password('pass123')
    user_vend_b.save()
    UtilisateurRole.objects.get_or_create(utilisateur=user_vend_b, role=role_vendeur)

    vend_b, _ = Etablissement.objects.get_or_create(
        proprietaire=user_vend_b,
        defaults={'nom': 'Cuisine Maison Ousmane', 'type_etablissement': Etablissement.TYPE_VENDEUR, 'statut_verification': Etablissement.STATUT_VALIDE, 'adresse': 'Ouakam, Dakar'}
    )


    client_rest_a.force_authenticate(user=user_resto_a)
    client_rest_b.force_authenticate(user=user_resto_b)
    client_vend_a.force_authenticate(user=user_vend_a)
    client_vend_b.force_authenticate(user=user_vend_b)

    categorie, _ = Categorie.objects.get_or_create(nom='Plats Nationaux')

    # SCÉNARIO 1 : RESTAURANT A - Création, Modification, Upload Image & Vidéo
    print("\n[1/10] RESTAURANT A: Création de plat (Thiéboudienne Rouge)...")
    res_create_p1 = client_rest_a.post('/api/pro/merchant/products/', {
        'nom': 'Thiéboudienne Rouge Royale',
        'description': 'Riz rouge au mérou frais et légumes',
        'prix_base': '4500.00',
        'categorie': categorie.id,
        'image_url': 'https://res.cloudinary.com/demo/image/upload/ayyou/products/thieb.jpg',
        'est_disponible': True,
        'variantes': [{'titre': 'Portion Individuelle', 'surcout_prix': '0.00'}]
    }, format='json')

    print(f"       POST product HTTP {res_create_p1.status_code}")
    if res_create_p1.status_code == 201:
        results['restaurant_creation_produit'] = True
        prod_a_id = res_create_p1.data['id']
        print(f"       [OK] Plat créé avec succès ID #{prod_a_id} dans PostgreSQL")

        # Test Modification Prix & Disponibilité
        print("\n[2/10] RESTAURANT A: Modification du prix et bascule disponibilité...")
        res_patch_price = client_rest_a.patch(f'/api/pro/merchant/products/{prod_a_id}/', {'prix_base': '5000.00'}, format='json')
        if res_patch_price.status_code == 200 and Decimal(str(res_patch_price.data['prix_base'])) == Decimal('5000.00'):
            results['restaurant_modification_prix'] = True
            print("       [OK] Prix mis à jour à 5000 FCFA")

        res_toggle = client_rest_a.patch(f'/api/pro/merchant/products/{prod_a_id}/toggle-disponibilite/')
        if res_toggle.status_code == 200 and not res_toggle.data['est_disponible']:
            client_rest_a.patch(f'/api/pro/merchant/products/{prod_a_id}/toggle-disponibilite/')
            results['restaurant_toggle_disponibilite'] = True
            print("       [OK] Bascule de disponibilité validée")

        # Test Upload Image via API
        print("\n[3/10] RESTAURANT A: Upload photo de plat vers Cloudinary...")
        real_png_bytes = b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x02\x00\x00\x00\x90wS\xde\x00\x00\x00\x0cIDATx\x9cc`\x00\x00\x00\x02\x00\x01H\xaf\xa4q\x00\x00\x00\x00IEND\xaeB`\x82'
        try:
            import urllib.request
            real_mp4_bytes = urllib.request.urlopen('https://res.cloudinary.com/demo/video/upload/dog.mp4').read(100000)
        except Exception:
            real_mp4_bytes = b'\x00\x00\x00\x1cftypmp42\x00\x00\x00\x01mp41isomiso2avc1mp41\x00\x00\x00\x08free'

        fake_img = SimpleUploadedFile("plat_thieb.png", real_png_bytes, content_type="image/png")
        res_img = client_rest_a.post('/api/pro/merchant/upload-image/', {'image_file': fake_img}, format='multipart')
        print(f"       Upload Image HTTP {res_img.status_code} -> {res_img.data}")
        if res_img.status_code == 201 and 'image_url' in res_img.data and 'hcotlph6' in res_img.data['image_url']:
            results['restaurant_upload_image'] = True
            print(f"       [OK] Image téléversée sur Cloudinary: {res_img.data['image_url']}")

        # Test Upload Vidéo & Association au Plat
        print("\n[4/10] RESTAURANT A: Publication vidéo Feed & association plat...")
        fake_vid = SimpleUploadedFile("video_cooking.mp4", real_mp4_bytes, content_type="video/mp4")
        res_vid = client_rest_a.post('/api/catalog/feed/', {
            'video_file': fake_vid,
            'produit_id': prod_a_id,
            'duree_secondes': 45
        }, format='multipart')
        print(f"       Upload Vidéo HTTP {res_vid.status_code} -> {res_vid.data}")
        prod_res_data = res_vid.data.get('produit')
        prod_res_id = prod_res_data.get('id') if isinstance(prod_res_data, dict) else prod_res_data
        if res_vid.status_code == 201 and prod_res_id == prod_a_id and 'hcotlph6' in res_vid.data.get('media_url', ''):
            results['restaurant_upload_video'] = True
            results['restaurant_association_video_plat'] = True
            print(f"       [OK] Vidéo publiée et rattachée au plat #{prod_a_id}")

    # SCÉNARIO 2 : VENDEUR A - Produit & Vidéo
    print("\n[5/10] VENDEUR A (À Domicile): Création produit & publication vidéo...")
    real_vend_img = SimpleUploadedFile("ngalakh.png", real_png_bytes, content_type="image/png")
    res_vend_upload_img = client_vend_a.post('/api/pro/merchant/upload-image/', {'image_file': real_vend_img}, format='multipart')
    vend_img_url = res_vend_upload_img.data.get('image_url', '') if res_vend_upload_img.status_code == 201 else ''
    if res_vend_upload_img.status_code == 201 and 'hcotlph6' in vend_img_url:
        results['vendeur_upload_image'] = True
        print(f"       [OK] Image Vendeur téléversée sur Cloudinary: {vend_img_url}")

    res_vend_p = client_vend_a.post('/api/pro/merchant/products/', {
        'nom': 'Ngalakh Onctueux Maison',
        'description': 'Dessert traditionnel à la pâte d arachide et bouye',
        'prix_base': '2500.00',
        'categorie': categorie.id,
        'image_url': vend_img_url or 'https://res.cloudinary.com/hcotlph6/image/upload/ayyou/products/ngalakh.png',
        'est_disponible': True
    }, format='json')

    if res_vend_p.status_code == 201:
        results['vendeur_creation_produit'] = True
        vend_prod_id = res_vend_p.data['id']
        print(f"       [OK] Produit Vendeur créé avec succès ID #{vend_prod_id}")

        fake_vid_v = SimpleUploadedFile("video_ngalakh.mp4", real_mp4_bytes, content_type="video/mp4")
        res_vid_v = client_vend_a.post('/api/catalog/feed/', {
            'video_file': fake_vid_v,
            'produit_id': vend_prod_id,
            'duree_secondes': 30
        }, format='multipart')
        if res_vid_v.status_code == 201 and 'hcotlph6' in res_vid_v.data.get('media_url', ''):
            results['vendeur_upload_video'] = True
            print("       [OK] Vidéo Vendeur publiée avec succès")

    # SCÉNARIO 3 : ISOLATION MULTI-TENANT
    print("\n[6/10] Test d'ISOLATION MULTI-TENANT...")
    # Restaurant B essaie de modifier le plat de Restaurant A -> Doit renvoyer HTTP 404
    res_hacker_rest = client_rest_b.patch(f'/api/pro/merchant/products/{prod_a_id}/', {'prix_base': '1.00'}, format='json')
    if res_hacker_rest.status_code == 404:
        results['isolation_restaurant_a_b'] = True
        print("       [OK] Restaurant B rejeté (404 Not Found) sur tentative d altération du plat de Restaurant A.")

    # Vendeur B essaie de modifier le produit de Vendeur A -> HTTP 404
    res_hacker_vend = client_vend_b.patch(f'/api/pro/merchant/products/{vend_prod_id}/', {'prix_base': '1.00'}, format='json')
    if res_hacker_vend.status_code == 404:
        results['isolation_vendeur_a_b'] = True
        print("       [OK] Vendeur B rejeté (404 Not Found) sur tentative d altération du produit de Vendeur A.")

    # Restaurant A essaie de modifier le produit de Vendeur A -> HTTP 404
    res_cross_role = client_rest_a.patch(f'/api/pro/merchant/products/{vend_prod_id}/', {'prix_base': '1.00'}, format='json')
    if res_cross_role.status_code == 404:
        results['isolation_restaurant_vendeur'] = True
        print("       [OK] Cross-role isolation validée : Restaurant ne peut pas modifier un produit Vendeur.")

    # SCÉNARIO 4 : VISIBILITÉ CÔTÉ CLIENT AYYOU
    print("\n[7/10] Consultation du catalogue et du Feed par le CLIENT AYYOU...")
    res_client_prods = client_public.get('/api/catalog/products/')
    if res_client_prods.status_code == 200:
        prods_list = res_client_prods.data.get('results', res_client_prods.data)
        found_thieb = any(p['id'] == prod_a_id for p in prods_list if isinstance(p, dict))
        if found_thieb:
            results['client_visibilite_produits'] = True
            print(f"       [OK] Client voit les vrais produits créés dans le catalogue REST (Plat #{prod_a_id})")

    res_client_feed = client_public.get('/api/catalog/feed/')
    if res_client_feed.status_code == 200:
        feed_list = res_client_feed.data.get('results', res_client_feed.data)
        if len(feed_list) > 0:
            results['client_visibilite_feed_video'] = True
            print(f"       [OK] Client voit les vidéos réelles publiées dans le Feed ({len(feed_list)} vidéo(s))")

    # SCÉNARIO 5 : TEST DIRECT SERVICE CLOUDINARY
    print("\n[8/10] Test direct du service Cloudinary (Image & Vidéo)...")
    try:
        res_cloud_img = CloudinaryFeedService.upload_product_image(SimpleUploadedFile("test_direct.png", real_png_bytes, content_type="image/png"))
        if 'image_url' in res_cloud_img and 'hcotlph6' in res_cloud_img['image_url']:
            results['cloudinary_real_image_test'] = True
            print(f"       [OK] Cloudinary Image Service retour: {res_cloud_img['image_url']}")
        else:
            print("       [KO] Cloudinary Image retourné une URL non valide/mock.")
    except Exception as e:
        print(f"       [KO] Cloudinary Image test rejeté : {str(e)}")

    try:
        res_cloud_vid = CloudinaryFeedService.upload_feed_video(SimpleUploadedFile("test_direct.mp4", real_mp4_bytes, content_type="video/mp4"), duree_secondes=60)
        if 'media_url' in res_cloud_vid and 'hcotlph6' in res_cloud_vid['media_url']:
            results['cloudinary_real_video_test'] = True
            print(f"       [OK] Cloudinary Video Service retour: {res_cloud_vid['media_url']}")
        else:
            print("       [KO] Cloudinary Vidéo retourné une URL non valide/mock.")
    except Exception as e:
        print(f"       [KO] Cloudinary Vidéo test rejeté : {str(e)}")

    print("\n" + "=" * 80)
    print("RESULTAT RECAPITULATIF DES TESTS CATALOGUE, MEDIA & CLOUDINARY")

    print("=" * 80)
    for k, v in results.items():
        status_icon = "[PASSED]" if v else "[FAILED]"
        print(f" - {k:<35} : {status_icon}")
    print("=" * 80)

    return results

if __name__ == '__main__':
    run_media_and_catalog_e2e_tests()
