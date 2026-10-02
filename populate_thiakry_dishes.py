import os
import sys
import shutil
import django

sys.path.append('c:\\Users\\HP\\Desktop\\Ayyou-backend')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from apps.catalog.models import Categorie, Etablissement, Produit, VarianteProduit, OptionProduit

print("==================================================")
print("  POPULATION DU THIAKRY / DEGUE (CATEGORIE 17)")
print("==================================================")

# Source images
SOURCE_DIR = r"C:\Users\HP\.gemini\antigravity\brain\1f2cd0a4-e39b-4ef8-b924-e7e0bc2d34a3\.user_uploaded"
DEST_DIR = r"C:\Users\HP\Desktop\Ayyou-backend\media\dishes"

os.makedirs(DEST_DIR, exist_ok=True)

IMAGE_MAPPINGS = {
    "thiakry_bol_verre_menthe.png": "media_1790507757043.png",
    "thiakry_louche_bois_saladier.png": "media_1790507775977.png",
    "thiakry_bol_coco_fruits.png": "media_1790507786571.png",
    "thiakry_verre_etages_raisins.png": "media_1790507798826.png"
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

THIAKRY_DISHES = [
    {
        "etablissement_nom": "Douceurs de Dakar",
        "nom": "Thiakry Traditionnel au Yaourt Crémeux & Menthe Fraîche",
        "description": "Granulés de mil biologique roulés à la main et cuits à la vapeur, immergés dans un yaourt fermier crémeux assaisonné de muscade, vanille et sucre de canne, décoré de feuilles de menthe.",
        "prix_base": 1800.00,
        "image_url": "http://127.0.0.1:8000/media/dishes/thiakry_bol_verre_menthe.png",
        "temps_preparation": "05 min",
        "tags": ["Thiakry", "Dégué", "Mil Bio", "Douceurs de Dakar", "Menthe"],
        "variantes": [
            {"titre": "Bol Individuel 250g", "sous_titre": "Thiakry traditionnel au yaourt vanillé", "surcout_prix": 0.00, "est_requis": True, "ordre": 1},
            {"titre": "Grand Bol Gourmand 500g", "sous_titre": "Portion généreuse 500g", "surcout_prix": 1200.00, "est_requis": False, "ordre": 2},
        ],
        "options": [
            {"type_option": OptionProduit.TYPE_SUPPLEMENT, "titre": "Supplément Lait Concentré Sucré", "sous_titre": "Nappage lait concentré", "surcout_prix": 200.00, "est_inclus": True, "ordre": 1},
            {"type_option": OptionProduit.TYPE_SUPPLEMENT, "titre": "Raisins Secs Dorés Extra", "sous_titre": "Raisins secs moelleux", "surcout_prix": 150.00, "est_inclus": False, "ordre": 2},
        ]
    },
    {
        "etablissement_nom": "Teranga Saveurs",
        "nom": "Thiakry Fait Maison servi à la Louche en Saladier Bois",
        "description": "Spécialité du terroir : dôme de couscous de mil aromatisé à la fleur d'oranger et vanille Bourbon, mélangé à louche ouverte avec un lait caillé onctueux et riche.",
        "prix_base": 2000.00,
        "image_url": "http://127.0.0.1:8000/media/dishes/thiakry_louche_bois_saladier.png",
        "temps_preparation": "05 min",
        "tags": ["Thiakry Teranga", "Fleur d'Oranger", "Lait Caillé", "Fait Maison"],
        "variantes": [
            {"titre": "Saladier Teranga 350g", "sous_titre": "Servi bien frais à la cuillère", "surcout_prix": 0.00, "est_requis": True, "ordre": 1},
            {"titre": "Grand Saladier Familial 1kg", "sous_titre": "Pour partager à la fin du repas", "surcout_prix": 3000.00, "est_requis": False, "ordre": 2},
        ],
        "options": [
            {"type_option": OptionProduit.TYPE_SUPPLEMENT, "titre": "Pincée de Cannelle Moulue", "sous_titre": "Épice cannelle", "surcout_prix": 100.00, "est_inclus": True, "ordre": 1},
        ]
    },
    {
        "etablissement_nom": "Glaces Dakar",
        "nom": "Thiakry Bowl en Noix de Coco, Bananes & Framboises",
        "description": "Création moderne rafraîchissante : Thiakry servi dans une véritable coque de noix de coco naturelle, surmonté de couscous de mil, raisins secs dorés, rondelles de banane et framboises.",
        "prix_base": 2500.00,
        "image_url": "http://127.0.0.1:8000/media/dishes/thiakry_bol_coco_fruits.png",
        "temps_preparation": "05 min",
        "tags": ["Thiakry Bowl", "Glaces Dakar", "Noix de Coco", "Fruits Frais", "Gourmet"],
        "variantes": [
            {"titre": "Coco Bowl Thiakry Gourmet", "sous_titre": "Servi en coque de noix de coco avec fruits", "surcout_prix": 0.00, "est_requis": True, "ordre": 1},
            {"titre": "Coco Bowl XL + Boule de Glace", "sous_titre": "Avec une boule de glace vanille ou bouye", "surcout_prix": 1000.00, "est_requis": False, "ordre": 2},
        ],
        "options": [
            {"type_option": OptionProduit.TYPE_SUPPLEMENT, "titre": "Boule de Glace Bouye", "sous_titre": "Glace artisanale au fruit du baobab", "surcout_prix": 500.00, "est_inclus": False, "ordre": 1},
            {"type_option": OptionProduit.TYPE_SUPPLEMENT, "titre": "Nappage Sirop d'Érable", "sous_titre": "Touche sucrée érable", "surcout_prix": 200.00, "est_inclus": False, "ordre": 2},
        ]
    },
    {
        "etablissement_nom": "Chez Penda",
        "nom": "Verrine de Dégué Sénégalais à Deux Étages & Raisins",
        "description": "Présentation raffinée en verre à double couche : lit de granulés de mil dorés parfumés à la muscade au fond, surmonté d'un yaourt vanillé onctueux et parsemé de raisins secs.",
        "prix_base": 2200.00,
        "image_url": "http://127.0.0.1:8000/media/dishes/thiakry_verre_etages_raisins.png",
        "temps_preparation": "05 min",
        "tags": ["Verrine Dégué", "Chez Penda", "Deux Étages", "Yaourt Vanille", "Raisins Secs"],
        "variantes": [
            {"titre": "Verrine Dégué 300g", "sous_titre": "Verrine raffinée à deux étages", "surcout_prix": 0.00, "est_requis": True, "ordre": 1},
            {"titre": "Duo de Verrines Dégué", "sous_titre": "Deux verrines fraîcheur", "surcout_prix": 1800.00, "est_requis": False, "ordre": 2},
        ],
        "options": [
            {"type_option": OptionProduit.TYPE_SUPPLEMENT, "titre": "Lait Concentré Non Sucré Extra", "sous_titre": "Onctuosité supplémentaire", "surcout_prix": 150.00, "est_inclus": True, "ordre": 1},
        ]
    }
]

created_count = 0
for d in THIAKRY_DISHES:
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
    print(f"OK: Plat Thiakry / Dégué [{produit.id}] '{produit.nom[:30]}...' cree pour {etab.nom}")

print(f"\nTOTAL PLATS THIAKRY / DEGUE CREES: {created_count}")
