import os
import sys
import shutil
import django

sys.path.append('c:\\Users\\HP\\Desktop\\Ayyou-backend')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from apps.catalog.models import Categorie, Etablissement, Produit, VarianteProduit, OptionProduit

print("==================================================")
print("  POPULATION DES COUPES DE GLACES ARTISANALES (CATEGORIE 17)")
print("==================================================")

# Source images
SOURCE_DIR = r"C:\Users\HP\.gemini\antigravity\brain\1f2cd0a4-e39b-4ef8-b924-e7e0bc2d34a3\.user_uploaded"
DEST_DIR = r"C:\Users\HP\Desktop\Ayyou-backend\media\dishes"

os.makedirs(DEST_DIR, exist_ok=True)

IMAGE_MAPPINGS = {
    "coupe_glace_vanille_caramel_pecan.jpg": "media_1790508663234.jpg",
    "coupe_glace_stracciatella_chocolat.png": "media_1790508683621.png",
    "coupe_glace_pistache_amandes.jpg": "media_1790508693784.jpg",
    "coupe_glace_tout_chocolat_pepites.jpg": "media_1790508706205.jpg"
}

for dest_name, src_name in IMAGE_MAPPINGS.items():
    src_path = os.path.join(SOURCE_DIR, src_name)
    dest_path = os.path.join(DEST_DIR, dest_name)
    if os.path.exists(src_path):
        shutil.copy(src_path, dest_path)
        print(f"Copied {src_name} -> {dest_name}")
    else:
        print(f"WARNING: {src_path} not found!")

cat_official = Categorie.objects.get(id=17)
print(f"Categorie officielle: {cat_official.nom} (ID {cat_official.id})")

