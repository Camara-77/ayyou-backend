import os
import sys
import shutil
import django

sys.path.append('c:\\Users\\HP\\Desktop\\Ayyou-backend')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from apps.catalog.models import Categorie, Etablissement, Produit, VarianteProduit, OptionProduit

print("==================================================")
print("  POPULATION DES SALADES & HEALTHY (CATEGORIE 20)")
print("==================================================")

# Source images
SOURCE_DIR = r"C:\Users\HP\.gemini\antigravity\brain\1f2cd0a4-e39b-4ef8-b924-e7e0bc2d34a3\.user_uploaded"
DEST_DIR = r"C:\Users\HP\Desktop\Ayyou-backend\media\dishes"

os.makedirs(DEST_DIR, exist_ok=True)

IMAGE_MAPPINGS = {
    "salade_fraicheur_concombre_carottes.jpg": "media_1790511427593.jpg",
    "salade_cesar_oeufs_bacon.jpg": "media_1790511439820.jpg",
    "salade_composee_avocat_mais.jpg": "media_1790511449510.jpg",
    "plateau_healthy_plantain_oeufs_guacamole.jpg": "media_1790511461383.jpg"
}

for dest_name, src_name in IMAGE_MAPPINGS.items():
    src_path = os.path.join(SOURCE_DIR, src_name)
    dest_path = os.path.join(DEST_DIR, dest_name)
    if os.path.exists(src_path):
        shutil.copy(src_path, dest_path)
        print(f"Copied {src_name} -> {dest_name}")
    else:
        print(f"WARNING: {src_path} not found!")

cat_official = Categorie.objects.get(id=20)
print(f"Categorie officielle: {cat_official.nom} (ID {cat_official.id})")

