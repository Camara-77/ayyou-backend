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

# Plats Fruits (ID 23)
dishes_data = [
    {
        "cat_id": 23,
        "etab_id": 130, # Le Panier Tropical
        "src_image": "media_1790514055741.png",
        "dest_image": "salade_fruits_mangue_banane_fraise_yaourt.png",
        "nom": "Coupe Salade de Fruits Mangue, Banane & Fraise au Yaourt",
        "description": "Coupe gourmande de dés de mangue tropicale sucrée, rondelles de banane fraîche et fraises juteuses, liées d'un lit de yaourt vanillé onctueux.",
        "prix_base": 3000,
        "temps_prep": 10,
        "tags": "Fruits, Salade de Fruits, Mangue, Fraise, Banane, Yaourt",
        "variantes": [
            {"titre": "Taille du Bol", "sous_titre": "Bol Médium (350ml)", "surcout_prix": 0, "est_requis": True, "ordre": 1},
            {"titre": "Taille du Bol", "sous_titre": "Bol XL Gourmand (500ml)", "surcout_prix": 1500, "est_requis": True, "ordre": 2},
        ],
        "options": [
            {"type_option": "Base", "titre": "Liant au choix", "sous_titre": "Yaourt vanille léger ou Sirop de miel bio", "surcout_prix": 0, "est_inclus": True, "ordre": 1},
            {"type_option": "Extra", "titre": "Coulis de Miel pur & Menthe", "sous_titre": "Nappage de miel d'acacia", "surcout_prix": 500, "est_inclus": False, "ordre": 2},
            {"type_option": "Extra", "titre": "Portion Chantilly Maison", "sous_titre": "Dôme de crème chantilly", "surcout_prix": 500, "est_inclus": False, "ordre": 3}
        ]
    },
    {
        "cat_id": 23,
        "etab_id": 129, # Fruits Frais Dakar
        "src_image": "media_1790514067109.png",
        "dest_image": "salade_fruits_exotiques_kiwi_myrtilles.png",
        "nom": "Salade de Fruits Exotiques, Kiwis & Myrtilles au Sirop",
        "description": "Mélange rafraîchissant de kiwis tranchés, myrtilles fraîches, fraises, dés de mangue, pommes et raisins sans pépins, arrosés d'un léger sirop de fleur d'oranger.",
        "prix_base": 3500,
        "temps_prep": 10,
        "tags": "Fruits, Fruits Exotiques, Kiwi, Myrtilles, Fraise, Rafraîchissant",
        "variantes": [
            {"titre": "Format", "sous_titre": "Coupe Individuelle (400g)", "surcout_prix": 0, "est_requis": True, "ordre": 1},
            {"titre": "Format", "sous_titre": "Saladier Partage (800g)", "surcout_prix": 3000, "est_requis": True, "ordre": 2},
        ],
        "options": [
            {"type_option": "Extra", "titre": "Feuilles de Menthe Fraîche", "sous_titre": "Menthe ciselée", "surcout_prix": 0, "est_inclus": True, "ordre": 1},
            {"type_option": "Extra", "titre": "Graines de Chia & Granola", "sous_titre": "Topping croustillant healthy", "surcout_prix": 800, "est_inclus": False, "ordre": 2}
        ]
    },
    {
        "cat_id": 23,
        "etab_id": 107, # Sweet Ice Dakar
        "src_image": "media_1790514081408.jpg",
        "dest_image": "trifle_fruits_rouges_peche_crumble.jpg",
        "nom": "Trifle Gourmet Fruits Rouges, Pêches & Crumble Croustillant",
        "description": "Dessert fruité et croquant composé de couches successives de pêches mûres, framboises, mûres et fraises, crème mascarpone légère et sablé crumble au beurre.",
        "prix_base": 4000,
        "temps_prep": 15,
        "tags": "Fruits, Trifle, Fruits Rouges, Pêche, Crumble, Dessert",
        "variantes": [
            {"titre": "Taille", "sous_titre": "Verrine Individuelle", "surcout_prix": 0, "est_requis": True, "ordre": 1},
            {"titre": "Taille", "sous_titre": "Grande Verrine Royale", "surcout_prix": 1500, "est_requis": True, "ordre": 2},
        ],
        "options": [
            {"type_option": "Topping", "titre": "Crumble Sablé & Menthe", "sous_titre": "Sablé doré croustillant", "surcout_prix": 0, "est_inclus": True, "ordre": 1},
            {"type_option": "Extra", "titre": "Boule de Glace Vanille", "sous_titre": "Glace artisanale vanille", "surcout_prix": 1000, "est_inclus": False, "ordre": 2}
        ]
    },
    {
        "cat_id": 23,
        "etab_id": 131, # Marché des Fruits
        "src_image": "media_1790514100104.jpg",
        "dest_image": "salade_fruits_saison_banane_raisins_clementine.jpg",
        "nom": "Salade de Fruits Frais de Saison (Banane, Raisins & Clémentines)",
        "description": "Le plein de vitamines ! Bol multicolore garni de bananes fraîches, raisins verts et noirs sucrés, quartiers de clémentines juteuses et morceaux d'ananas frais.",
        "prix_base": 2500,
        "temps_prep": 10,
        "tags": "Fruits, Vitamines, Raisins, Clémentines, Banane, Ananas",
        "variantes": [
            {"titre": "Portion", "sous_titre": "Bol Standard (300g)", "surcout_prix": 0, "est_requis": True, "ordre": 1},
            {"titre": "Portion", "sous_titre": "Grand Bol Vitaminé (500g)", "surcout_prix": 1500, "est_requis": True, "ordre": 2},
        ],
        "options": [
            {"type_option": "Jus", "titre": "Jus de Citron Vert Pressé", "sous_titre": "Arrosage au citron vert frais", "surcout_prix": 0, "est_inclus": True, "ordre": 1},
            {"type_option": "Extra", "titre": "Noix de Coco Râpée", "sous_titre": "Topping coco séchée", "surcout_prix": 500, "est_inclus": False, "ordre": 2}
        ]
    }
]

print("==================================================")
print("  POPULATION SALADES DE FRUITS (CAT 23)")
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
