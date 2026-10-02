import os
import sys
import shutil
import django

sys.path.append('c:\\Users\\HP\\Desktop\\Ayyou-backend')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from apps.catalog.models import Categorie, Etablissement, Produit, VarianteProduit, OptionProduit

print("==================================================")
print("  POPULATION DU PLACALI / SAUCE GRAINE (CATEGORIE 13)")
print("==================================================")

# Source images
SOURCE_DIR = r"C:\Users\HP\.gemini\antigravity\brain\1f2cd0a4-e39b-4ef8-b924-e7e0bc2d34a3\.user_uploaded"
DEST_DIR = r"C:\Users\HP\Desktop\Ayyou-backend\media\dishes"

os.makedirs(DEST_DIR, exist_ok=True)

IMAGE_MAPPINGS = {
    "placali_sauce_graine_terre_cuite.png": "media_1790505210263.png",
    "placali_sauce_kope_crabes_crevettes.jpg": "media_1790505222225.jpg",
    "placali_sauce_graine_crabe_poisson.jpg": "media_1790505232576.jpg",
    "placali_sauce_graine_poulet.jpg": "media_1790505251783.jpg"
}

for dest_name, src_name in IMAGE_MAPPINGS.items():
    src_path = os.path.join(SOURCE_DIR, src_name)
    dest_path = os.path.join(DEST_DIR, dest_name)
    if os.path.exists(src_path):
        shutil.copy(src_path, dest_path)
        print(f"Copied {src_name} -> {dest_name}")
    else:
        print(f"WARNING: {src_path} not found!")

cat_official = Categorie.objects.get(id=13)
print(f"Categorie officielle: {cat_official.nom} (ID {cat_official.id})")

