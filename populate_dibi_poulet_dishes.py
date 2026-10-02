import os
import sys
import shutil
import django

sys.path.append('c:\\Users\\HP\\Desktop\\Ayyou-backend')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from apps.catalog.models import Categorie, Etablissement, Produit, VarianteProduit, OptionProduit

print("==================================================")
print("  POPULATION DES PLATS DIBI POULET (DIBITERIE & GRILLADES)")
print("==================================================")

# Source images
SOURCE_DIR = r"C:\Users\HP\.gemini\antigravity\brain\1f2cd0a4-e39b-4ef8-b924-e7e0bc2d34a3\.user_uploaded"
DEST_DIR = r"C:\Users\HP\Desktop\Ayyou-backend\media\dishes"

os.makedirs(DEST_DIR, exist_ok=True)

IMAGE_MAPPINGS = {
    "dibi_poulet_kraft_frites.jpg": "media_1790475990529.jpg",
    "dibi_poulet_oignons_rouges.png": "media_1790476011161.png",
    "dibi_poulet_moutarde_grosplan.png": "media_1790476020100.png",
    "dibi_poulet_barbecue_braises.jpg": "media_1790476041483.jpg"
}

for dest_name, src_name in IMAGE_MAPPINGS.items():
    src_path = os.path.join(SOURCE_DIR, src_name)
    dest_path = os.path.join(DEST_DIR, dest_name)
    if os.path.exists(src_path):
        shutil.copy(src_path, dest_path)
        print(f"Copied {src_name} -> {dest_name}")
    else:
        print(f"WARNING: {src_path} not found!")

cat_official = Categorie.objects.get(id=9)
print(f"Categorie officielle: {cat_official.nom} (ID {cat_official.id})")

