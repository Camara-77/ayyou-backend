import os
import sys
import django
import random

# Setup Django environment
sys.path.append('c:\\Users\\HP\\Desktop\\Ayyou-backend')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from apps.users.models import Utilisateur, Role, UtilisateurRole, ProfilLivreur, ProfilClient
from apps.catalog.models import Categorie, Etablissement, Produit, VarianteProduit, OptionProduit

print("Starting AYYOU database seeding script...")

# 1. Ensure Roles exist
roles_dict = {}
for role_name in [Role.CLIENT, Role.RESTAURANT, Role.VENDEUR, Role.LIVREUR, Role.ADMINISTRATEUR]:
    role_obj, _ = Role.objects.get_or_create(nom=role_name, defaults={'description': f'Rôle {role_name}'})
    roles_dict[role_name] = role_obj

# Helper function to create or get user with password
def create_account(email, telephone, prenom, nom, role_name, password="Password123!"):
    user = Utilisateur.objects.filter(email=email).first()
    if not user:
        user = Utilisateur.objects.filter(numero_telephone=telephone).first()
    if not user:
        user = Utilisateur.objects.create_user(
            email=email,
            numero_telephone=telephone,
            password=password,
            prenom=prenom,
            nom=nom,
            est_actif=True,
            est_verifie=True
        )
    else:
        user.set_password(password)
        user.save()

    # Assign role
    role_obj = roles_dict[role_name]
    UtilisateurRole.objects.get_or_create(utilisateur=user, role=role_obj)
    return user, password

# List to collect credentials
all_credentials = []

# 2. Create Livreurs (Delivery Drivers)
livreurs_data = [
    ("mamadou.diallo@ayyou.sn", "+221771000001", "Mamadou", "Diallo", "MOTO", "Yamaha YBR", "DK-1001-AY"),
    ("ibrahima.sow@ayyou.sn", "+221771000002", "Ibrahima", "Sow", "MOTO", "Honda CB", "DK-1002-AY"),
    ("ousmane.diop@ayyou.sn", "+221771000003", "Ousmane", "Diop", "VOITURE", "Peugeot 208", "DK-1003-AY"),
    ("babacar.ndiaye@ayyou.sn", "+221771000004", "Babacar", "Ndiaye", "MOTO", "Kymco Agility", "DK-1004-AY"),
    ("cheikh.tall@ayyou.sn", "+221771000005", "Cheikh", "Tall", "MOTO", "TVS King", "DK-1005-AY"),
    ("modou.fall@ayyou.sn", "+221771000006", "Modou", "Fall", "VELO", "BTWIN Rockrider", "DK-1006-AY"),
    ("samba.ba@ayyou.sn", "+221771000007", "Samba", "Ba", "MOTO", "Yamaha DTMX", "DK-1007-AY"),
    ("alioune.faye@ayyou.sn", "+221771000008", "Alioune", "Faye", "MOTO", "Bajaj Boxer", "DK-1008-AY"),
    ("omar.cisse@ayyou.sn", "+221771000009", "Omar", "Cissé", "VOITURE", "Renault Clio", "DK-1009-AY"),
    ("abdoulaye.kane@ayyou.sn", "+221771000010", "Abdoulaye", "Kane", "MOTO", "TVS Apache", "DK-1010-AY"),
    ("demba.seck@ayyou.sn", "+221771000011", "Demba", "Seck", "MOTO", "Yamaha Crux", "DK-1011-AY"),
    ("moustapha.sy@ayyou.sn", "+221771000012", "Moustapha", "Sy", "MOTO", "Honda Ace", "DK-1012-AY"),
]

print("Creating Livreurs...")
for email, tel, prenom, nom, vehicule, marque, immat in livreurs_data:
    user, pwd = create_account(email, tel, prenom, nom, Role.LIVREUR)
    user.mode_actif = Utilisateur.MODE_LIVREUR
    user.save()

    profil, _ = ProfilLivreur.objects.get_or_create(utilisateur=user)
    profil.statut_verification = ProfilLivreur.STATUT_VALIDE
    profil.est_disponible = True
    profil.type_vehicule = vehicule
    profil.marque = marque
    profil.immatriculation = immat
    profil.secteur_intervention = "Dakar & Banlieue"
    profil.save()

    all_credentials.append({
        "role": "LIVREUR",
        "nom_complet": f"{prenom} {nom}",
        "email": email,
        "telephone": tel,
        "password": pwd,
        "details": f"Livreur ({vehicule} {marque})"
    })

# 3. Create Establishments Data (Restaurants, Pâtisseries, Vendeurs, Boutiques)
# Target: 50 Establishments

