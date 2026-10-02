import os
import sys
import django

sys.path.append('c:\\Users\\HP\\Desktop\\Ayyou-backend')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from apps.catalog.models import Categorie, Etablissement, Produit, VarianteProduit, OptionProduit

print("==================================================")
print("  POPULATION DES PLATS YASSA POULET")
print("==================================================")

cat_official = Categorie.objects.get(id=8)
print(f"Categorie officielle: {cat_official.nom} (ID {cat_official.id})")

YASSA_DISHES = [
    {
        "etablissement_nom": "Teranga Saveurs",
        "nom": "Yassa Poulet Braisé Gourmand aux Poivrons & Œufs Durs",
        "description": "Poulet fermier mariné au jus de citron vert et moutarde de Dijon, braisé au charbon puis nappé d'une compotée d'oignons caramélisés, rondelles de poivrons tricolores, dés de concombre et œufs durs.",
        "prix_base": 3500.00,
        "image_url": "http://127.0.0.1:8000/media/dishes/yassa_poulet_teranga.jpg",
        "temps_preparation": "20-25 min",
        "tags": ["Yassa Poulet", "Poulet Braisé", "Cuisine sénégalaise", "Oignons Citron"],
        "variantes": [
            {"titre": "Portion 1/4 Poulet", "sous_titre": "Cuisse ou blanc braisé + Riz blanc", "surcout_prix": 0.00, "est_requis": True, "ordre": 1},
            {"titre": "Portion 1/2 Poulet Gourmand", "sous_titre": "Demi poulet entier + légumes extra", "surcout_prix": 2000.00, "est_requis": False, "ordre": 2},
        ],
        "options": [
            {"type_option": OptionProduit.TYPE_SAUCE, "titre": "Extra Sauce Oignon Yassa", "sous_titre": "Sauce oignon citronnée supplémentaire", "surcout_prix": 500.00, "est_inclus": True, "ordre": 1},
            {"type_option": OptionProduit.TYPE_SUPPLEMENT, "titre": "Œuf dur supplémentaire", "sous_titre": "Œuf dur bio", "surcout_prix": 300.00, "est_inclus": False, "ordre": 2},
            {"type_option": OptionProduit.TYPE_SUPPLEMENT, "titre": "Piment antillais frais", "sous_titre": "Pour les amateurs de piquant", "surcout_prix": 0.00, "est_inclus": True, "ordre": 3},
        ]
    },
    {
        "etablissement_nom": "Chez Penda",
        "nom": "Yassa Poulet Traditionnel au Citron & Oignons Caramélisés",
        "description": "Le véritable Yassa de la maman sénégalaise : cuisses de poulet mijotées dans une marmelade d'oignons fondants relevée au piment doux, ail, laurier et jus de citron bio pressé, servi sur riz blanc fumant.",
        "prix_base": 3000.00,
        "image_url": "http://127.0.0.1:8000/media/dishes/yassa_poulet_chez_penda.jpg",
        "temps_preparation": "15-20 min",
        "tags": ["Yassa Poulet", "Fait Maison", "Cuisine sénégalaise", "Tradition"],
        "variantes": [
            {"titre": "Assiette Individuelle", "sous_titre": "Riz blanc parfumé & Cuisse de poulet", "surcout_prix": 0.00, "est_requis": True, "ordre": 1},
            {"titre": "Assiette Duo", "sous_titre": "2 cuisses de poulet + double sauce", "surcout_prix": 2500.00, "est_requis": False, "ordre": 2},
        ],
        "options": [
            {"type_option": OptionProduit.TYPE_SAUCE, "titre": "Sauce Piment Maison", "sous_titre": "Sauce piment rouge mijotée", "surcout_prix": 300.00, "est_inclus": False, "ordre": 1},
            {"type_option": OptionProduit.TYPE_SUPPLEMENT, "titre": "Riz blanc extra", "sous_titre": "Portion supplémentaire de riz", "surcout_prix": 500.00, "est_inclus": False, "ordre": 2},
        ]
    },
    {
        "etablissement_nom": "Le Baobab Gourmand",
        "nom": "Yassa Poulet Plateau Royal aux Cornichons & Oignons Vinaigrés",
        "description": "Présentation prestige sur plateau inox : poulet fermier grillé au feu de bois, oignons caramélisés aux cornichons croquants, câpres, demi-lunes de citron, poivrons verts/rouges et œufs mollets.",
        "prix_base": 4500.00,
        "image_url": "http://127.0.0.1:8000/media/dishes/yassa_poulet_royal_baobab.jpg",
        "temps_preparation": "25-30 min",
        "tags": ["Yassa Royal", "Poulet Grillé", "Feu de Bois", "Plateau Inox"],
        "variantes": [
            {"titre": "Plateau Royal Individuel", "sous_titre": "Servi chaud avec garniture prestige", "surcout_prix": 0.00, "est_requis": True, "ordre": 1},
            {"titre": "Plateau Royal Familial 3-4 pers", "sous_titre": "Poulet entier braisé + garnitures XXL", "surcout_prix": 7500.00, "est_requis": False, "ordre": 2},
        ],
        "options": [
            {"type_option": OptionProduit.TYPE_SUPPLEMENT, "titre": "Cornichons & Câpres extra", "sous_titre": "Accompagnement croquant", "surcout_prix": 400.00, "est_inclus": True, "ordre": 1},
            {"type_option": OptionProduit.TYPE_SAUCE, "titre": "Sauce Moutarde & Citron Vert", "sous_titre": "Moutarde à l'ancienne", "surcout_prix": 300.00, "est_inclus": True, "ordre": 2},
        ]
    },
    {
        "etablissement_nom": "Saveurs de Ndar",
        "nom": "Yassa Poulet Rôti Artisan à la Moutarde & Riz Légumes",
        "description": "Délicieuses pilons et cuisses de poulet rôties au four avec leur jus de rôti acidulé, sauce oignons caramélisés et son dôme de riz blanc aromatisé aux petits légumes (carottes, petits pois, poivrons).",
        "prix_base": 4000.00,
        "image_url": "http://127.0.0.1:8000/media/dishes/yassa_poulet_ndar.jpg",
        "temps_preparation": "20-25 min",
        "tags": ["Yassa Rôti", "Artisan", "Saint-Louis", "Poulet au Four"],
        "variantes": [
            {"titre": "Portion Gourmet Ndar", "sous_titre": "Riz aux légumes & Poulet rôti", "surcout_prix": 0.00, "est_requis": True, "ordre": 1},
            {"titre": "Barquette XL 2 personnes", "sous_titre": "Double portion de poulet rôti", "surcout_prix": 3000.00, "est_requis": False, "ordre": 2},
        ],
        "options": [
            {"type_option": OptionProduit.TYPE_SAUCE, "titre": "Jus de Rôti Acidulé Extra", "sous_titre": "Sauce parfumée au piment doux", "surcout_prix": 400.00, "est_inclus": True, "ordre": 1},
            {"type_option": OptionProduit.TYPE_SUPPLEMENT, "titre": "Tranches de Tomates & Oignons frais", "sous_titre": "Salade de garniture", "surcout_prix": 300.00, "est_inclus": False, "ordre": 2},
        ]
    }
]

created_count = 0
for d in YASSA_DISHES:
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
    print(f"OK: Plat Yassa [{produit.id}] '{produit.nom[:30]}...' cree pour {etab.nom}")

print(f"\nTOTAL PLATS YASSA CREES: {created_count}")