GLACE_DISHES = [
    {
        "etablissement_nom": "Glaces Dakar",
        "nom": "Coupe Glacée Sundae Vanille, Caramel Beurre Salé & Noix de Pécan",
        "description": "Boules généreuses de glace artisanale à la vanille de Madagascar, nappées d'une sauce caramel coulant au beurre salé et parsemées de noix de pécan torréfiées.",
        "prix_base": 3000.00,
        "image_url": "http://127.0.0.1:8000/media/dishes/coupe_glace_vanille_caramel_pecan.jpg",
        "temps_preparation": "05 min",
        "tags": ["Glace Vanille", "Caramel Beurre Salé", "Noix de Pécan", "Glaces Dakar", "Gourmet"],
        "variantes": [
            {"titre": "Coupe 2 Boules Gourmandes", "sous_titre": "2 boules vanille, caramel & pécan", "surcout_prix": 0.00, "est_requis": True, "ordre": 1},
            {"titre": "Coupe XL 4 Boules", "sous_titre": "4 boules gourmandes avec supplément noix", "surcout_prix": 1500.00, "est_requis": False, "ordre": 2},
        ],
        "options": [
            {"type_option": OptionProduit.TYPE_SUPPLEMENT, "titre": "Chantilly Maison", "sous_titre": "Crème chantilly fouettée", "surcout_prix": 300.00, "est_inclus": True, "ordre": 1},
            {"type_option": OptionProduit.TYPE_SUPPLEMENT, "titre": "Extra Coulis Caramel", "sous_titre": "Nappage caramel chaud", "surcout_prix": 200.00, "est_inclus": False, "ordre": 2},
        ]
    },
    {
        "etablissement_nom": "Douceurs de Dakar",
        "nom": "Coupe Artisanale Stracciatella & Copeaux de Chocolat Noir",
        "description": "Crémeuse glace artisanale Stracciatella préparée au lait frais entier, enrichie d'une abondance de pépites et de gros copeaux de chocolat noir 70%.",
        "prix_base": 2800.00,
        "image_url": "http://127.0.0.1:8000/media/dishes/coupe_glace_stracciatella_chocolat.png",
        "temps_preparation": "05 min",
        "tags": ["Stracciatella", "Chocolat Noir", "Douceurs de Dakar", "Artisanal", "Copeaux"],
        "variantes": [
            {"titre": "Coupe Stracciatella 2 Boules", "sous_titre": "2 boules stracciatella & copeaux chocolat", "surcout_prix": 0.00, "est_requis": True, "ordre": 1},
            {"titre": "Coupe Stracciatella 3 Boules", "sous_titre": "3 boules généreuses", "surcout_prix": 1000.00, "est_requis": False, "ordre": 2},
        ],
        "options": [
            {"type_option": OptionProduit.TYPE_SUPPLEMENT, "titre": "Biscuits Cigarettes Russe", "sous_titre": "Deux gaufrettes croustillantes", "surcout_prix": 200.00, "est_inclus": True, "ordre": 1},
            {"type_option": OptionProduit.TYPE_SUPPLEMENT, "titre": "Nappage Chocolat Fondant", "sous_titre": "Sauce chocolat chaud", "surcout_prix": 250.00, "est_inclus": False, "ordre": 2},
        ]
    },
    {
        "etablissement_nom": "Teranga Saveurs",
        "nom": "Coupe Glacée Pistache de Sicile, Amandes & Éclats de Pistaches",
        "description": "Glace artisanale parfumée à la pâte de pistache pure de Sicile, surmontée d'un nappage blanc soyeux, d'amandes grillées et d'éclats de pistaches croquantes.",
        "prix_base": 3200.00,
        "image_url": "http://127.0.0.1:8000/media/dishes/coupe_glace_pistache_amandes.jpg",
        "temps_preparation": "05 min",
        "tags": ["Glace Pistache", "Amandes Grillées", "Teranga Saveurs", "Sicile", "Luxe"],
        "variantes": [
            {"titre": "Coupe Pistache 2 Boules", "sous_titre": "2 boules pistache & amandes grillées", "surcout_prix": 0.00, "est_requis": True, "ordre": 1},
            {"titre": "Coupe Royale Pistache 3 Boules", "sous_titre": "3 boules pistache avec extra fruits secs", "surcout_prix": 1200.00, "est_requis": False, "ordre": 2},
        ],
        "options": [
            {"type_option": OptionProduit.TYPE_SUPPLEMENT, "titre": "Extra Éclats de Pistaches", "sous_titre": "Pistaches torréfiées", "surcout_prix": 300.00, "est_inclus": True, "ordre": 1},
        ]
    },
    {
        "etablissement_nom": "Chez Penda",
        "nom": "Coupe Glacée Tout Chocolat Supérieur & Pépites Fondantes",
        "description": "Pour les passionnés de cacao : boules de glace au chocolat noir intense de Côte d'Ivoire, nappées de sauce chocolat chaud faite maison et parsemées de pépites de chocolat.",
        "prix_base": 2900.00,
        "image_url": "http://127.0.0.1:8000/media/dishes/coupe_glace_tout_chocolat_pepites.jpg",
        "temps_preparation": "05 min",
        "tags": ["Tout Chocolat", "Chez Penda", "Chocolat Intense", "Pépites", "Nappage Chaud"],
        "variantes": [
            {"titre": "Coupe Chocolat 2 Boules", "sous_titre": "2 boules chocolat intense & pépites", "surcout_prix": 0.00, "est_requis": True, "ordre": 1},
            {"titre": "Coupe Chocolat Maniac 4 Boules", "sous_titre": "4 boules avec double nappage chocolat", "surcout_prix": 1600.00, "est_requis": False, "ordre": 2},
        ],
        "options": [
            {"type_option": OptionProduit.TYPE_SUPPLEMENT, "titre": "Chantilly Chocolatée", "sous_titre": "Chantilly au cacao", "surcout_prix": 250.00, "est_inclus": True, "ordre": 1},
        ]
    }
]

created_count = 0
for d in GLACE_DISHES:
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
    print(f"OK: Plat Coupe de Glace [{produit.id}] '{produit.nom[:30]}...' cree pour {etab.nom}")

print(f"\nTOTAL PLATS COUPES DE GLACES CREES: {created_count}")
