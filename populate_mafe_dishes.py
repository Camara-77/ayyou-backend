import os
import sys
import django

sys.path.append('c:\\Users\\HP\\Desktop\\Ayyou-backend')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from apps.catalog.models import Categorie, Etablissement, Produit, VarianteProduit, OptionProduit

print("==================================================")
print("  POPULATION DES PLATS MAFÉ (SAUCE ARACHIDE)")
print("==================================================")

cat_official = Categorie.objects.get(id=8)
print(f"Categorie officielle: {cat_official.nom} (ID {cat_official.id})")

MAFE_DISHES = [
    {
        "etablissement_nom": "Teranga Saveurs",
        "nom": "Mafé Bœuf Raffiné au Riz Parfumé & Carottes",
        "description": "Morceaux choisis de viande de bœuf tendres mijotés dans une sauce onctueuse à la pâte d'arachide grillée, carottes croquantes et patates douces, servis avec un dôme de riz blanc parfumé.",
        "prix_base": 3500.00,
        "image_url": "http://127.0.0.1:8000/media/dishes/mafe_boeuf_teranga.jpg",
        "temps_preparation": "20-25 min",
        "tags": ["Mafé", "Mafé Bœuf", "Sauce Arachide", "Cuisine sénégalaise"],
        "variantes": [
            {"titre": "Assiette Individuelle Bœuf", "sous_titre": "Portion classique 1 personne", "surcout_prix": 0.00, "est_requis": True, "ordre": 1},
            {"titre": "Assiette Gourmande Double Viande", "sous_titre": "Portion généreuse de bœuf + légumes extra", "surcout_prix": 1500.00, "est_requis": False, "ordre": 2},
        ],
        "options": [
            {"type_option": OptionProduit.TYPE_SAUCE, "titre": "Extra Sauce Arachide Mafé", "sous_titre": "Sauce arachide supplémentaire", "surcout_prix": 400.00, "est_inclus": True, "ordre": 1},
            {"type_option": OptionProduit.TYPE_SUPPLEMENT, "titre": "Supplément Patate Douce & Carottes", "sous_titre": "Légumes pays", "surcout_prix": 300.00, "est_inclus": False, "ordre": 2},
            {"type_option": OptionProduit.TYPE_SUPPLEMENT, "titre": "Piment frais antillais", "sous_titre": "Pour assaisonner à table", "surcout_prix": 0.00, "est_inclus": True, "ordre": 3},
        ]
    },
    {
        "etablissement_nom": "Chez Penda",
        "nom": "Mafé Poulet Traditionnel à la Pâte d'Arachide Onctueuse",
        "description": "Cuisses de poulet fermier mijotées à feu doux dans une sauce veloutée à la pâte d'arachide artisanale, tomate concentrée et épices du pays, entourant un puits de riz blanc cuit à la vapeur.",
        "prix_base": 3000.00,
        "image_url": "http://127.0.0.1:8000/media/dishes/mafe_poulet_chez_penda.png",
        "temps_preparation": "15-20 min",
        "tags": ["Mafé Poulet", "Sauce Arachide", "Cuisine sénégalaise", "Fait Maison"],
        "variantes": [
            {"titre": "Plat Individuel Poulet", "sous_titre": "1 cuisse de poulet & riz blanc", "surcout_prix": 0.00, "est_requis": True, "ordre": 1},
            {"titre": "Plat Duo Poulet", "sous_titre": "2 cuisses de poulet + extra sauce", "surcout_prix": 2000.00, "est_requis": False, "ordre": 2},
        ],
        "options": [
            {"type_option": OptionProduit.TYPE_SAUCE, "titre": "Piment rouge pilé maison", "sous_titre": "Sauce pimentée à part", "surcout_prix": 300.00, "est_inclus": False, "ordre": 1},
            {"type_option": OptionProduit.TYPE_SUPPLEMENT, "titre": "Rondelle de citron vert", "sous_titre": "Pour relevé le goût acidulé", "surcout_prix": 0.00, "est_inclus": True, "ordre": 2},
        ]
    },
    {
        "etablissement_nom": "Le Baobab Gourmand",
        "nom": "Mafé Bœuf Gourmet au Piment & Feuilles de Laurier",
        "description": "Recette d'exception servie en bol céramique : bœuf mijoté 3 heures dans une réduction d'arachide dorée, piments frais parfumés, manioc et carottes du jardin, servi avec riz de qualité supérieure.",
        "prix_base": 4500.00,
        "image_url": "http://127.0.0.1:8000/media/dishes/mafe_boeuf_royal_baobab.jpg",
        "temps_preparation": "25-30 min",
        "tags": ["Mafé Gourmet", "Bœuf Braisé", "Sauce Arachide", "Bol Céramique"],
        "variantes": [
            {"titre": "Bol Gourmet Individuel", "sous_titre": "Served hot in ceramic bowl", "surcout_prix": 0.00, "est_requis": True, "ordre": 1},
            {"titre": "Bol Prestige Familial", "sous_titre": "Portion 3 personnes avec bœuf fondant XL", "surcout_prix": 5000.00, "est_requis": False, "ordre": 2},
        ],
        "options": [
            {"type_option": OptionProduit.TYPE_SUPPLEMENT, "titre": "Portion de Viande Bœuf extra", "sous_titre": "2 gros morceaux de bœuf", "surcout_prix": 1500.00, "est_inclus": False, "ordre": 1},
            {"type_option": OptionProduit.TYPE_SAUCE, "titre": "Sauce Piment Jaune Piquant", "sous_titre": "Sauce piment parfumée", "surcout_prix": 300.00, "est_inclus": True, "ordre": 2},
        ]
    },
    {
        "etablissement_nom": "Saveurs de Ndar",
        "nom": "Mafé Bœuf Fait Maison Copieux Saint-Louis",
        "description": "Préparation généreuse de la tradition de Ndar : grand plat de riz blanc recouvert d'une sauce Mafé riche au bœuf mijoté, huile d'arachide rouge artisanale et piment habanero entier.",
        "prix_base": 4000.00,
        "image_url": "http://127.0.0.1:8000/media/dishes/mafe_boeuf_ndar.jpg",
        "temps_preparation": "20-25 min",
        "tags": ["Mafé Ndar", "Artisan", "Saint-Louis", "Copieux"],
        "variantes": [
            {"titre": "Barquette Gourmet Ndar", "sous_titre": "Servie chaude en barquette étanche", "surcout_prix": 0.00, "est_requis": True, "ordre": 1},
            {"titre": "Barquette XL Familiale", "sous_titre": "Double portion pour 2-3 personnes", "surcout_prix": 3000.00, "est_requis": False, "ordre": 2},
        ],
        "options": [
            {"type_option": OptionProduit.TYPE_SAUCE, "titre": "Extra Sauce Mafé Ndar", "sous_titre": "Onctueuse & parfumée", "surcout_prix": 400.00, "est_inclus": True, "ordre": 1},
            {"type_option": OptionProduit.TYPE_SUPPLEMENT, "titre": "Piment Jaune Entier", "sous_titre": "Piment piquant", "surcout_prix": 200.00, "est_inclus": False, "ordre": 2},
        ]
    }
]

created_count = 0
for d in MAFE_DISHES:
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
    print(f"OK: Plat Mafe [{produit.id}] '{produit.nom[:30]}...' cree pour {etab.nom}")

print(f"\nTOTAL PLATS MAFE CREES: {created_count}")