PLACALI_DISHES = [
    {
        "etablissement_nom": "Maquis Abidjan Dakar",
        "nom": "Placali Traditionnel servi en Bol Terre Cuite & Sauce Graine",
        "description": "Recette authentique ivoirienne : boule de Placali (pâte de manioc fermentée étuvée) servie dans un bol traditionnel en terre cuite avec une riche sauce Graine aux fruits du palier, viande de bœuf & crevettes.",
        "prix_base": 4800.00,
        "image_url": "http://127.0.0.1:8000/media/dishes/placali_sauce_graine_terre_cuite.png",
        "temps_preparation": "15-20 min",
        "tags": ["Placali", "Sauce Graine", "Maquis Abidjan", "Terre Cuite", "Manioc"],
        "variantes": [
            {"titre": "Portion Bol Terre Cuite 1 Personne", "sous_titre": "Boule de Placali & sauce graine bœuf", "surcout_prix": 0.00, "est_requis": True, "ordre": 1},
            {"titre": "Portion Duo Maquis", "sous_titre": "Deux boules de Placali & extra sauce graine", "surcout_prix": 2500.00, "est_requis": False, "ordre": 2},
        ],
        "options": [
            {"type_option": OptionProduit.TYPE_SAUCE, "titre": "Sauce Piment Jaune Akpi", "sous_titre": "Sauce piquante aux épices akpi", "surcout_prix": 200.00, "est_inclus": True, "ordre": 1},
            {"type_option": OptionProduit.TYPE_SUPPLEMENT, "titre": "Extra Boule de Placali", "sous_titre": "Boule de pâte de manioc supplémentaire", "surcout_prix": 600.00, "est_inclus": False, "ordre": 2},
        ]
    },
    {
        "etablissement_nom": "Saveurs de Côte d'Ivoire",
        "nom": "Placali Sauce Kopè Royale aux Crabes & Crevettes Géantes",
        "description": "Gourmandise ivoirienne d'exception : boule de Placali sculptée dans un bol de terre cuite, noyée dans une onctueuse sauce Kopè (sauce gombo battue à l'huile de palme) garnie de crabes royaux et crevettes.",
        "prix_base": 5800.00,
        "image_url": "http://127.0.0.1:8000/media/dishes/placali_sauce_kope_crabes_crevettes.jpg",
        "temps_preparation": "20-25 min",
        "tags": ["Placali Kopè", "Sauce Gombo", "Crabes", "Crevettes", "Saveurs CI"],
        "variantes": [
            {"titre": "Assiette Kopè Royale 1 Personne", "sous_titre": "Placali, crabes royaux & gombo", "surcout_prix": 0.00, "est_requis": True, "ordre": 1},
            {"titre": "Plateau Kopè Prestige Familial", "sous_titre": "Portion 2-3 personnes avec double crabe", "surcout_prix": 4500.00, "est_requis": False, "ordre": 2},
        ],
        "options": [
            {"type_option": OptionProduit.TYPE_SAUCE, "titre": "Piment Rouge Végétalien", "sous_titre": "Purée piment fort", "surcout_prix": 200.00, "est_inclus": True, "ordre": 1},
            {"type_option": OptionProduit.TYPE_SUPPLEMENT, "titre": "Supplément Crabe Royal (x1)", "sous_titre": "Crabe décortiqué", "surcout_prix": 1200.00, "est_inclus": False, "ordre": 2},
        ]
    },
    {
        "etablissement_nom": "Chez Aya Ivoire",
        "nom": "Placali Dôme Sculpté, Sauce Graine, Poisson Fumé & Crabe",
        "description": "Dôme de Placali blanc sculpté avec précision, servi sur grande assiette dans une sauce graine mijotée aux pelles de pince de crabe, poisson fumé du fleuve et piments entiers.",
        "prix_base": 5200.00,
        "image_url": "http://127.0.0.1:8000/media/dishes/placali_sauce_graine_crabe_poisson.jpg",
        "temps_preparation": "15-20 min",
        "tags": ["Placali Dôme", "Chez Aya Ivoire", "Poisson Fumé", "Crabe", "Sauce Graine"],
        "variantes": [
            {"titre": "Assiette Dôme Aya", "sous_titre": "Placali dôme, poisson fumé & crabe", "surcout_prix": 0.00, "est_requis": True, "ordre": 1},
            {"titre": "Formule XL Dôme Double Viande", "sous_titre": "Avec viande de bœuf & poisson fumé", "surcout_prix": 2200.00, "est_requis": False, "ordre": 2},
        ],
        "options": [
            {"type_option": OptionProduit.TYPE_SAUCE, "titre": "Sauce Gombo Séparée", "sous_titre": "Petit ramequin sauce gombo", "surcout_prix": 300.00, "est_inclus": False, "ordre": 1},
            {"type_option": OptionProduit.TYPE_SUPPLEMENT, "titre": "Extra Poisson Fumé", "sous_titre": "Morceau de poisson fumé", "surcout_prix": 800.00, "est_inclus": False, "ordre": 2},
        ]
    },
    {
        "etablissement_nom": "Ivoire Saveurs",
        "nom": "Placali Sauce Graine & Pilon de Poulet Braisé",
        "description": "Fusion gourmande : boule de Placali moelleuse accompagnée d'une sauce graine riche à l'huile de palme purifiée, relevée d'un filet de sauce gombo verte et d'un gros pilon de poulet braisé.",
        "prix_base": 4500.00,
        "image_url": "http://127.0.0.1:8000/media/dishes/placali_sauce_graine_poulet.jpg",
        "temps_preparation": "15-20 min",
        "tags": ["Placali Poulet", "Ivoire Saveurs", "Sauce Graine", "Pilon Braisé"],
        "variantes": [
            {"titre": "Assiette Placali Poulet Standard", "sous_titre": "Placali & pilon de poulet braisé", "surcout_prix": 0.00, "est_requis": True, "ordre": 1},
            {"titre": "Assiette Gourmande Double Pilon", "sous_titre": "Deux pilons de poulet braisés", "surcout_prix": 1500.00, "est_requis": False, "ordre": 2},
        ],
        "options": [
            {"type_option": OptionProduit.TYPE_SAUCE, "titre": "Sauce Piment Vert Ail", "sous_titre": "Sauce piquante à l'ail", "surcout_prix": 150.00, "est_inclus": True, "ordre": 1},
            {"type_option": OptionProduit.TYPE_SUPPLEMENT, "titre": "Extra Sauce Graine", "sous_titre": "Portion supplémentaire de sauce", "surcout_prix": 500.00, "est_inclus": False, "ordre": 2},
        ]
    }
]

created_count = 0
for d in PLACALI_DISHES:
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
    print(f"OK: Plat Placali / Sauce Graine [{produit.id}] '{produit.nom[:30]}...' cree pour {etab.nom}")

print(f"\nTOTAL PLATS PLACALI / SAUCE GRAINE CREES: {created_count}")