SALADE_DISHES = [
    {
        "etablissement_nom": "Healthy Dakar",
        "nom": "Salade Fraîcheur Tomates Cerises, Concombres & Carottes Râpées",
        "description": "Composition colorée et vitaminée : jeunes pousses de salade frisée, tomates cerises juteuses coupées en deux, rondelles de concombre croquant & dôme de carottes fraîches râpées à l'huile d'olive extra-vierge.",
        "prix_base": 3200.00,
        "image_url": "http://127.0.0.1:8000/media/dishes/salade_fraicheur_concombre_carottes.jpg",
        "temps_preparation": "10-15 min",
        "tags": ["Salade Fraîcheur", "Healthy Dakar", "Bio", "Végétarien", "Vinaigrette Olive"],
        "variantes": [
            {"titre": "Bol Fraîcheur 1 Personne", "sous_titre": "Salade verte, tomates cerises & carottes râpées", "surcout_prix": 0.00, "est_requis": True, "ordre": 1},
            {"titre": "Grand Bol Healthy XL", "sous_titre": "Portion géante avec supplément graines", "surcout_prix": 1500.00, "est_requis": False, "ordre": 2},
        ],
        "options": [
            {"type_option": OptionProduit.TYPE_SAUCE, "titre": "Vinaigrette Vierge au Citron", "sous_titre": "Sauce allégée au citron vert", "surcout_prix": 0.00, "est_inclus": True, "ordre": 1},
            {"type_option": OptionProduit.TYPE_SUPPLEMENT, "titre": "Dés de Fromage Feta Bio", "sous_titre": "Feta AOP émiettée", "surcout_prix": 500.00, "est_inclus": False, "ordre": 2},
        ]
    },
    {
        "etablissement_nom": "Green Teranga",
        "nom": "Salade César Gourmande aux Œufs Durs & Lardons Grillés",
        "description": "L'incontournable Salade César revisitée par Green Teranga : lits de batavia et roquette, quartiers d'œufs durs biologiques, morceaux de bacon/lardons croustillants dorés & sauce César crémeuse.",
        "prix_base": 4200.00,
        "image_url": "http://127.0.0.1:8000/media/dishes/salade_cesar_oeufs_bacon.jpg",
        "temps_preparation": "10-15 min",
        "tags": ["Salade César", "Green Teranga", "Œufs Durs", "Bacon Grillé", "Sauce César"],
        "variantes": [
            {"titre": "Salade César Standard", "sous_titre": "Œufs durs, bacon croustillant & sauce César", "surcout_prix": 0.00, "est_requis": True, "ordre": 1},
            {"titre": "Salade César Poulet & Bacon XL", "sous_titre": "Avec supplément blanc de poulet grillé", "surcout_prix": 1800.00, "est_requis": False, "ordre": 2},
        ],
        "options": [
            {"type_option": OptionProduit.TYPE_SUPPLEMENT, "titre": "Croûtons à l'Ail Maison", "sous_titre": "Croûtons croustillants à l'ail", "surcout_prix": 200.00, "est_inclus": True, "ordre": 1},
            {"type_option": OptionProduit.TYPE_SUPPLEMENT, "titre": "Copeaux de Parmesan AOP", "sous_titre": "Parmesan frais râpé", "surcout_prix": 400.00, "est_inclus": False, "ordre": 2},
        ]
    },
    {
        "etablissement_nom": "Dakar Fresh Bowl",
        "nom": "Salade Composée Avocat, Maïs Doux, Œufs & Pain Baguette",
        "description": "Assiette fraîcheur gourmande et nourrissante : mélange d'avocats mûrs à point, maïs doux, dés de tomates, quartiers d'œufs durs et thon, servie avec deux tranches de pain baguette artisanal.",
        "prix_base": 3800.00,
        "image_url": "http://127.0.0.1:8000/media/dishes/salade_composee_avocat_mais.jpg",
        "temps_preparation": "10-15 min",
        "tags": ["Fresh Bowl", "Avocat & Maïs", "Dakar Fresh", "Salade Composée", "Pain Baguette"],
        "variantes": [
            {"titre": "Assiette Composée Avocat-Maïs", "sous_titre": "Servie avec 2 tranches de baguette", "surcout_prix": 0.00, "est_requis": True, "ordre": 1},
            {"titre": "Menu Fresh Bowl + Jus Fresh 33cl", "sous_titre": "Salade composée + jus de fruits frais", "surcout_prix": 1500.00, "est_requis": False, "ordre": 2},
        ],
        "options": [
            {"type_option": OptionProduit.TYPE_SAUCE, "titre": "Sauce Honey-Mustard (Miel-Moutarde)", "sous_titre": "Sauce douce sucrée-salée", "surcout_prix": 150.00, "est_inclus": True, "ordre": 1},
            {"type_option": OptionProduit.TYPE_SUPPLEMENT, "titre": "Extra Tranches d'Avocat", "sous_titre": "Demi-avocat frais supplémentaire", "surcout_prix": 600.00, "est_inclus": False, "ordre": 2},
        ]
    },
    {
        "etablissement_nom": "Healthy Chez Fatima",
        "nom": "Plateau Healthy Bananes Plantain, Œufs Durs & Guacamole",
        "description": "Plateau énergie naturelle servi sur planche en bois : dés de bananes plantain frites (aloco au four), œufs durs coupés en deux et ramequin de guacamole fraîchement écrasé aux herbes.",
        "prix_base": 3500.00,
        "image_url": "http://127.0.0.1:8000/media/dishes/plateau_healthy_plantain_oeufs_guacamole.jpg",
        "temps_preparation": "10-15 min",
        "tags": ["Healthy Fatima", "Plantain AirFryer", "Guacamole", "Œufs Durs", "Énergie"],
        "variantes": [
            {"titre": "Plateau Healthy Fatima 1 Personne", "sous_titre": "Bananes plantain, œufs durs & guacamole", "surcout_prix": 0.00, "est_requis": True, "ordre": 1},
            {"titre": "Plateau Duo Fit XL", "sous_titre": "Portion 2 personnes avec extra guacamole", "surcout_prix": 2000.00, "est_requis": False, "ordre": 2},
        ],
        "options": [
            {"type_option": OptionProduit.TYPE_SAUCE, "titre": "Sauce Piment Doux Vert", "sous_titre": "Piment doux aux herbes", "surcout_prix": 150.00, "est_inclus": True, "ordre": 1},
            {"type_option": OptionProduit.TYPE_SUPPLEMENT, "titre": "Extra Raméquin Guacamole", "sous_titre": "Guacamole maison extra", "surcout_prix": 500.00, "est_inclus": False, "ordre": 2},
        ]
    }
]

created_count = 0
for d in SALADE_DISHES:
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
    print(f"OK: Plat Salade & Healthy [{produit.id}] '{produit.nom[:30]}...' cree pour {etab.nom}")

print(f"\nTOTAL PLATS SALADES & HEALTHY CREES: {created_count}")
