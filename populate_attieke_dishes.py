import os
import sys
import shutil
import django

sys.path.append('c:\\Users\\HP\\Desktop\\Ayyou-backend')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from apps.catalog.models import Categorie, Etablissement, Produit, VarianteProduit, OptionProduit

print("==================================================")
print("  POPULATION DES ATTIEKES POISSON GRILLE (CATEGORIE 13)")
print("==================================================")

# Source images
SOURCE_DIR = r"C:\Users\HP\.gemini\antigravity\brain\1f2cd0a4-e39b-4ef8-b924-e7e0bc2d34a3\.user_uploaded"
DEST_DIR = r"C:\Users\HP\Desktop\Ayyou-backend\media\dishes"

os.makedirs(DEST_DIR, exist_ok=True)

IMAGE_MAPPINGS = {
    "attieke_poisson_legumes_couleurs.png": "media_1790504792453.png",
    "attieke_poisson_planche_aloco.jpg": "media_1790504803946.jpg",
    "attieke_poisson_assiette_noire.jpg": "media_1790504831249.jpg",
    "attieke_poisson_ovale_aloco.jpg": "media_1790504848484.jpg"
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

ATTIEKE_DISHES = [
    {
        "etablissement_nom": "Maquis Abidjan Dakar",
        "nom": "Attiéké Poisson Carpe Braisé aux Légumes Multicolores",
        "description": "Véritable Attiéké frais de Dabou cuit à la vapeur, surmonté d'une carpe entière braisée aux épices ivoiriennes et généreusement garnie de dés de poivrons rouges/jaunes/verts, oignons crus et tomates.",
        "prix_base": 5500.00,
        "image_url": "http://127.0.0.1:8000/media/dishes/attieke_poisson_legumes_couleurs.png",
        "temps_preparation": "20-25 min",
        "tags": ["Attiéké", "Maquis Abidjan", "Poisson Braisé", "Carpe", "Piment Ivoirien"],
        "variantes": [
            {"titre": "Assiette Maquis Abidjan 1 Personne", "sous_titre": "Attiéké vapeur, poisson braisé & légumes", "surcout_prix": 0.00, "est_requis": True, "ordre": 1},
            {"titre": "Plat Géant Maquis 2-3 Personnes", "sous_titre": "Format XXL avec poisson géant & extra attiéké", "surcout_prix": 4000.00, "est_requis": False, "ordre": 2},
        ],
        "options": [
            {"type_option": OptionProduit.TYPE_SAUCE, "titre": "Sauce Piment Frais Pilé", "sous_titre": "Piment vert et rouge ivoirien", "surcout_prix": 200.00, "est_inclus": True, "ordre": 1},
            {"type_option": OptionProduit.TYPE_SUPPLEMENT, "titre": "Supplément Bananes Alloco", "sous_titre": "Portion bananes frites", "surcout_prix": 1000.00, "est_inclus": False, "ordre": 2},
        ]
    },
    {
        "etablissement_nom": "Saveurs de Côte d'Ivoire",
        "nom": "Attiéké Poisson Grillé sur Planche, Aloco & Piment Rouge",
        "description": "Poisson entier braisé au charbon de bois servi sur planche en bois rustique avec dôme d'attiéké jaune au beurre, dés de bananes Alloco frites et ramequin de purée de piment rouge.",
        "prix_base": 6000.00,
        "image_url": "http://127.0.0.1:8000/media/dishes/attieke_poisson_planche_aloco.jpg",
        "temps_preparation": "20-25 min",
        "tags": ["Saveurs CI", "Poisson Grillé", "Attiéké Beurre", "Aloco", "Planche"],
        "variantes": [
            {"titre": "Planche Attiéké & Aloco", "sous_titre": "Poisson grillé, attiéké & bananes aloco", "surcout_prix": 0.00, "est_requis": True, "ordre": 1},
            {"titre": "Planche Royale Duo", "sous_titre": "2 poissons grillés & double aloco", "surcout_prix": 5000.00, "est_requis": False, "ordre": 2},
        ],
        "options": [
            {"type_option": OptionProduit.TYPE_SAUCE, "titre": "Jus de Poisson Vinaigré", "sous_titre": "Jus de cuisson assaisonné", "surcout_prix": 200.00, "est_inclus": True, "ordre": 1},
            {"type_option": OptionProduit.TYPE_SUPPLEMENT, "titre": "Extra Dôme d'Attiéké", "sous_titre": "Portion attiéké vapeur", "surcout_prix": 800.00, "est_inclus": False, "ordre": 2},
        ]
    },
    {
        "etablissement_nom": "Chez Aya Ivoire",
        "nom": "Attiéké Poisson Capitaine Grillé, Aloco & Salade Composée",
        "description": "Grand poisson Capitaine braisé aux épices d'Abidjan, servi sur grande assiette noire avec attiéké moucheté aux légumes, dés d'Aloco dorés et salade composée concombre-tomate.",
        "prix_base": 6500.00,
        "image_url": "http://127.0.0.1:8000/media/dishes/attieke_poisson_assiette_noire.jpg",
        "temps_preparation": "20-25 min",
        "tags": ["Chez Aya Ivoire", "Capitaine", "Attiéké", "Aloco", "Salade"],
        "variantes": [
            {"titre": "Assiette Noire Prestige Aya", "sous_titre": "Capitaine braisé, attiéké & aloco", "surcout_prix": 0.00, "est_requis": True, "ordre": 1},
            {"titre": "Formule XL Capitaine Entier", "sous_titre": "Grand poisson capitaine pour 2-3 personnes", "surcout_prix": 4500.00, "est_requis": False, "ordre": 2},
        ],
        "options": [
            {"type_option": OptionProduit.TYPE_SAUCE, "titre": "Sauce Piment Noir Maison", "sous_titre": "Piment fumé ivoirien", "surcout_prix": 300.00, "est_inclus": False, "ordre": 1},
            {"type_option": OptionProduit.TYPE_SUPPLEMENT, "titre": "Extra Portion Aloco", "sous_titre": "Bananes frites croustillantes", "surcout_prix": 1000.00, "est_inclus": False, "ordre": 2},
        ]
    },
    {
        "etablissement_nom": "Ivoire Saveurs",
        "nom": "Attiéké Poisson Tilapia Braisé au Piment & Bananes Aloco",
        "description": "Recette classique d'Ivoire Saveurs : poisson Tilapia croustillant braisé au charbon, dôme d'attiéké fin, dés de bananes plantain frites et condiment tomate-concombre à l'huile aromatisée.",
        "prix_base": 5000.00,
        "image_url": "http://127.0.0.1:8000/media/dishes/attieke_poisson_ovale_aloco.jpg",
        "temps_preparation": "15-20 min",
        "tags": ["Ivoire Saveurs", "Tilapia", "Attiéké", "Bananes Aloco", "Piment"],
        "variantes": [
            {"titre": "Plat Ovale Ivoire Saveurs", "sous_titre": "Tilapia braisé, dôme attiéké & aloco", "surcout_prix": 0.00, "est_requis": True, "ordre": 1},
            {"titre": "Plat Familial 2 Personnes", "sous_titre": "Double portion tilapia & attiéké", "surcout_prix": 3800.00, "est_requis": False, "ordre": 2},
        ],
        "options": [
            {"type_option": OptionProduit.TYPE_SAUCE, "titre": "Condiment Oignon-Tomate", "sous_titre": "Légumes crus vinaigrés", "surcout_prix": 200.00, "est_inclus": True, "ordre": 1},
            {"type_option": OptionProduit.TYPE_SUPPLEMENT, "titre": "Extra Piment Frais Haché", "sous_titre": "Piment vert fort", "surcout_prix": 150.00, "est_inclus": False, "ordre": 2},
        ]
    }
]

created_count = 0
for d in ATTIEKE_DISHES:
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
    print(f"OK: Plat Attiéké Poisson [{produit.id}] '{produit.nom[:30]}...' cree pour {etab.nom}")

print(f"\nTOTAL PLATS ATTIEKE POISSON CREES: {created_count}")
