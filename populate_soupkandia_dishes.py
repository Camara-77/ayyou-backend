import os
import sys
import django

sys.path.append('c:\\Users\\HP\\Desktop\\Ayyou-backend')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from apps.catalog.models import Categorie, Etablissement, Produit, VarianteProduit, OptionProduit

print("==================================================")
print("  POPULATION DES PLATS SOUPOU KANDIA (SAUCE GOMBO)")
print("==================================================")

cat_official = Categorie.objects.get(id=8)
print(f"Categorie officielle: {cat_official.nom} (ID {cat_official.id})")

SOUPKANDIA_DISHES = [
    {
        "etablissement_nom": "Teranga Saveurs",
        "nom": "Soupou Kandia aux Crevettes & Thiof à l'Huile de Palme",
        "description": "L'authentique sauce gombo sénégalaise préparée à l'huile de palme rouge naturelle, garnie de morceaux de mérou (Thiof), crevettes entières, Yet (mollusque séché), Kétiakh et piment rouge, servie avec riz blanc parfumé.",
        "prix_base": 4000.00,
        "image_url": "http://127.0.0.1:8000/media/dishes/soupkandia_teranga.jpg",
        "temps_preparation": "20-25 min",
        "tags": ["Soupou Kandia", "Sauce Gombo", "Huile de Palme", "Thiof", "Crevettes"],
        "variantes": [
            {"titre": "Assiette Individuelle Gombo", "sous_titre": "Riz blanc & Sauce Kandia crevettes/poisson", "surcout_prix": 0.00, "est_requis": True, "ordre": 1},
            {"titre": "Assiette Royale Gourmande", "sous_titre": "Portion extra Thiof & crevettes géantes", "surcout_prix": 2000.00, "est_requis": False, "ordre": 2},
        ],
        "options": [
            {"type_option": OptionProduit.TYPE_SAUCE, "titre": "Extra Huile de Palme Parfumée", "sous_titre": "Pour amateurs de sauce riche", "surcout_prix": 300.00, "est_inclus": True, "ordre": 1},
            {"type_option": OptionProduit.TYPE_SUPPLEMENT, "titre": "Portion de Crevettes entières (x3)", "sous_titre": "Crevettes sautées", "surcout_prix": 1000.00, "est_inclus": False, "ordre": 2},
            {"type_option": OptionProduit.TYPE_SUPPLEMENT, "titre": "Piment antillais frais", "sous_titre": "Piquant à volonté", "surcout_prix": 0.00, "est_inclus": True, "ordre": 3},
        ]
    },
    {
        "etablissement_nom": "Chez Penda",
        "nom": "Soupou Kandia Traditionnel au Faitout Inox & Poisson Séché",
        "description": "Recette ancestrale mijotée à feu doux dans son faitout inox : gombos hachés extra fins, poisson séché Kétiakh, Touffa, morceaux de poisson frais et piment jaune, servie avec grand plat de riz blanc cuit à la vapeur.",
        "prix_base": 3500.00,
        "image_url": "http://127.0.0.1:8000/media/dishes/soupkandia_chez_penda.jpg",
        "temps_preparation": "15-20 min",
        "tags": ["Soupou Kandia", "Fait Maison", "Poisson Séché", "Kétiakh", "Tradition"],
        "variantes": [
            {"titre": "Portion Faitout 1 personne", "sous_titre": "Sauce gombo tradition & Riz blanc", "surcout_prix": 0.00, "est_requis": True, "ordre": 1},
            {"titre": "Portion Faitout Duo", "sous_titre": "2 personnes avec supplément Kétiakh", "surcout_prix": 2500.00, "est_requis": False, "ordre": 2},
        ],
        "options": [
            {"type_option": OptionProduit.TYPE_SAUCE, "titre": "Piment jaune pilé", "sous_titre": "Sauce piquante piment jaune", "surcout_prix": 300.00, "est_inclus": False, "ordre": 1},
            {"type_option": OptionProduit.TYPE_SUPPLEMENT, "titre": "Riz blanc supplément", "sous_titre": "Portion de riz vapeur", "surcout_prix": 500.00, "est_inclus": False, "ordre": 2},
        ]
    },
    {
        "etablissement_nom": "Le Baobab Gourmand",
        "nom": "Soupou Kandia Prestige aux Fruits de Mer (Langouste, Crabes & Crevettes)",
        "description": "Le sommet de la gastronomie sénégalaise : une queue de langouste braisée, crabes royaux, crevettes géantes et poisson frais noyés dans une sauce gombo affinée à l'huile de palme pure.",
        "prix_base": 6500.00,
        "image_url": "http://127.0.0.1:8000/media/dishes/soupkandia_royal_baobab.jpg",
        "temps_preparation": "25-30 min",
        "tags": ["Langouste", "Crabes", "Soupou Kandia Prestige", "Fruits de Mer", "Luxe"],
        "variantes": [
            {"titre": "Assiette Prestige Langouste", "sous_titre": "Servie avec langouste entiere & crabes", "surcout_prix": 0.00, "est_requis": True, "ordre": 1},
            {"titre": "Plateau Royal Geant 3 personnes", "sous_titre": "Double langouste & crabes XXL", "surcout_prix": 8500.00, "est_requis": False, "ordre": 2},
        ],
        "options": [
            {"type_option": OptionProduit.TYPE_SUPPLEMENT, "titre": "Supplément Crabe Royal (x1)", "sous_titre": "Crabe frais décortiqué", "surcout_prix": 1500.00, "est_inclus": False, "ordre": 1},
            {"type_option": OptionProduit.TYPE_SAUCE, "titre": "Sauce Piment Vert & Citron", "sous_titre": "Accompagnement fraîcheur", "surcout_prix": 300.00, "est_inclus": True, "ordre": 2},
        ]
    },
    {
        "etablissement_nom": "Saveurs de Ndar",
        "nom": "Soupou Kandia Fait Maison Saint-Louis sur Assiette Noire",
        "description": "Présentation moderne de la cuisine de Ndar : dôme de riz blanc nappé d'une généreuse cuillerée de sauce gombo foncée aux crevettes du fleuve, Yet et poisson Capitaine cuit à la perfection.",
        "prix_base": 4500.00,
        "image_url": "http://127.0.0.1:8000/media/dishes/soupkandia_ndar.jpg",
        "temps_preparation": "20-25 min",
        "tags": ["Soupou Kandia Ndar", "Capitaine", "Crevettes Fleuve", "Saint-Louis"],
        "variantes": [
            {"titre": "Barquette Gourmet Ndar", "sous_titre": "Sauce gombo & Riz blanc", "surcout_prix": 0.00, "est_requis": True, "ordre": 1},
            {"titre": "Barquette XL Familiale", "sous_titre": "Portion 2-3 personnes", "surcout_prix": 3500.00, "est_requis": False, "ordre": 2},
        ],
        "options": [
            {"type_option": OptionProduit.TYPE_SAUCE, "titre": "Extra Sauce Gombo Ndar", "sous_titre": "Onctueuse & piquante", "surcout_prix": 400.00, "est_inclus": True, "ordre": 1},
            {"type_option": OptionProduit.TYPE_SUPPLEMENT, "titre": "Piment Rouge Habanero", "sous_titre": "Entier sur plat", "surcout_prix": 200.00, "est_inclus": False, "ordre": 2},
        ]
    }
]

created_count = 0
for d in SOUPKANDIA_DISHES:
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
    print(f"OK: Plat SoupKandia [{produit.id}] '{produit.nom[:30]}...' cree pour {etab.nom}")

print(f"\nTOTAL PLATS SOUPKANDIA CREES: {created_count}")