establishments_raw_data = [
    # RESTAURANTS SÉNÉGALAIS
    ("Le Teranga Palace", "RESTAURANT", "Cuisine Sénégalaise & Grillades", "Almadies, Dakar", "Chez Le Teranga Palace, dégustez le vrai Thiéboudienne Penda Mbaye et les meilleures grillades du Plateau.", "https://images.unsplash.com/photo-1555396273-367ea4eb4db5?w=500", "Sénégalais"),
    ("Chez Loutcha", "RESTAURANT", "Spécialités Ouest-Africaines", "Rue Mousse Diop, Plateau, Dakar", "Instituion dakaroise réputée pour ses plats généreux, Yassa, Mafé et Thieb.", "https://images.unsplash.com/photo-1517248135467-4c7edcad34c4?w=500", "Sénégalais"),
    ("La Pirogue des Saveurs", "RESTAURANT", "Cuisine Traditionnelle & Poisson", "Ngor, Dakar", "Poissons frais du jour, Soupou Kandia aux gombos et fruits de mer grillés.", "https://images.unsplash.com/photo-1537047902294-62a40c20a6ae?w=500", "Sénégalais"),
    ("Mamie Thiébou Dakar", "VENDEUR", "Plats Fait-Maison Sénégalais", "Fann Résidence, Dakar", "Authentique cuisine sénégalaise préparée avec amour par Mamie.", "https://images.unsplash.com/photo-1504674900247-0877df9cc836?w=500", "Sénégalais"),
    ("Le Baobab Gourmand", "RESTAURANT", "Thiébou Dieune & Yassa Royale", "Médina, Dakar", "Recettes ancestrales sénégalaises, riz au poisson rouge et caldou parfumé.", "https://images.unsplash.com/photo-1543007630-9710e4a00a20?w=500", "Sénégalais"),
    ("Saly Resto Teranga", "RESTAURANT", "Plats du Terroir Sénégalais", "Point E, Dakar", "Délicieux Mbaxal de salagne, Coki et Thiébou Yapp gourmand.", "https://images.unsplash.com/photo-1552566626-52f8b828add9?w=500", "Sénégalais"),

    # DIBITERIE & GRILLADES
    ("Dibiterie Haoussa Chef Moussa", "VENDEUR", "Viande d'Agneau Grillée au Feu de Bois", "Grand Yoff, Dakar", "Agneau braisé épicé, piment haoussa authentique et oignons confits.", "https://images.unsplash.com/photo-1544025162-d76694265947?w=500", "Dibiterie"),
    ("Grillades des Almadies", "RESTAURANT", "Brochettes, Poulet & Agneau Braisé", "Route des Almadies, Dakar", "Les meilleures grillades au charbon de bois face à l'océan.", "https://images.unsplash.com/photo-1529193591184-b1d58069ecdd?w=500", "Dibiterie"),
    ("Le Jardin du Braisé", "RESTAURANT", "Dibiterie Moderne & Steaks", "Mermoz, Dakar", "Viandes maturées, dibi d'agneau tendre et saucisses grillées.", "https://images.unsplash.com/photo-1558030006-450675393462?w=500", "Dibiterie"),
    ("Tata Amina Grillades", "VENDEUR", "Poulet Braisé & Dibi Spécial", "Parcelles Assainies, Dakar", "Poulet entier braisé, marinade secret oignons & moutarde.", "https://images.unsplash.com/photo-1598515214211-89d3c73ae83b?w=500", "Dibiterie"),
    ("Dibi Express Plateau", "RESTAURANT", "Dibiterie de Nuit & Brochettes", "Avenue Ponty, Plateau", "Brochettes de bœuf succulentes et dibi agneau emballé sous papier.", "https://images.unsplash.com/photo-1498654896293-37aacf113fd9?w=500", "Dibiterie"),

    # FAST-FOOD & BURGERS
    ("Planet Burger Dakar", "RESTAURANT", "Burgers Gourmet & Tacos", "Sacré-Cœur 3, Dakar", "Burgers géants au cheddar fondant, frites maison et milkshakes.", "https://images.unsplash.com/photo-1568901346375-23c9450c58cd?w=500", "Fast-Food"),
    ("Chez Awa Fast-Food", "VENDEUR", "Shawarma, Tacos & Chawarma", "Ouakam, Dakar", "Tacos XXL 3 viandes, sauce fromagère maison et frites croustillantes.", "https://images.unsplash.com/photo-1561758033-d89a9ad46330?w=500", "Fast-Food"),
    ("O'Tacos Dakar", "RESTAURANT", "French Tacos Sur-Mesure", "Almadies, Dakar", "Le véritable French Tacos avec sa sauce fromagère légendaire.", "https://images.unsplash.com/photo-1586190848861-99aa4a171e90?w=500", "Fast-Food"),
    ("Dakar Urban Burger", "RESTAURANT", "Smash Burgers & Hot-Dogs", "Simbad, Mermoz", "Smash burger double steak crémeux, bacon croustillant et frites truffées.", "https://images.unsplash.com/photo-1550547660-d9450f859349?w=500", "Fast-Food"),
    ("KFC Dakar Corniche", "RESTAURANT", "Poulet Frit Croustillant & Buckets", "Corniche Ouest, Dakar", "Poulet frit secret aux 11 herbes et épices, tenders et zinger burgers.", "https://images.unsplash.com/photo-1626082927389-6cd097cdc6ec?w=500", "Fast-Food"),

    # BOULANGERIE & PÂTISSERIE
    ("Pâtisserie Les Ambassades", "RESTAURANT", "Viennoiseries, Gâteaux & Brunch", "Fann Hock, Dakar", "Pâtisserie fine française, croissants au beurre, mille-feuilles et entremets.", "https://images.unsplash.com/photo-1509440159596-0249088772ff?w=500", "Pâtisserie"),
    ("Maison Eric Kayser Dakar", "RESTAURANT", "Boulangerie Artisanal & Pains Bio", "Avenue Roume, Plateau", "Pains au levain naturel, tartes aux fruits de saison et viennoiseries raffinées.", "https://images.unsplash.com/photo-1555507036-ab1f4038808a?w=500", "Pâtisserie"),
    ("Brioche Dorée Dakar", "RESTAURANT", "Sandwichs, Brioches & Pâtisserie", "Liberte 6, Dakar", "La pause gourmande référence à Dakar : quiches, chouquettes et éclairs.", "https://images.unsplash.com/photo-1578985545062-69928b1d9587?w=500", "Pâtisserie"),
    ("Pâtisserie Les Madeleines", "RESTAURANT", "Salons de Thé & Pâtisserie Fine", "Avenue Pasteur, Dakar", "Gâteaux de mariage, macaron parisien et chocolat chaud artisanal.", "https://images.unsplash.com/photo-1587314168485-3236d6710814?w=500", "Pâtisserie"),
    ("Sokhna Douceurs", "VENDEUR", "Gâteaux Personnalisés & Crêpes", "Keur Gorgui, Dakar", "Cupcakes artistiques, crêpes garnies Nutella et cakes faits maison.", "https://images.unsplash.com/photo-1535141192574-5d4897c13136?w=500", "Pâtisserie"),
    ("Pâtisserie Saint-Germain", "RESTAURANT", "Tartes, Éclairs & Viennoiseries", "Ngor Village, Dakar", "Pâtisserie d'excellence au cœur de Ngor.", "https://images.unsplash.com/photo-1517433670267-08bbd4be890f?w=500", "Pâtisserie"),

    # JUS & BOISSONS LOCALES
    ("Oumou Jus Nectars", "VENDEUR", "Jus Naturels Bissap, Bouye & Corossol", "Hann Maristes, Dakar", "100% pur fruit naturel : Bissap menthe, Bouye baobab et Ditakh vert.", "https://images.unsplash.com/photo-1551024709-8f23befc6f87?w=500", "Boissons"),
    ("Saveurs des Tropiques", "RESTAURANT", "Cocktails de Fruits & Smoothies", "Virage, Almadies", "Smoothies mangue passion, cocktails gingembre ananas sans alcool.", "https://images.unsplash.com/photo-1534353473418-4cfa6c56fd38?w=500", "Boissons"),
    ("Maison du Bissap Dakar", "VENDEUR", "Infusions & Sirops Artisanaux", "Cité Keur Gorgui", "Sirops concentrés de bissap blanc et rouge, ditakh et madd frais.", "https://images.unsplash.com/photo-1621263764928-df1444c5e859?w=500", "Boissons"),

    # POISSONS & FRUITS DE MER
    ("Le Lagon 1", "RESTAURANT", "Gastronomie Poissons & Langoustes", "Route de la Corniche Est, Dakar", "Restaurant panoramique sur la mer : carpaccio de thon rouge et langoustes braisées.", "https://images.unsplash.com/photo-1534422298391-e4f8c172dddb?w=500", "Poissons"),
    ("Chez Cabani Ngor", "RESTAURANT", "Poisson Braisé sur l'Île de Ngor", "Île de Ngor, Dakar", "Espadon braisé au feu de bois, Gambas géantes et crevettes sautées à l'ail.", "https://images.unsplash.com/photo-1519708227418-c8fd9a32b7a2?w=500", "Poissons"),
    ("La Marée Gourmande", "RESTAURANT", "Plateau de Fruits de Mer", "Yoff Beach, Dakar", "Huitres de Joal, moules marinières et thon grillé avec aloco.", "https://images.unsplash.com/photo-1565680018434-b513d5e5fd47?w=500", "Poissons"),

    # CUISINE IVOIRIENNE
    ("L'Attiéké d'Abidjan", "RESTAURANT", "Garba, Alloco & Poisson Grillé", "Grand Yoff, Dakar", "Véritable Garba à l'attiéké de Grand-Lahou, thon frit et piment vert frais.", "https://images.unsplash.com/photo-1541544741938-0af808871cc0?w=500", "Ivoirienne"),
    ("Maquis Le Cocody", "RESTAURANT", "Kedjenou de Poulet & Placali", "Sacre-Coeur 2, Dakar", "Kedjenou de poulet cuit en pot de terre, sauce graine et foutou banane.", "https://images.unsplash.com/photo-1512621776951-a57141f2eefd?w=500", "Ivoirienne"),
    ("Chez Tantie Akissi", "VENDEUR", "Alloco, Poulet Piqué & Choukouya", "Cité Fadia, Dakar", "Choukouya de bœuf juteux, alloco mûr doré et sauce piment maison.", "https://images.unsplash.com/photo-1565299585323-38d6b0865b47?w=500", "Ivoirienne"),

    # PIZZA
    ("La Pizzeria Di Napoli", "RESTAURANT", "Pizzas au Feu de Bois Italiennes", "Fann Résidence, Dakar", "Pizzas artisanales napolitaines, pâte fermentée 48h et mozzarella di bufala.", "https://images.unsplash.com/photo-1513104890138-7c749659a591?w=500", "Pizza"),
    ("Pizza Inn Dakar", "RESTAURANT", "Pizzas Pan & Calzone Gourmet", "Avenue Cheikh Anta Diop", "Pizzas généreuses 4 fromages, pepperoni suprême et pâtes soufflées.", "https://images.unsplash.com/photo-1574071318508-1cdbab80d002?w=500", "Pizza"),
    ("La Piazzetta Almadies", "RESTAURANT", "Pizzas Romaines & Pastas", "Route des Almadies", "Pizza Reine, Margherita fraîche et lasagnes bolognaises maison.", "https://images.unsplash.com/photo-1534308983496-4fabb1a015ee?w=500", "Pizza"),

    # DESSERTS & GLACES
    ("N'ice Cream Dakar", "RESTAURANT", "Glaces Artisanales & Gaufres", "Avenue Ponty & Almadies", "Glaces italiennes onctueuses, parfums vanille Bourbon, pistache et bouye.", "https://images.unsplash.com/photo-1563805042-7684c019e1cb?w=500", "Desserts"),
    ("Paillettes & Chocolat", "VENDEUR", "Fondues au Chocolat & Milkshakes", "Point E, Dakar", "Milkshakes toppings géants, donuts et fondues au chocolat belge.", "https://images.unsplash.com/photo-1572490122747-3968b75cc699?w=500", "Desserts"),

    # CUISINE MALIENNE
    ("Le Mandingue Bamako", "RESTAURANT", "Fakoye, Tiguadèguèna & Djouka", "Médina, Dakar", "Cuisine du Mali authentique : riz au gras, poulet tiguadèguèna à la pâte d'arachide.", "https://images.unsplash.com/photo-1546069901-ba9599a7e63c?w=500", "Malienne"),

    # CUISINE MAROCAINE
    ("Le Riad de Fès", "RESTAURANT", "Couscous Royal & Tajines Berberes", "Les Almadies, Dakar", "Tajine d'agneau aux pruneaux et amandes grillées, couscous 7 légumes et thé à la menthe.", "https://images.unsplash.com/photo-1511690656952-34342bb7c2f2?w=500", "Marocaine"),

    # SALADES & HEALTHY
    ("Green & Co Dakar", "RESTAURANT", "Poke Bowls, Salades & Jus Detox", "Point E, Dakar", "Poke bowl thon frais, quinoa bio, salades César et wrap saumon avocat.", "https://images.unsplash.com/photo-1512621776951-a57141f2eefd?w=500", "Salades"),

    # CUISINE DU MONDE & ASIATIQUE
    ("Le Jardin Thaï", "RESTAURANT", "Pad Thaï, Nems & Sushis", "Fann Résidence, Dakar", "Pad Thaï aux crevettes géantes, curry vert au lait de coco et sushis frais.", "https://images.unsplash.com/photo-1559314809-0d155014e29e?w=500", "Cuisine du monde"),
    ("L'Alkimia Fine Dining", "RESTAURANT", "Gastronomie Internationale", "Almadies, Dakar", "Cuisine d'auteur fusion méditerranéenne et asiatique.", "https://images.unsplash.com/photo-1544025162-d76694265947?w=500", "Cuisine du monde"),

    # STREET FOOD & TANGANA
    ("Tangana Chez Moussa & Fils", "VENDEUR", "Omelette Viande, Foie & Piment", "Médina Rue 6 x 11", "Le Tangana mythique : omelette baveuse à la viande hachée, pain chaud et mayo.", "https://images.unsplash.com/photo-1525351484163-7529414344d8?w=500", "Tangana"),
    ("Street Food Dakar Express", "VENDEUR", "Fataya, Pastels & Beignets", "HLM 5, Dakar", "Pastels de poisson croustillants avec sauce tomate piquante maison.", "https://images.unsplash.com/photo-1561758033-d89a9ad46330?w=500", "Street food"),

    # FRUITS & FRAÎCHEUR
    ("Marché Frais Bio Dakar", "RESTAURANT", "Corbeilles de Fruits Cut & Fresh", "Mermoz, Dakar", "Pastèques sucrées découpées, mangues Kent mûres et ananas de Casamance.", "https://images.unsplash.com/photo-1619566636858-adf3ef46400b?w=500", "Fruits"),
]

