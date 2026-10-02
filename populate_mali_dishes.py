import os
import sys
import shutil
import django

# Configuration environnement Django
sys.path.append(r'C:\Users\HP\Desktop\Ayyou-backend')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from apps.catalog.models import Categorie, Etablissement, Produit, VarianteProduit, OptionProduit

MEDIA_DIR = r'C:\Users\HP\Desktop\Ayyou-backend\media\dishes'
os.makedirs(MEDIA_DIR, exist_ok=True)

USER_UPLOADED_DIR = r'C:\Users\HP\.gemini\antigravity\brain\1f2cd0a4-e39b-4ef8-b924-e7e0bc2d34a3\.user_uploaded'

# Plats Cuisine malienne (ID 18)
dishes_data = [
    {
        "cat_id": 18,
        "etab_id": 109, # Saveurs du Mali
        "src_image": "media_1790514332615.jpg",
        "dest_image": "tigadeguena_mafe_malien_boeuf.jpg",
        "nom": "Tigadèguèna Malien (Sauce Mafé d'Arachide au Bœuf)",
        "description": "La vraie sauce Mafé malienne (Tigadèguèna) : Pâte d'arachide artisanale dorée et mijotée longuement avec de généreux morceaux de bœuf tendre, aubergines africaines et piment frais. Servie avec riz parfumé.",
        "prix_base": 4000,
        "temps_prep": 20,
        "tags": "Cuisine malienne, Tigadèguèna, Mafé, Bœuf, Arachide, Mali",
        "variantes": [
            {"titre": "Choix de la Viande", "sous_titre": "Viande de Bœuf Tendre", "surcout_prix": 0, "est_requis": True, "ordre": 1},
            {"titre": "Choix de la Viande", "sous_titre": "Poulet Fermier Braisé", "surcout_prix": 500, "est_requis": True, "ordre": 2},
            {"titre": "Choix de la Viande", "sous_titre": "Viande de Mouton", "surcout_prix": 1000, "est_requis": True, "ordre": 3}
        ],
        "options": [
            {"type_option": "Accompagnement", "titre": "Riz Blanc Parfumé", "sous_titre": "Riz chaud cuit à la vapeur", "surcout_prix": 0, "est_inclus": True, "ordre": 1},
            {"type_option": "Accompagnement", "titre": "Tô (Bouillie de Mil/Maïs)", "sous_titre": "Accompagnement traditionnel malien", "surcout_prix": 0, "est_inclus": False, "ordre": 2},
            {"type_option": "Extra", "titre": "Extra Viande de Bœuf", "sous_titre": "2 morceaux de bœuf supplémentaires", "surcout_prix": 1500, "est_inclus": False, "ordre": 3}
        ]
    },
    {
        "cat_id": 18,
        "etab_id": 111, # Le Bamako Dakar
        "src_image": "media_1790514398266.png",
        "dest_image": "sauce_fakoye_du_nord_mali_riz.png",
        "nom": "Sauce Fakoye Authentique du Nord-Mali & Riz Blanc",
        "description": "Spécialité légendaire du Nord du Mali (Gao/Tombouctou) : Sauce foncée aux feuilles de corète potagère séchées et moulues, enrichie aux épices rares du désert et viande de bœuf/mouton. Servie avec riz blanc.",
        "prix_base": 4500,
        "temps_prep": 25,
        "tags": "Cuisine malienne, Fakoye, Nord Mali, Gao, Tombouctou, Spécialité",
        "variantes": [
            {"titre": "Viande au Choix", "sous_titre": "Morceaux de Bœuf Mijotés", "surcout_prix": 0, "est_requis": True, "ordre": 1},
            {"titre": "Viande au Choix", "sous_titre": "Gigot de Mouton du Désert", "surcout_prix": 1000, "est_requis": True, "ordre": 2},
        ],
        "options": [
            {"type_option": "Accompagnement", "titre": "Riz Blanc ou Fonio", "sous_titre": "Riz blanc brisé ou Fonio cuit à la vapeur", "surcout_prix": 0, "est_inclus": True, "ordre": 1},
            {"type_option": "Extra", "titre": "Sauce Fakoye Supplémentaire", "sous_titre": "Ramequin de sauce Fakoye extra", "surcout_prix": 1200, "est_inclus": False, "ordre": 2}
        ]
    },
    {
        "cat_id": 18,
        "etab_id": 110, # Maïga Cuisine
        "src_image": "media_1790514472726.jpg",
        "dest_image": "djouka_malien_fonio_poulet_braise.jpg",
        "nom": "Djouka Malien au Fonio & Poulet Braisé aux Oignons",
        "description": "Plat traditionnel savoureux : Couscous de Fonio fin mélangé à la pâte d'arachide torréfiée et épices Djouka, accompagné d'une cuisse de poulet braisée bien dorée et confit d'oignons citronnés.",
        "prix_base": 4000,
        "temps_prep": 20,
        "tags": "Cuisine malienne, Djouka, Fonio, Poulet Braisé, Arachide, Mali",
        "variantes": [
            {"titre": "Portion", "sous_titre": "Portion Poulet Yassa / Braisé", "surcout_prix": 0, "est_requis": True, "ordre": 1},
            {"titre": "Portion", "sous_titre": "Portion Viande de Bœuf Grillée", "surcout_prix": 500, "est_requis": True, "ordre": 2},
        ],
        "options": [
            {"type_option": "Accompagnement", "titre": "Confit d'Oignons Citronné", "sous_titre": "Sauce aux oignons braisés", "surcout_prix": 0, "est_inclus": True, "ordre": 1},
            {"type_option": "Extra", "titre": "Extra Cuisse de Poulet", "sous_titre": "1 cuisse de poulet braisée en plus", "surcout_prix": 1500, "est_inclus": False, "ordre": 2}
        ]
    },
    {
        "cat_id": 18,
        "etab_id": 112, # Chez Aïcha Mali
        "src_image": "media_1790514520260.png",
        "dest_image": "widjila_malien_pains_vapeur_sauce_viande.png",
        "nom": "Widjila Malien (Pains à la Vapeur) & Sauce Viande Épicée",
        "description": "Spécialité très prisée au Mali : Petits boules de pain blanc ultra moelleuses cuites à la vapeur (Widjila), accompagnées d'un bol de sauce tomate-viande richement épicée et mijotée.",
        "prix_base": 3500,
        "temps_prep": 20,
        "tags": "Cuisine malienne, Widjila, Pain Vapeur, Sauce Viande, Traditionnel",
        "variantes": [
            {"titre": "Nombre de Pains Widjila", "sous_titre": "Portion 5 Pains Widjila + Sauce", "surcout_prix": 0, "est_requis": True, "ordre": 1},
            {"titre": "Nombre de Pains Widjila", "sous_titre": "Portion 8 Pains Widjila + Grande Sauce", "surcout_prix": 1500, "est_requis": True, "ordre": 2},
        ],
        "options": [
            {"type_option": "Sauce", "titre": "Sauce Viande Épicée", "sous_titre": "Sauce concentrée à la tomate et viande hachée", "surcout_prix": 0, "est_inclus": True, "ordre": 1},
            {"type_option": "Extra", "titre": "Extra Widjila (x3)", "sous_titre": "3 pains vapeur supplémentaires", "surcout_prix": 800, "est_inclus": False, "ordre": 2}
        ]
    }
]

