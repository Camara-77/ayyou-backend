import os
import sys
import shutil
import django

sys.path.append('c:\\Users\\HP\\Desktop\\Ayyou-backend')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from apps.catalog.models import Categorie, Etablissement, Produit, VarianteProduit, OptionProduit

print("==================================================")
print("  POPULATION DES BROCHETTES DE CREVETTES (CATEGORIE 12)")
print("==================================================")

# Source images
SOURCE_DIR = r"C:\Users\HP\.gemini\antigravity\brain\1f2cd0a4-e39b-4ef8-b924-e7e0bc2d34a3\.user_uploaded"
DEST_DIR = r"C:\Users\HP\Desktop\Ayyou-backend\media\dishes"

os.makedirs(DEST_DIR, exist_ok=True)

IMAGE_MAPPINGS = {
    "brochette_crevette_persillade.png": "media_1790503565061.png",
    "brochette_crevette_poivrons.jpg": "media_1790503582500.jpg",
    "brochette_crevette_mais_saucisse.jpg": "media_1790503602199.jpg",
    "brochette_gambas_braises.jpg": "media_1790503613174.jpg"
}

for dest_name, src_name in IMAGE_MAPPINGS.items():
    src_path = os.path.join(SOURCE_DIR, src_name)
    dest_path = os.path.join(DEST_DIR, dest_name)
    if os.path.exists(src_path):
        shutil.copy(src_path, dest_path)
        print(f"Copied {src_name} -> {dest_name}")
    else:
        print(f"WARNING: {src_path} not found!")

cat_official = Categorie.objects.get(id=12)
print(f"Categorie officielle: {cat_official.nom} (ID {cat_official.id})")

CREVETTE_DISHES = [
    {
        "etablissement_nom": "Le Poisson de Dakar",
        "nom": "Brochettes de Crevettes Géantes Marinées Ail & Persillade",
        "description": "Brochettes de crevettes royales décortiquées marinées au beurre d'ail, persil frais du jardin, paprika doux et jus de citron vert pressé, saisies à la planche.",
        "prix_base": 6500.00,
        "image_url": "http://127.0.0.1:8000/media/dishes/brochette_crevette_persillade.png",
        "temps_preparation": "15-20 min",
        "tags": ["Brochettes Crevettes", "Le Poisson de Dakar", "Persillade", "Ail & Beurre", "Gambas"],
        "variantes": [
            {"titre": "Portion 3 Brochettes Géantes", "sous_titre": "Servies avec riz persillé ou frites", "surcout_prix": 0.00, "est_requis": True, "ordre": 1},
            {"titre": "Plateau 6 Brochettes XL", "sous_titre": "Grand plateau pour 2 personnes", "surcout_prix": 5500.00, "est_requis": False, "ordre": 2},
        ],
        "options": [
            {"type_option": OptionProduit.TYPE_SAUCE, "titre": "Sauce Beurre-Citronnelle", "sous_titre": "Sauce onctueuse aux herbes", "surcout_prix": 300.00, "est_inclus": True, "ordre": 1},
            {"type_option": OptionProduit.TYPE_SUPPLEMENT, "titre": "Portion de Rice Pilaf Extra", "sous_titre": "Riz aux petits légumes", "surcout_prix": 800.00, "est_inclus": False, "ordre": 2},
        ]
    },
    {
        "etablissement_nom": "Poisson Frais Chez Ali",
        "nom": "Brochettes de Gambas aux Poivrons Triangulaires & Oignons",
        "description": "Grosses gambas fraîches alternées sur pique de bois avec dés de poivrons rouges, verts, jaunes croquants et pétales d'oignons rouges mariné au poivre noir.",
        "prix_base": 6000.00,
        "image_url": "http://127.0.0.1:8000/media/dishes/brochette_crevette_poivrons.jpg",
        "temps_preparation": "15-20 min",
        "tags": ["Gambas", "Chez Ali", "Poivrons", "Brochettes", "Grillé"],
        "variantes": [
            {"titre": "Assiette 3 Brochettes Gambas", "sous_titre": "Avec accompagnement frites ou alloco", "surcout_prix": 0.00, "est_requis": True, "ordre": 1},
            {"titre": "Plat 5 Brochettes Gourmandes", "sous_titre": "Portion généreuse avec double garniture", "surcout_prix": 3500.00, "est_requis": False, "ordre": 2},
        ],
        "options": [
            {"type_option": OptionProduit.TYPE_SAUCE, "titre": "Sauce Tartare Maison", "sous_titre": "Sauce froide mayonnaise & câpres", "surcout_prix": 200.00, "est_inclus": True, "ordre": 1},
            {"type_option": OptionProduit.TYPE_SUPPLEMENT, "titre": "Bananes Alloco Frites Extra", "sous_titre": "Portion alloco", "surcout_prix": 1000.00, "est_inclus": False, "ordre": 2},
        ]
    },
    {
        "etablissement_nom": "Le Baobab Gourmand",
        "nom": "Brochettes Mixed Gambas, Maïs Grillé & Saucisses Fumées",
        "description": "Brochettes barbecue gourmandes réunissant crevettes roses marinées, tranches de maïs doux grillé à la braise et rondelles de saucisses fumées assaisonnées.",
        "prix_base": 7000.00,
        "image_url": "http://127.0.0.1:8000/media/dishes/brochette_crevette_mais_saucisse.jpg",
        "temps_preparation": "20-25 min",
        "tags": ["Mixed Grill", "Baobab Gourmand", "Maïs Grillé", "Crevettes", "Saucisses"],
        "variantes": [
            {"titre": "Assiette Barbecue 3 Brochettes", "sous_titre": "Crevettes, maïs & saucisse fumée", "surcout_prix": 0.00, "est_requis": True, "ordre": 1},
            {"titre": "Plateau Barbecue XXL 5 Brochettes", "sous_titre": "Grand format BBQ à partager", "surcout_prix": 4500.00, "est_requis": False, "ordre": 2},
        ],
        "options": [
            {"type_option": OptionProduit.TYPE_SAUCE, "titre": "Sauce BBQ Épicée", "sous_titre": "Sauce barbecue fumée", "surcout_prix": 200.00, "est_inclus": True, "ordre": 1},
            {"type_option": OptionProduit.TYPE_SUPPLEMENT, "titre": "Épi de Maïs Grillé Extra", "sous_titre": "Maïs entier au beurre", "surcout_prix": 500.00, "est_inclus": False, "ordre": 2},
        ]
    },
    {
        "etablissement_nom": "Teranga Saveurs",
        "nom": "Gambas Royales Grillées en Direct au Charbon de Bois",
        "description": "Grandes gambas sélectionnées sur la grande grille métallique au-dessus du charbon incandescent, marinées au piment doux, ail pilé et persil frais.",
        "prix_base": 7500.00,
        "image_url": "http://127.0.0.1:8000/media/dishes/brochette_gambas_braises.jpg",
        "temps_preparation": "15-20 min",
        "tags": ["Gambas Braisées", "Teranga Saveurs", "Charbon de Bois", "Grillade Directe"],
        "variantes": [
            {"titre": "Brochettes Gambas Charbon (4 piques)", "sous_titre": "Gambas braisées au charbon", "surcout_prix": 0.00, "est_requis": True, "ordre": 1},
            {"titre": "Plateau Gambas Royale (8 piques)", "sous_titre": "Portion XXL 2 personnes", "surcout_prix": 6000.00, "est_requis": False, "ordre": 2},
        ],
        "options": [
            {"type_option": OptionProduit.TYPE_SAUCE, "titre": "Sauce Piment Citron Vert", "sous_titre": "Piquant & acidulé", "surcout_prix": 200.00, "est_inclus": True, "ordre": 1},
            {"type_option": OptionProduit.TYPE_SUPPLEMENT, "titre": "Portion Frites de Patate Douce", "sous_titre": "Frites patate douce frites", "surcout_prix": 1200.00, "est_inclus": False, "ordre": 2},
        ]
    }
]