print(f"Creating {len(establishments_raw_data)} Establishments...")

created_establishments = []
for index, (nom, type_etab, specialite, adresse, desc, logo_url, cat_name) in enumerate(establishments_raw_data, start=1):
    slug_name = nom.lower().replace(" ", "_").replace("'", "").replace("&", "et")
    email = f"owner.{slug_name}{index}@ayyou.sn"
    tel = f"+22177{2000000 + index}"
    
    user_role = Role.RESTAURANT if type_etab == "RESTAURANT" else Role.VENDEUR
    owner_user, pwd = create_account(email, tel, "Propriétaire", nom, user_role)

    # Find matching category if exists
    cat_obj = Categorie.objects.filter(nom__icontains=cat_name).first()

    etab, created = Etablissement.objects.get_or_create(
        nom=nom,
        defaults={
            'type_etablissement': type_etab,
            'proprietaire': owner_user,
            'logo_url': logo_url,
            'couverture_url': logo_url,
            'slogan': f"Le meilleur de {specialite} à Dakar",
            'description': desc,
            'adresse': adresse,
            'telephone': tel,
            'specialite': specialite,
            'statut': Etablissement.STATUT_OUVERT,
            'statut_verification': Etablissement.STATUT_VALIDE,
            'est_verifie': True,
            'note_moyenne': round(random.uniform(4.3, 4.9), 2),
            'nombre_avis': random.randint(35, 320)
        }
    )
    if not created:
        etab.type_etablissement = type_etab
        etab.proprietaire = owner_user
        etab.statut_verification = Etablissement.STATUT_VALIDE
        etab.est_verifie = True
        etab.save()

    created_establishments.append(etab)

    all_credentials.append({
        "role": type_etab,
        "nom_complet": nom,
        "email": email,
        "telephone": tel,
        "password": pwd,
        "details": f"{type_etab} ({specialite} - {adresse})"
    })

