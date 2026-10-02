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

# Plats Street Food (ID 22) et Cuisine du Monde (ID 21)
dishes_data = [
    {
        "cat_id": 22,
        "etab_id": 125, # Street Dakar
        "src_image": "media_1790512774988.jpg",
        "dest_image": "plateau_asian_street_food_nems_tacos.jpg",
        "nom": "Plateau Asian Street Food (Soupe Nouilles, Nems & Tacos Fusion)",
        "description": "Combo ultime Street Food asiatique & fusion : Soupe de nouilles ramen épicée au bœuf effiloché, nems croustillants dorés au poulet, tacos mexicains au bœuf fondain et fromage, riz au jasmin parfumé, frites épicées maison et sauces dipping.",
        "prix_base": 7500,
        "temps_prep": 25,
        "tags": "Street Food, Asian, Nems, Tacos, Ramen, Combo",
        "variantes": [
            {"titre": "Taille du Plateau", "sous_titre": "Combo Solo", "surcout_prix": 0, "est_requis": True, "ordre": 1},
            {"titre": "Taille du Plateau", "sous_titre": "Combo XL à Partager (2-3 Pers)", "surcout_prix": 4500, "est_requis": True, "ordre": 2},
        ],
        "options": [
            {"type_option": "Sauce", "titre": "Sauces Dipping", "sous_titre": "Sauce Nems Douce & Sauce Blanche Ail", "surcout_prix": 0, "est_inclus": True, "ordre": 1},
            {"type_option": "Extra", "titre": "Extra Nems (x2)", "sous_titre": "2 Nems au poulet croustillants supplémentaires", "surcout_prix": 1500, "est_inclus": False, "ordre": 2},
            {"type_option": "Boisson", "titre": "Canette 33cl au choix", "sous_titre": "Coca, Fanta, Sprite ou Jus local", "surcout_prix": 1000, "est_inclus": False, "ordre": 3}
        ]
    },
    {
        "cat_id": 22,
        "etab_id": 127, # Chez Street Food
        "src_image": "media_1790512783550.jpg",
        "dest_image": "plateau_brochettes_wings_steak_eggs.jpg",
        "nom": "Plateau Géant Brochettes Grillées, Wings BBQ & Steak aux Œufs",
        "description": "Le roi des platteaux Street Food : Brochettes de poulet mariné grillé au feu de bois, Wings BBQ caramélisés, Steak de bœuf fondant surmonté de 2 œufs au plat, frites croquantes, Alloco (plantains frites), salade et sauces maison.",
        "prix_base": 9500,
        "temps_prep": 30,
        "tags": "Street Food, Grillades, Brochettes, Wings, Alloco, Steak",
        "variantes": [
            {"titre": "Choix de la Viande Steak", "sous_titre": "Steak de Bœuf aux Œufs Durs / Plat", "surcout_prix": 0, "est_requis": True, "ordre": 1},
            {"titre": "Choix de la Viande Steak", "sous_titre": "Côte d'Agneau Grillée aux Œufs", "surcout_prix": 1500, "est_requis": True, "ordre": 2},
        ],
        "options": [
            {"type_option": "Accompagnement", "titre": "Duo Frites & Alloco", "sous_titre": "Frites de pommes de terre & Bananes plantains", "surcout_prix": 0, "est_inclus": True, "ordre": 1},
            {"type_option": "Extra", "titre": "Portion Alloco Extra", "sous_titre": "Bananes plantains frits caramélisés", "surcout_prix": 1000, "est_inclus": False, "ordre": 2},
            {"type_option": "Sauce", "titre": "Sauce Piment Maison", "sous_titre": "Piment fort sénégalais à part", "surcout_prix": 0, "est_inclus": True, "ordre": 3}
        ]
    },
    {
        "cat_id": 22,
        "etab_id": 126, # Food Corner Dakar
        "src_image": "media_1790512794968.jpg",
        "dest_image": "mix_grill_poulet_saucisses_kefta.jpg",
        "nom": "Mix Grill Combo Street Food (Poulet Rôti, Saucisses & Keftas)",
        "description": "Assortiment gourmand Street Food : Cuisses de poulet grillées aux herbes, saucisses savoureuses braisées, médaillons de bœuf kefta épicés, montagnes de frites croustillantes, chips craquantes et duo de sauces barbecue/blanche.",
        "prix_base": 8000,
        "temps_prep": 25,
        "tags": "Street Food, Mix Grill, Poulet Rôti, Saucisses, Kefta, Frites",
        "variantes": [
            {"titre": "Taille", "sous_titre": "Planche Duo (2 Personnes)", "surcout_prix": 0, "est_requis": True, "ordre": 1},
            {"titre": "Taille", "sous_titre": "Planche XL Familiale (3-4 Personnes)", "surcout_prix": 5000, "est_requis": True, "ordre": 2},
        ],
        "options": [
            {"type_option": "Sauce", "titre": "Sauce au choix", "sous_titre": "Ketchup & Sauce Blanche aux herbes", "surcout_prix": 0, "est_inclus": True, "ordre": 1},
            {"type_option": "Extra", "titre": "Extra Kefta (x2)", "sous_titre": "2 Boulettes Kefta grillées", "surcout_prix": 1200, "est_inclus": False, "ordre": 2}
        ]
    },
    {
        "cat_id": 21,
        "etab_id": 122, # Le Comptoir International
        "src_image": "media_1790512807601.jpg",
        "dest_image": "pave_boeuf_sauce_poivre_creme.jpg",
        "nom": "Pavé de Bœuf Sauce Poivre Crémée & Pommes Rissolées",
        "description": "Grand classique de la gastronomie internationale : Tranches de pavé de bœuf tendre saisies à la perfection, recouvertes d'une sauce crémeuse au poivre vert concassé, accompagnées d'haricots verts sautés et pommes sautées à l'ail.",
        "prix_base": 9000,
        "temps_prep": 20,
        "tags": "Cuisine du monde, Pavé de Bœuf, Sauce Poivre, Gastronomie, Viande",
        "variantes": [
            {"titre": "Cuisson de la Viande", "sous_titre": "Saignant", "surcout_prix": 0, "est_requis": True, "ordre": 1},
            {"titre": "Cuisson de la Viande", "sous_titre": "À point", "surcout_prix": 0, "est_requis": True, "ordre": 2},
            {"titre": "Cuisson de la Viande", "sous_titre": "Bien cuit", "surcout_prix": 0, "est_requis": True, "ordre": 3}
        ],
        "options": [
            {"type_option": "Accompagnement", "titre": "Haricots Verts & Pommes Sautées", "sous_titre": "Légumes frais sautés au beurre", "surcout_prix": 0, "est_inclus": True, "ordre": 1},
            {"type_option": "Extra", "titre": "Sauce Poivre Supplémentaire", "sous_titre": "Ramequin de sauce poivre maison", "surcout_prix": 1000, "est_inclus": False, "ordre": 2}
        ]
    },
    {
        "cat_id": 21,
        "etab_id": 121, # World Kitchen Dakar
        "src_image": "media_1790512816116.jpg",
        "dest_image": "roti_boeuf_glace_bbq_oignons.jpg",
        "nom": "Rôti de Bœuf Brisket Glacé BBQ & Oignons Rôtis",
        "description": "Spécialité barbecue américaine & internationale : Poitrine de bœuf (Brisket) fumée et confite longuement, laquée d'une sauce BBQ sucrée-salée caramélisée, servie avec des oignons rôtis au thym et brins de romarin frais.",
        "prix_base": 8500,
        "temps_prep": 25,
        "tags": "Cuisine du monde, Brisket, BBQ, Rôti de Bœuf, Smokehouse",
        "variantes": [
            {"titre": "Portion", "sous_titre": "Portion Individuelle (350g)", "surcout_prix": 0, "est_requis": True, "ordre": 1},
            {"titre": "Portion", "sous_titre": "Portion Généreuse (550g)", "surcout_prix": 3500, "est_requis": True, "ordre": 2}
        ],
        "options": [
            {"type_option": "Accompagnement", "titre": "Oignons Rôtis & Romarin", "sous_titre": "Oignons caramélisés au four", "surcout_prix": 0, "est_inclus": True, "ordre": 1},
            {"type_option": "Sauce", "titre": "Sauce BBQ Fumée maison", "sous_titre": "Sauce dipping BBQ en pot", "surcout_prix": 0, "est_inclus": True, "ordre": 2},
            {"type_option": "Extra", "titre": "Purée de Pommes de Terre Maison", "sous_titre": "Purée onctueuse au beurre", "surcout_prix": 1500, "est_inclus": False, "ordre": 3}
        ]
    }
]

print("==================================================")
print("  POPULATION STREET FOOD (CAT 22) & CUISINE DU MONDE (CAT 21)")
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