created_count = 0
for d in CREVETTE_DISHES:
    etab = Etablissement.objects.filter(nom__icontains=d["etablissement_nom"]).first()
    if not etab:
        print(f"Etablissement '{d['etablissement_nom']}' non trouve dans la BD.")
        continue
    
    produit, _ = Produit.objects.update_or_create(
        etablissement=etab,
        nom=d["nom"],
        defaults={
            "categorie": cat_official,
            "description": d["description"],
            "prix_base": d["prix_base"],
            "image_url": d["image_url"],
            "temps_preparation": d["temps_preparation"],
            "tags": d["tags"],
            "est_disponible": True,
            "stock_disponible": 100,
            "stock_ayyou_reserve": 50,
        }
    )
    
    produit.variantes.all().delete()
    for v in d["variantes"]:
        VarianteProduit.objects.create(
            produit=produit,
            titre=v["titre"],
            sous_titre=v["sous_titre"],
            surcout_prix=v["surcout_prix"],
            est_requis=v["est_requis"],
            ordre=v["ordre"]
        )
        
    produit.options.all().delete()
    for opt in d["options"]:
        OptionProduit.objects.create(
            produit=produit,
            type_option=opt["type_option"],
            titre=opt["titre"],
            sous_titre=opt["sous_titre"],
            surcout_prix=opt["surcout_prix"],
            est_inclus=opt["est_inclus"],
            ordre=opt["ordre"]
        )
        
    created_count += 1
    print(f"OK: Plat Brochettes Crevettes [{produit.id}] '{produit.nom[:30]}...' cree pour {etab.nom}")

print(f"\nTOTAL PLATS BROCHETTES CREVETTES CREES: {created_count}")