print(f"Successfully created {len(created_establishments)} Establishments and Owners.")

# 4. Create authentic Dishes (5 Dishes per category, linked to 5 different sellers)
# Also each establishment will have 10+ products in its menu.

categories_dishes_catalog = {
    "Cuisine sénégalaise": [
        ("Thiéboudienne Penda Mbaye", "Le plat national sénégalais : riz rouge au mérou (thiof), légumes frais (chou, manioc, carotte) et roff persillé.", 3500, "https://images.unsplash.com/photo-1546069901-ba9599a7e63c?w=500"),
        ("Mafé Viande d'Agneau", "Onctueux ragoût à la pâte d'arachide artisanale, viande d'agneau tendre et patates douces.", 3000, "https://images.unsplash.com/photo-1547496592-15782374be14?w=500"),
        ("Soupou Kandia aux Fruits de Mer", "Sauce gombo traditionnelle parfumée à l'huile de palme, crevettes, crabes et poisson fumé.", 4000, "https://images.unsplash.com/photo-1512621776951-a57141f2eefd?w=500"),
        ("Mbaxal de Salagne", "Riz crémeux préparé au poisson séché salagne, arachides pilées et piment frais.", 2500, "https://images.unsplash.com/photo-1504674900247-0877df9cc836?w=500"),
        ("Yassa Poulet Braisé", "Poulet fermier mariné au citron vert, oignons confits au feu de bois et moutarde à l'ancienne.", 3200, "https://images.unsplash.com/photo-1598515214211-89d3c73ae83b?w=500")
    ],
    "Dibiterie & Grillades": [
        ("Dibi d'Agneau Haoussa", "Viande d'agneau braisée au feu de bois, oignons marinés et piment haoussa en poudre.", 4500, "https://images.unsplash.com/photo-1544025162-d76694265947?w=500"),
        ("Poulet Braisé Entier", "Poulet mariné au gingembre et piment doux, braisé lentement avec alloco.", 6000, "https://images.unsplash.com/photo-1529193591184-b1d58069ecdd?w=500"),
        ("Brochettes de Bœuf Capitaine", "Brochettes de filet de bœuf tendre grillées, servies avec sauce oignon moutarde.", 3500, "https://images.unsplash.com/photo-1555939594-58d7cb561ad1?w=500"),
        ("Côtelettes d'Agneau Grillées", "Côtelettes marinées aux herbes aromatiques, servies avec frites ou fufu.", 5000, "https://images.unsplash.com/photo-1544025162-d76694265947?w=500"),
        ("Saucisses de Bœuf Braisées", "Saucisses de bœuf épicées faites maison, dorées sur le gril.", 3000, "https://images.unsplash.com/photo-1529193591184-b1d58069ecdd?w=500")
    ],
    "Fast-Food": [
        ("Double Smash Bacon Burger", "Deux steaks de bœuf smashés, cheddar fondant, bacon croustillant et sauce secret.", 4500, "https://images.unsplash.com/photo-1568901346375-23c9450c58cd?w=500"),
        ("French Tacos 3 Viandes XL", "Tortilla géante fourrée au poulet pané, viande hachée, cordon bleu et sauce fromagère.", 4000, "https://images.unsplash.com/photo-1561758033-d89a9ad46330?w=500"),
        ("Bucket 10 Tenders Frit", "Aiguillettes de poulet marinées ultra-croustillantes avec 2 sauces au choix.", 5500, "https://images.unsplash.com/photo-1626082927389-6cd097cdc6ec?w=500"),
        ("Shawarma Poulet Fromage", "Pain pita artisanal garni de poulet rôti à la broche, salade, frites et sauce ail.", 2500, "https://images.unsplash.com/photo-1529006557810-274b9b2fc783?w=500"),
        ("Hot-Dog New-Yorkais Gourmet", "Saucisse géante géante grillée, oignons frits, pickles et relish moutarde miel.", 2800, "https://images.unsplash.com/photo-1619740455993-9e612b1af08a?w=500")
    ],
    "Boulangerie Pâtisserie": [
        ("Mille-Feuille Pur Beurre Cerise", "Feuilletage croustillant, crème diplomate vanille et cerises confites au sirop.", 2000, "assets/banners/banner_patisserie.jpg"),
        ("Croissant au Beurre AOP", "Véritable croissant feuilleté au beurre frais de Normandie, doré au four.", 800, "https://images.unsplash.com/photo-1555507036-ab1f4038808a?w=500"),
        ("Éclair au Chocolat Noir Valrhona", "Chou moelleux garni d'une crème crémeuse au chocolat intense 70%.", 1500, "https://images.unsplash.com/photo-1578985545062-69928b1d9587?w=500"),
        ("Tartelette aux Fraises Fraîches", "Pâte sablée croustillante, crème pâtissière et fraises mûres nappées.", 2200, "https://images.unsplash.com/photo-1587314168485-3236d6710814?w=500"),
        ("Pain au Chocolat Gourmand", "Viennoiserie pure beurre garnie de 2 barres de chocolat noir.", 900, "https://images.unsplash.com/photo-1509440159596-0249088772ff?w=500")
    ],
    "Jus & Boissons locales": [
        ("Nectar de Bissap Menthe Fraîche", "Jus de fleurs d'hibiscus infusé à la menthe douce et à la vanille, 50cl.", 1000, "https://images.unsplash.com/photo-1551024709-8f23befc6f87?w=500"),
        ("Jus de Bouye Pur Baobab", "Boisson crémeuse au pain de singe (fruit du baobab) enrichi au lait et muscade.", 1200, "https://images.unsplash.com/photo-1534353473418-4cfa6c56fd38?w=500"),
        ("Cocktail Ditakh Vert", "Jus rafraîchissant au fruit ditakh sauvage riche en vitamine C.", 1500, "https://images.unsplash.com/photo-1621263764928-df1444c5e859?w=500"),
        ("Jus de Gingembre Épicé (Gnamakoudji)", "Jus stimulant au gingembre pur, jus de citron vert et ananas.", 1000, "https://images.unsplash.com/photo-1551024709-8f23befc6f87?w=500"),
        ("Smoothie Mangue Passion Casamance", "Mangue fraîche mixée avec fruit de la passion et jus d'orange.", 2000, "https://images.unsplash.com/photo-1534353473418-4cfa6c56fd38?w=500")
    ],
    "Poissons & Fruits de mer": [
        ("Thiof Grillé au Feu de Bois", "Mérou royal grillé à l'ail et aux fines herbes, accompagné de bananes aloco.", 6500, "https://images.unsplash.com/photo-1519708227418-c8fd9a32b7a2?w=500"),
        ("Gambas Géantes Poêlées au Persillade", "Gambas locales sautées au beurre d'ail et persil frais, riz parfumé.", 7500, "https://images.unsplash.com/photo-1565680018434-b513d5e5fd47?w=500"),
        ("Sole Grillée au Citron Vert", "Sole fraîche entière braisée, servie avec frites maison et salade verte.", 5500, "https://images.unsplash.com/photo-1534422298391-e4f8c172dddb?w=500"),
        ("Brochettes de Lotterot & Crevettes", "Brochettes de poisson blanc lotte et crevettes marinées au paprika doux.", 4800, "https://images.unsplash.com/photo-1519708227418-c8fd9a32b7a2?w=500"),
        ("Plateau Royal de Fruits de Mer", "Huitres de Joal, crevettes, crabes, bucins et moules marinières pour 2 personnes.", 15000, "https://images.unsplash.com/photo-1565680018434-b513d5e5fd47?w=500")
    ],
    "Cuisine ivoirienne": [
        ("Garba Thon Frit & Attiéké", "Semoule de manioc attiéké servie avec darne de thon frit croustillant et piment rond.", 2500, "https://images.unsplash.com/photo-1541544741938-0af808871cc0?w=500"),
        ("Alloco Poulet Braisé Piquant", "Bananes plantains frites bien dorées servies avec quart de poulet braisé.", 3000, "https://images.unsplash.com/photo-1565299585323-38d6b0865b47?w=500"),
        ("Kedjenou de Poulet en Pot", "Ragoût stéamé de poulet aux tomates, oignons et piments en pot d'argile.", 4500, "https://images.unsplash.com/photo-1512621776951-a57141f2eefd?w=500"),
        ("Sauce Graine & Foutou Banane", "Sauce aux noix de palme concentrée avec viandes sélectionnées et foutou doux.", 4000, "https://images.unsplash.com/photo-1541544741938-0af808871cc0?w=500"),
        ("Choukouya de Bœuf", "Bœuf braisé émincé sur braises fines, assaisonné aux épices d'Abidjan.", 3500, "https://images.unsplash.com/photo-1565299585323-38d6b0865b47?w=500")
    ],
    "Pizza": [
        ("Pizza Reine Royale 33cm", "Base tomate San Marzano, mozzarella fior di latte, jambon, champignons de paris.", 5000, "https://images.unsplash.com/photo-1513104890138-7c749659a591?w=500"),
        ("Pizza 4 Fromages Fondante", "Mozzarella, gorgonzola AOP, emmental et parmesan reggiano râpé.", 5500, "https://images.unsplash.com/photo-1574071318508-1cdbab80d002?w=500"),
        ("Pizza Pepperoni Spicy", "Sauce tomate épicée, double dose de pepperoni italien croustillant.", 5200, "https://images.unsplash.com/photo-1534308983496-4fabb1a015ee?w=500"),
        ("Pizza Teranga Poulet Yassa", "Création originale : mozzarella, effiloché de poulet rôti et sauce oignons citron.", 4800, "https://images.unsplash.com/photo-1513104890138-7c749659a591?w=500"),
        ("Pizza Fruits de Mer Calamars", "Crevettes sautées, chair de calamar, ail, persil et huile d'olive pimentée.", 6000, "https://images.unsplash.com/photo-1574071318508-1cdbab80d002?w=500")
    ],
    "Desserts & Glaces": [
        ("Coupe Glacée 3 Boules Gourmande", "Parfums Vanille, Chocolat Belge, Bouye baobab avec chantilly et coulis.", 2500, "https://images.unsplash.com/photo-1563805042-7684c019e1cb?w=500"),
        ("Gaufre Liégeoise Nutella Banane", "Gaufre croustillante au sucre perlé nappée de Nutella et rondelles de banane.", 2000, "https://images.unsplash.com/photo-1572490122747-3968b75cc699?w=500"),
        ("Fondant au Chocolat Coeur Coulant", "Gâteau chaud au chocolat noir avec sa boule de glace vanille Bourbon.", 2800, "https://images.unsplash.com/photo-1563805042-7684c019e1cb?w=500"),
        ("Cheesecake aux Fruits Rouges", "Cheesecake new-yorkais crémeux sur lit de biscuits spéculoos et coulis framboise.", 3000, "https://images.unsplash.com/photo-1572490122747-3968b75cc699?w=500"),
        ("Milkshake Oreo Spéculoos", "Lait frais, glace vanille, biscuits Oreo mixés et topping chantilly cacao.", 2500, "https://images.unsplash.com/photo-1563805042-7684c019e1cb?w=500")
    ],
    "Tangana": [
        ("Omelette Viande Hachée Pimentée", "Omelette 3 œufs garnie de bœuf haché, oignons sautés et sauce piment dans un pain chaud.", 1500, "https://images.unsplash.com/photo-1525351484163-7529414344d8?w=500"),
        ("Pain Foie de Mouton Sauté", "Foie de mouton tendre sauté aux oignons confits et moutarde dans pain baguette.", 1800, "https://images.unsplash.com/photo-1525351484163-7529414344d8?w=500"),
        ("Omelette Spaghetti Tangana", "Mélange iconique tangana : omelette bien dorée et spaghetti à la sauce oignon.", 1500, "https://images.unsplash.com/photo-1525351484163-7529414344d8?w=500"),
        ("Sandwich Petit Pois Viande", "Ragoût de petits pois et dés de viande servis dans un quart de pain chaud.", 1600, "https://images.unsplash.com/photo-1525351484163-7529414344d8?w=500"),
        ("Thé Ataya 3èmes Trois Shots", "Thé vert à la menthe traditionnel sénégalais fort et moussant.", 500, "https://images.unsplash.com/photo-1551024709-8f23befc6f87?w=500")
    ]
}