print("==================================================")
print("  POPULATION CUISINE MALIENNE (CAT 18)")
print("==================================================")

created_count = 0
for item in dishes_data:
    cat = Categorie.objects.get(id=item["cat_id"])
    etab = Etablissement.objects.get(id=item["etab_id"])
    
    # Copy file to media/dishes
    src_path = os.path.join(USER_UPLOADED_DIR, item["src_image"])
    dest_path = os.path.join(MEDIA_DIR, item["dest_image"])
    
    if os.path.exists(src_path):
        shutil.copy(src_path, dest_path)
        print(f"Copied {item['src_image']} -> {item['dest_image']}")
    else:
        print(f"WARNING: File {src_path} not found!")

    image_url = f"http://127.0.0.1:8000/media/dishes/{item['dest_image']}"

    # Supprimer les anciens produits identiques s'ils existent pour éviter doublon
    Produit.objects.filter(etablissement=etab, nom=item["nom"]).delete()

    produit = Produit.objects.create(
        etablissement=etab,
        categorie=cat,
        nom=item["nom"],
        description=item["description"],
        prix_base=item["prix_base"],
        temps_preparation=item["temps_prep"],
        image_url=image_url,
        est_disponible=True,
        stock_disponible=50,
        stock_ayyou_reserve=10,
        tags=item["tags"]
    )
    created_count += 1
    print(f"OK: Plat [{produit.id}] '{produit.nom[:35]}...' créé pour '{etab.nom}' dans Categorie {cat.nom}")

    # Variantes
    for v_data in item["variantes"]:
        VarianteProduit.objects.create(
            produit=produit,
            titre=v_data["titre"],
            sous_titre=v_data["sous_titre"],
            surcout_prix=v_data["surcout_prix"],
            est_requis=v_data["est_requis"],
            ordre=v_data["ordre"]
        )

    # Options
    for o_data in item["options"]:
        OptionProduit.objects.create(
            produit=produit,
            type_option=o_data["type_option"],
            titre=o_data["titre"],
            sous_titre=o_data["sous_titre"],
            surcout_prix=o_data["surcout_prix"],
            est_inclus=o_data["est_inclus"],
            ordre=o_data["ordre"]
        )

print(f"\nTOTAL PLATS CREES: {created_count}")