DIBI_POULET_DISHES = [
    {
        "etablissement_nom": "Dibi Dakar",
        "nom": "Dibi Poulet Braisé sur Kraft & Barquette de Frites",
        "description": "Poulet fermier mariné à la moutarde de Dijon, poivre noir et ail, braisé à l'étouffée sur papier kraft. Servi avec sauce oignon onctueuse, rondelles d'oignons blancs et grande barquette de frites croustillantes.",
        "prix_base": 4800.00,
        "image_url": "http://127.0.0.1:8000/media/dishes/dibi_poulet_kraft_frites.jpg",
        "temps_preparation": "15-20 min",
        "tags": ["Dibi Poulet", "Kraft", "Frites", "Moutarde", "Oignons"],
        "variantes": [
            {"titre": "Demie Portion Dibi Poulet", "sous_titre": "Demis-poulet braisé avec frites & oignons", "surcout_prix": 0.00, "est_requis": True, "ordre": 1},
            {"titre": "Poulet Entier Dibi Kraft", "sous_titre": "Poulet entier pour 2-3 personnes + XXL frites", "surcout_prix": 4500.00, "est_requis": False, "ordre": 2},
        ],
        "options": [
            {"type_option": OptionProduit.TYPE_SAUCE, "titre": "Sauce Moutarde Maison", "sous_titre": "Sauce crémeuse poivrée", "surcout_prix": 200.00, "est_inclus": True, "ordre": 1},
            {"type_option": OptionProduit.TYPE_SUPPLEMENT, "titre": "Supplément Frites Maison", "sous_titre": "Barquette supplémentaire de frites", "surcout_prix": 1000.00, "est_inclus": False, "ordre": 2},
        ]
    },
    {
        "etablissement_nom": "Dibi Chez Samba",
        "nom": "Dibi Poulet Mariné aux Oignons Rouges & Sauce Moutarde",
        "description": "Morceaux choisis de poulet marinés longuement dans une épice secrète Samba, cuits doucement au charbon de bois et recouverts d'oignons rouges sautés croquants et sauce moutarde intense.",
        "prix_base": 4500.00,
        "image_url": "http://127.0.0.1:8000/media/dishes/dibi_poulet_oignons_rouges.png",
        "temps_preparation": "15-20 min",
        "tags": ["Dibi Poulet", "Oignons Rouges", "Moutarde", "Charbon"],
        "variantes": [
            {"titre": "Assiette Dibi Poulet Samba", "sous_titre": "Garni d'oignons rouges & sauce", "surcout_prix": 0.00, "est_requis": True, "ordre": 1},
            {"titre": "Plat XXL Poulet Entier", "sous_titre": "Poulet entier mariné aux oignons rouges", "surcout_prix": 4000.00, "est_requis": False, "ordre": 2},
        ],
        "options": [
            {"type_option": OptionProduit.TYPE_SAUCE, "titre": "Piment Rouge Pilé", "sous_titre": "Relevé et parfumé", "surcout_prix": 200.00, "est_inclus": True, "ordre": 1},
            {"type_option": OptionProduit.TYPE_SUPPLEMENT, "titre": "Extra Oignons Rouges", "sous_titre": "Portion d'oignons caramélisés", "surcout_prix": 500.00, "est_inclus": False, "ordre": 2},
        ]
    },
    {
        "etablissement_nom": "Le Grill du Sahel",
        "nom": "Dibi Poulet Gourmet au Feu de Bois & Sauce Crème Moutarde",
        "description": "Morceaux de cuisses et pilons de poulet tendres et juteux, braisés au feu de bois avec croûte croustillante, accompagnés de sauce moutarde gourmet en ramequin et oignons grillés.",
        "prix_base": 5000.00,
        "image_url": "http://127.0.0.1:8000/media/dishes/dibi_poulet_moutarde_grosplan.png",
        "temps_preparation": "15-20 min",
        "tags": ["Grill du Sahel", "Poulet Gourmet", "Moutarde", "Braisé"],
        "variantes": [
            {"titre": "Portion Gourmet 1 Personne", "sous_titre": "Cuisses & pilons braisés avec sauce", "surcout_prix": 0.00, "est_requis": True, "ordre": 1},
            {"titre": "Plateau Familial Poulet", "sous_titre": "Portion 3-4 personnes", "surcout_prix": 5000.00, "est_requis": False, "ordre": 2},
        ],
        "options": [
            {"type_option": OptionProduit.TYPE_SAUCE, "titre": "Sauce Verte Persillade", "sous_titre": "Ail, persil & citron", "surcout_prix": 300.00, "est_inclus": False, "ordre": 1},
            {"type_option": OptionProduit.TYPE_SUPPLEMENT, "titre": "Suppléments Pilons (x2)", "sous_titre": "Deux pilons de poulet braisés", "surcout_prix": 1200.00, "est_inclus": False, "ordre": 2},
        ]
    },
    {
        "etablissement_nom": "Chez Penda",
        "nom": "Poulet Grillé au Barbecue & Épices Barbecue Sénégalaises",
        "description": "Poulet découpé grillé directement sur la grille métallique au barbecue braise fumante, saupoudré d'herbes aromatiques fraîches, persil haché et marinades maison Penda.",
        "prix_base": 4200.00,
        "image_url": "http://127.0.0.1:8000/media/dishes/dibi_poulet_barbecue_braises.jpg",
        "temps_preparation": "20-25 min",
        "tags": ["Chez Penda", "Poulet Grillé", "Barbecue", "Persil", "Braises"],
        "variantes": [
            {"titre": "Demi-Poulet Barbecue", "sous_titre": "Demi poulet grillé au charbon", "surcout_prix": 0.00, "est_requis": True, "ordre": 1},
            {"titre": "Poulet Barbecue Entier", "sous_titre": "Poulet entier garni d'herbes", "surcout_prix": 3800.00, "est_requis": False, "ordre": 2},
        ],
        "options": [
            {"type_option": OptionProduit.TYPE_SAUCE, "titre": "Sauce Piment Maison Penda", "sous_titre": "Recette secrète piquante", "surcout_prix": 200.00, "est_inclus": True, "ordre": 1},
            {"type_option": OptionProduit.TYPE_SUPPLEMENT, "titre": "Portion Alloco ou Frites", "sous_titre": "Bananes frites ou frites au choix", "surcout_prix": 1000.00, "est_inclus": False, "ordre": 2},
        ]
    }
]

created_count = 0
for d in DIBI_POULET_DISHES:
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
    print(f"OK: Plat Dibi Poulet [{produit.id}] '{produit.nom[:30]}...' cree pour {etab.nom}")

print(f"\nTOTAL PLATS DIBI POULET CREES: {created_count}")