# Populate products so that EVERY category has dishes sold by at least 5 different establishments!
# And every establishment gets 10+ menu items!

all_db_categories = list(Categorie.objects.all())
all_db_etabs = list(Etablissement.objects.all())

print("Populating Dishes across Categories and Establishments...")

total_products_created = 0

for cat_name, dishes_list in categories_dishes_catalog.items():
    cat_obj = Categorie.objects.filter(nom__icontains=cat_name).first()
    if not cat_obj and len(all_db_categories) > 0:
        cat_obj = all_db_categories[0]

    # Assign each dish in this category to at least 5 different establishments
    for dish_name, dish_desc, base_price, img_url in dishes_list:
        # Pick 5 random establishments to offer this dish
        selected_etabs = random.sample(all_db_etabs, min(5, len(all_db_etabs)))
        for etab in selected_etabs:
            prod, created = Produit.objects.get_or_create(
                etablissement=etab,
                nom=dish_name,
                defaults={
                    'categorie': cat_obj,
                    'description': dish_desc,
                    'prix_base': base_price,
                    'image_url': img_url,
                    'est_disponible': True,
                    'stock_disponible': 100,
                    'stock_ayyou_reserve': 50,
                    'temps_preparation': "20-30 min",
                    'nombre_likes': random.randint(12, 180)
                }
            )
            if created:
                total_products_created += 1

                # Add variants (portions)
                VarianteProduit.objects.create(
                    produit=prod,
                    titre="Portion Classique (1 pers)",
                    surcout_prix=0.00,
                    ordre=1
                )
                VarianteProduit.objects.create(
                    produit=prod,
                    titre="Portion Gourmande Tiof XL",
                    surcout_prix=1500.00,
                    ordre=2
                )

                # Add options (sauces / supplements)
                OptionProduit.objects.create(
                    produit=prod,
                    type_option=OptionProduit.TYPE_SAUCE,
                    titre="Sauce Oignon Pimentée",
                    surcout_prix=0.00,
                    est_inclus=True
                )
                OptionProduit.objects.create(
                    produit=prod,
                    type_option=OptionProduit.TYPE_SUPPLEMENT,
                    titre="Supplément Alloco",
                    surcout_prix=500.00
                )

