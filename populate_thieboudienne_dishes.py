import os
import sys
import django

sys.path.append('c:\\Users\\HP\\Desktop\\Ayyou-backend')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from apps.catalog.models import Categorie, Etablissement, Produit, VarianteProduit, OptionProduit

print("==================================================")
print("  POPULATION DES PLATS THIEBOUDIENNE (CEEBU JEN)")
print("==================================================")

cat_senegal = Categorie.objects.filter(slug__in=['senegalais', 'cuisine-senegalaise', 'plats-nationaux']).first()
if not cat_senegal:
    cat_senegal = Categorie.objects.first()

print(f"Categorie utilisee: {cat_senegal.nom} (ID {cat_senegal.id})")

DISHES_DATA = [
    {
        "etablissement_nom": "Teranga Saveurs",
        "nom": "Thiéboudienne Rouge Traditionnelle (Ceebu Jën Penda Mbaye)",
        "description": "Le légendaire Thiéboudienne Rouge sénégalais préparé avec du mérou frais (Thiof), sa farce aromatique persil-ail (Rof), légumes frais de saison (chou, manioc, carotte, gombo, aubergine) et riz cassé parfumé à la tomate.",
        "prix_base": 3500.00,
        "image_url": "http://127.0.0.1:8000/media/dishes/thieb_rouge_teranga.png",
        "temps_preparation": "20-25 min",
        "tags": ["Thiéboudienne", "Cuisine sénégalaise", "Poisson", "Plat National", "Thiof"],
        "variantes": [
            {"titre": "Portion Classique (1 pers.)", "sous_titre": "Tranche de Thiof & légumes complets", "surcout_prix": 0.00, "est_requis": True, "ordre": 1},
            {"titre": "Portion Royale Gourmande", "sous_titre": "Double portion de Thiof & légumes extra", "surcout_prix": 1500.00, "est_requis": False, "ordre": 2},
        ],
        "options": [
            {"type_option": OptionProduit.TYPE_SAUCE, "titre": "Sauce Tamarin Pimentée", "sous_titre": "Sauce piquante maison", "surcout_prix": 300.00, "est_inclus": False, "ordre": 1},
            {"type_option": OptionProduit.TYPE_SUPPLEMENT, "titre": "Légumes supplémentaires", "sous_titre": "Chou, manioc, gombo & carotte", "surcout_prix": 500.00, "est_inclus": False, "ordre": 2},
            {"type_option": OptionProduit.TYPE_SUPPLEMENT, "titre": "Citron vert & piment frais", "sous_titre": "Assaisonnement à table", "surcout_prix": 0.00, "est_inclus": True, "ordre": 3},
        ]
    },
    {
        "etablissement_nom": "Chez Penda",
        "nom": "Thiéboudienne Blanche Authentique (Ceebu Jën Blanc & Beugueul)",
        "description": "Thiéboudienne Blanc d'exception au poisson Thiof farci, accompagné de ses sauces traditionnelles (Beugueule aux feuilles d'oseille et Soumbala), légumes du pays mijotés et son ramequin de riz grillé croquant (Xons).",
        "prix_base": 3000.00,
        "image_url": "http://127.0.0.1:8000/media/dishes/thieb_blanc_chez_penda.jpg",
        "temps_preparation": "15-20 min",
        "tags": ["Ceebu Jën Blanc", "Cuisine sénégalaise", "Beugueule", "Xons", "Fait Maison"],
        "variantes": [
            {"titre": "Plat Individuel", "sous_titre": "Portion généreuse 1 personne", "surcout_prix": 0.00, "est_requis": True, "ordre": 1},
            {"titre": "Plat Duo Familial", "sous_titre": "Portion pour 2 personnes", "surcout_prix": 2500.00, "est_requis": False, "ordre": 2},
        ],
        "options": [
            {"type_option": OptionProduit.TYPE_SAUCE, "titre": "Extra Sauce Beugueul (Oseille)", "sous_titre": "Sauce verte acidulée", "surcout_prix": 400.00, "est_inclus": True, "ordre": 1},
            {"type_option": OptionProduit.TYPE_SUPPLEMENT, "titre": "Ramequin de Xons supplémentaires", "sous_titre": "Riz grillé croustillant", "surcout_prix": 500.00, "est_inclus": False, "ordre": 2},
        ]
    },
    {
        "etablissement_nom": "Le Baobab Gourmand",
        "nom": "Thiéboudienne Royale aux Crevettes & Thiof Braisé",
        "description": "Thiéboudienne d'exception servi dans son faitout garni d'une tranche généreuse de Thiof doré au four, crevettes sautées, citron vert fraîchement pressé, gombo tendre et aubergine farcie.",
        "prix_base": 5000.00,
        "image_url": "http://127.0.0.1:8000/media/dishes/thieb_royal_baobab.jpg",
        "temps_preparation": "25-30 min",
        "tags": ["Thiéboudienne Royal", "Crevettes", "Thiof Braisé", "Gastronomie Sénégalais"],
        "variantes": [
            {"titre": "Faitout Individuel Royal", "sous_titre": "Served hot in premium platter", "surcout_prix": 0.00, "est_requis": True, "ordre": 1},
            {"titre": "Faitout Prestige 3 personnes", "sous_titre": "Garni de crevettes géantes & 3 poissons", "surcout_prix": 6000.00, "est_requis": False, "ordre": 2},
        ],
        "options": [
            {"type_option": OptionProduit.TYPE_SUPPLEMENT, "titre": "Portion de Crevettes géantes (x4)", "sous_titre": "Crevettes sautées à l'ail", "surcout_prix": 2000.00, "est_inclus": False, "ordre": 1},
            {"type_option": OptionProduit.TYPE_SAUCE, "titre": "Sauce Piment Doux & Citron vert", "sous_titre": "Sauce acidulée piquante", "surcout_prix": 300.00, "est_inclus": True, "ordre": 2},
        ]
    },
    {
        "etablissement_nom": "Saveurs de Ndar",
        "nom": "Ceebu Jën Ndar Penda Mbaye Spécial Saint-Louis",
        "description": "Recette séculaire de la capitale gastronomique Saint-Louis (Ndar) : Riz rouge somptueux, tranche de Capitaine/Thiof, crevettes géantes sautées, gombos entiers, chou braisé et sauce tamarin artisanale.",
        "prix_base": 4500.00,
        "image_url": "http://127.0.0.1:8000/media/dishes/thieb_ndar_penda.jpg",
        "temps_preparation": "20-25 min",
        "tags": ["Saint-Louis", "Ndar", "Ceebu Jën", "Crevettes", "Vendeur Artisan"],
        "variantes": [
            {"titre": "Portion Gourmet Ndar", "sous_titre": "Servi en barquette étanche premium", "surcout_prix": 0.00, "est_requis": True, "ordre": 1},
            {"titre": "Barquette XL Familiale", "sous_titre": "2 personnes + boisson locale offerte", "surcout_prix": 3500.00, "est_requis": False, "ordre": 2},
        ],
        "options": [
            {"type_option": OptionProduit.TYPE_SAUCE, "titre": "Sauce Piment Tamarin Maison", "sous_titre": "Recette secrète de Ndar", "surcout_prix": 400.00, "est_inclus": True, "ordre": 1},
            {"type_option": OptionProduit.TYPE_SUPPLEMENT, "titre": "Bol Gueule-Tapée Xons & Soumbala", "sous_titre": "Riz gratiné d'exception", "surcout_prix": 500.00, "est_inclus": False, "ordre": 2},
        ]
    }
]

created_count = 0
for d in DISHES_DATA:
    etab = Etablissement.objects.filter(nom__icontains=d["etablissement_nom"]).first()
    if not etab:
        print(f"Etablissement '{d['etablissement_nom']}' non trouve dans la BD.")
        continue
    
    produit, _ = Produit.objects.update_or_create(
        etablissement=etab,
        nom=d["nom"],
        defaults={
            "categorie": cat_senegal,
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
    print(f"OK: Plat [{produit.id}] '{produit.nom[:30]}...' créé pour {etab.nom}")

print(f"\nTOTAL PLATS THIEBOUDIENNE CREES: {created_count}")