# Ensure EVERY establishment has at least 10 products in its menu
for etab in all_db_etabs:
    curr_count = etab.produits.count()
    if curr_count < 10:
        needed = 10 - curr_count
        # Sample items from any catalog category
        sample_dishes = []
        for dlist in categories_dishes_catalog.values():
            sample_dishes.extend(dlist)
        random.shuffle(sample_dishes)

        for i in range(needed):
            dish_name, dish_desc, base_price, img_url = sample_dishes[i % len(sample_dishes)]
            p_name = f"{dish_name} (Spécial {etab.nom})"
            cat_obj = random.choice(all_db_categories) if len(all_db_categories) > 0 else None
            
            prod, created = Produit.objects.get_or_create(
                etablissement=etab,
                nom=p_name,
                defaults={
                    'categorie': cat_obj,
                    'description': dish_desc,
                    'prix_base': base_price,
                    'image_url': img_url,
                    'est_disponible': True,
                    'stock_disponible': 100,
                    'stock_ayyou_reserve': 50,
                    'temps_preparation': "15-25 min",
                    'nombre_likes': random.randint(5, 90)
                }
            )
            if created:
                total_products_created += 1

print(f"Total new products created: {total_products_created}")
print(f"Total products in DB: {Produit.objects.count()}")

# Write all credentials to markdown artifact for user review
artifact_path = r"C:\Users\HP\.gemini\antigravity\brain\1f2cd0a4-e39b-4ef8-b924-e7e0bc2d34a3\credentials_ayyou.md"
os.makedirs(os.path.dirname(artifact_path), exist_ok=True)

with open(artifact_path, "w", encoding="utf-8") as f:
    f.write("# 🔑 Identifiants & Comptes de Connexion AYYOU\n\n")
    f.write("> [!IMPORTANT]\n")
    f.write("> Tous les comptes ci-dessous ont été enregistrés et activés dans la base de données Django (`db.sqlite3`). Vous pouvez utiliser ces identifiants pour vous connecter sur l'interface Vendeur, Restaurant ou Livreur.\n\n")

    f.write("## 🚚 Comptes Livreurs (12 Livreurs AYYOU Pro)\n\n")
    f.write("| Nom Complexe | Email de Connexion | Téléphone | Mot de Passe | Détails & Véhicule |\n")
    f.write("| :--- | :--- | :--- | :--- | :--- |\n")
    for cred in all_credentials:
        if cred["role"] == "LIVREUR":
            f.write(f"| **{cred['nom_complet']}** | `{cred['email']}` | `{cred['telephone']}` | `{cred['password']}` | {cred['details']} |\n")

    f.write("\n\n## 🍽️ Comptes Restaurants & Pâtisseries\n\n")
    f.write("| Établissement | Email Propriétaire | Téléphone | Mot de Passe | Spécialité & Adresse |\n")
    f.write("| :--- | :--- | :--- | :--- | :--- |\n")
    for cred in all_credentials:
        if cred["role"] == "RESTAURANT":
            f.write(f"| **{cred['nom_complet']}** | `{cred['email']}` | `{cred['telephone']}` | `{cred['password']}` | {cred['details']} |\n")

    f.write("\n\n## 🏠 Comptes Vendeurs à Domicile & Boutiques\n\n")
    f.write("| Établissement | Email Propriétaire | Téléphone | Mot de Passe | Spécialité & Adresse |\n")
    f.write("| :--- | :--- | :--- | :--- | :--- |\n")
    for cred in all_credentials:
        if cred["role"] == "VENDEUR":
            f.write(f"| **{cred['nom_complet']}** | `{cred['email']}` | `{cred['telephone']}` | `{cred['password']}` | {cred['details']} |\n")

print(f"Credentials written to {artifact_path}")
print("Seeding script completed successfully!")
