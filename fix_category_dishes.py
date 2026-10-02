import os
import sys
import django

sys.path.append('c:\\Users\\HP\\Desktop\\Ayyou-backend')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from apps.catalog.models import Categorie, Produit, Etablissement

print("Cleaning up category dishes alignment...")

official_categories_dishes = {
    "Cuisine sénégalaise": [
        ("Thiéboudienne Penda Mbaye", "Riz rouge au mérou (thiof), légumes frais (chou, manioc, carotte) et roff persillé."),
        ("Mafé Viande d'Agneau", "Ragoût à la pâte d'arachide artisanale, viande d'agneau tendre et patates douces."),
        ("Soupou Kandia aux Fruits de Mer", "Sauce gombo traditionnelle à l'huile de palme, crevettes, crabes et poisson fumé."),
        ("Mbaxal de Salagne", "Riz crémeux préparé au poisson séché salagne, arachides pilées et piment."),
        ("Yassa Poulet Braisé", "Poulet fermier mariné au citron vert, oignons confits au feu de bois et moutarde.")
    ],
    "Dibiterie & Grillades": [
        ("Dibi d'Agneau Haoussa", "Viande d'agneau braisée au feu de bois, oignons marinés et piment haoussa."),
        ("Poulet Braisé Entier", "Poulet mariné au gingembre et piment doux, braisé lentement avec alloco."),
        ("Brochettes de Bœuf Capitaine", "Brochettes de filet de bœuf tendre grillées avec sauce oignon moutarde."),
        ("Côtelettes d'Agneau Grillées", "Côtelettes marinées aux herbes aromatiques, servies avec frites ou fufu."),
        ("Saucisses de Bœuf Braisées", "Saucisses de bœuf épicées faites maison, dorées sur le gril.")
    ],
    "Fast-Food": [
        ("Double Smash Bacon Burger", "Deux steaks de bœuf smashés, cheddar fondant, bacon croustillant et sauce secret."),
        ("French Tacos 3 Viandes XL", "Tortilla géante fourrée au poulet pané, viande hachée, cordon bleu et sauce fromagère."),
        ("Bucket 10 Tenders Frit", "Aiguillettes de poulet marinées ultra-croustillantes avec 2 sauces au choix."),
        ("Shawarma Poulet Fromage", "Pain pita artisanal garni de poulet rôti à la broche, salade, frites et sauce ail."),
        ("Hot-Dog New-Yorkais Gourmet", "Saucisse géante grillée, oignons frits, pickles et relish moutarde miel.")
    ],
    "Boulangerie Pâtisserie": [
        ("Mille-Feuille Pur Beurre Cerise", "Feuilletage croustillant, crème diplomate vanille et cerises confites."),
        ("Croissant au Beurre AOP", "Croissant feuilleté au beurre frais de Normandie, doré au four."),
        ("Éclair au Chocolat Noir Valrhona", "Chou moelleux garni d'une crème crémeuse au chocolat intense 70%."),
        ("Tartelette aux Fraises Fraîches", "Pâte sablée croustillante, crème pâtissière et fraises mûres nappées."),
        ("Pain au Chocolat Gourmand", "Viennoiserie pure beurre garnie de 2 barres de chocolat noir.")
    ],
    "Jus & Boissons locales": [
        ("Nectar de Bissap Menthe Fraîche", "Jus d'hibiscus infusé à la menthe douce et à la vanille."),
        ("Jus de Bouye Pur Baobab", "Boisson crémeuse au pain de singe (fruit du baobab) enrichi au lait."),
        ("Cocktail Ditakh Vert", "Jus rafraîchissant au fruit ditakh sauvage riche en vitamine C."),
        ("Jus de Gingembre Épicé (Gnamakoudji)", "Jus stimulant au gingembre pur, jus de citron vert et ananas."),
        ("Smoothie Mangue Passion Casamance", "Mangue fraîche mixée avec fruit de la passion et jus d'orange.")
    ],
    "Poissons & Fruits de mer": [
        ("Thiof Grillé au Feu de Bois", "Mérou royal grillé à l'ail et aux fines herbes, accompagné d'aloco."),
        ("Gambas Géantes Poêlées au Persillade", "Gambas locales sautées au beurre d'ail et persil frais."),
        ("Sole Grillée au Citron Vert", "Sole fraîche entière braisée, servie avec frites maison."),
        ("Brochettes de Lotte & Crevettes", "Brochettes de poisson blanc lotte et crevettes marinées."),
        ("Plateau Royal de Fruits de Mer", "Huitres de Joal, crevettes, crabes et moules marinières.")
    ],
    "Cuisine ivoirienne": [
        ("Garba Thon Frit & Attiéké", "Semoule de manioc attiéké servie avec darne de thon frit croustillant."),
        ("Alloco Poulet Braisé Piquant", "Bananes plantains frites dorées servies avec quart de poulet braisé."),
        ("Kedjenou de Poulet en Pot", "Ragoût stéamé de poulet aux tomates, oignons et piments en pot d'argile."),
        ("Sauce Graine & Foutou Banane", "Sauce aux noix de palme concentrée avec viandes et foutou doux."),
        ("Choukouya de Bœuf", "Bœuf braisé émincé sur braises fines, assaisonné aux épices d'Abidjan.")
    ],
    "Pizza": [
        ("Pizza Reine Royale 33cm", "Base tomate San Marzano, mozzarella fior di latte, jambon, champignons."),
        ("Pizza 4 Fromages Fondante", "Mozzarella, gorgonzola AOP, emmental et parmesan reggiano râpé."),
        ("Pizza Pepperoni Spicy", "Sauce tomate épicée, double dose de pepperoni italien croustillant."),
        ("Pizza Teranga Poulet Yassa", "Création originale : mozzarella, effiloché de poulet rôti et sauce oignons citron."),
        ("Pizza Fruits de Mer Calamars", "Crevettes sautées, chair de calamar, ail, persil et huile pimentée.")
    ],
    "Desserts & Glaces": [
        ("Coupe Glacée 3 Boules Gourmande", "Parfums Vanille, Chocolat Belge, Bouye baobab avec chantilly."),
        ("Gaufre Liégeoise Nutella Banane", "Gaufre croustillante au sucre perlé nappée de Nutella et bananes."),
        ("Fondant au Chocolat Coeur Coulant", "Gâteau chaud au chocolat noir avec boule de glace vanille."),
        ("Cheesecake aux Fruits Rouges", "Cheesecake new-yorkais crémeux sur lit de spéculoos et coulis framboise."),
        ("Milkshake Oreo Spéculoos", "Lait frais, glace vanille, biscuits Oreo mixés et topping chantilly.")
    ],
    "Tangana": [
        ("Omelette Viande Hachée Pimentée", "Omelette 3 œufs garnie de bœuf haché et sauce piment dans pain chaud."),
        ("Pain Foie de Mouton Sauté", "Foie de mouton tendre sauté aux oignons confits dans pain baguette."),
        ("Omelette Spaghetti Tangana", "Mélange iconique tangana : omelette bien dorée et spaghetti sauce oignon."),
        ("Sandwich Petit Pois Viande", "Ragoût de petits pois et dés de viande servis dans un pain chaud."),
        ("Thé Ataya 3èmes Trois Shots", "Thé vert à la menthe traditionnel sénégalais fort et moussant.")
    ],
    "Cuisine malienne": [
        ("Tiguadèguèna Poulet Arachide", "Poulet mijoté dans une sauce onctueuse à la pâte d'arachide malienne."),
        ("Fakoye Viande d'Agneau", "Sauce aux feuilles de fakoye du Nord-Mali servi avec riz blanc."),
        ("Djouka de Fonio au Capitaine", "Fonio cuit à la vapeur avec pâte d'arachide et darna de capitaine frit."),
        ("Riz au Gras Bamako", "Riz mijoté dans un bouillon aromatique aux légumes et viande de bœuf."),
        ("Capitaine Frit Sauce Tomate", "Poisson Capitaine du fleuve Niger frit avec sauce tomate piquante.")
    ],
    "Cuisine marocaine": [
        ("Couscous Royal 7 Légumes", "Couscous fin, côtelette d'agneau, merguez, poulet et légumes confits."),
        ("Tajine d'Agneau aux Pruneaux", "Tajine d'agneau fondant mijoté aux pruneaux, amandes grillées et sésame."),
        ("Pastilla au Poulet & Amandes", "Feuilleté de warka garni de poulet effiloché, amandes et cannelle."),
        ("Tajine de Poulet au Citron Confit", "Poulet aux olives vertes, citron confit et safran pur."),
        ("Harira Marrakchia", "Soupe traditionnelle marocaine aux lentilles, pois chiches et viande.")
    ],
    "Salades & Healthy": [
        ("Poke Bowl Thon Saumon Avocat", "Thon rouge, saumon frais, riz vinaigré, edamame, mangue et graines sésame."),
        ("Salade César Poulet Grillé", "Romaine croustillante, blanc de poulet braisé, croûtons à l'ail et parmesan."),
        ("Salade Grecque Féta & Olives", "Tomates cerises, concombre, olives kalamata, féta AOP et huile d'olive."),
        ("Wrap Saumon Fumé Cream Cheese", "Tortilla blé complet garnie de saumon fumé, cream cheese et ciboulette."),
        ("Bowl Quinoa Légumes Rôtis", "Quinoa bio, courgettes rôties, pois chiches épicés et vinaigrette tahini.")
    ],
    "Cuisine du monde": [
        ("Pad Thaï Crevettes Géantes", "Nouilles de riz sautées au wok, crevettes géantes, cacahuètes et germes de soja."),
        ("Nems au Poulet Croustillants x4", "Nems artisanaux au poulet et champignons noirs avec feuille de menthe."),
        ("Plateau Sushis Mixed 16 Pcs", "Makis saumon, nigiris thon, California rolls avocat et wasabi."),
        ("Curry Vert Thaï au Lait de Coco", "Curry vert pimenté au poulet fermier, bambou et basilic thaï."),
        ("Ramen au Bœuf Chashu", "Bouillon dashi mijoté 12h, nouilles ramen, tranches de bœuf et œuf mollet.")
    ],
    "Street food": [
        ("Fataya Viande Hachée x3", "Chaussons frits farcis à la viande hachée pimentée avec sauce tomate."),
        ("Pastels de Poisson Dakar x5", "Beignets croustillants farcis au poisson avec sauce oignon tomate piquante."),
        ("Beignets Doux Kirikou x6", "Beignets de rue sénégalais chauds saupoudrés de sucre glace."),
        ("Accras de Morue Piquants x5", "Beignets de morue créoles frits et bien relevés."),
        ("Mini Tacos Street Beef", "2 mini tacos souples garnis de bœuf grillé, cilantro et piment rond.")
    ],
    "Fruits": [
        ("Corbeille Découpée Pastèque & Mangue", "Tranches de pastèque sucrée de Sangalkam et mangues Kent mûres."),
        ("Coupe d'Ananas de Casamance", "Dés d'ananas frais extra sucré servis dans sa pirogue d'ananas."),
        ("Salade de Fruits Frais des Tropiques", "Mélange mangue, ananas, papaye, melon et jus de fruit de la passion."),
        ("Assiette de Papaye & Citron Vert", "Papaye douce fraîchement coupée arrosée de jus de citron vert."),
        ("Barquette de Fraises de Niayes", "Fraises locales fraîches sucrées servies avec pointe de chantilly.")
    ]
}

# Update products in DB so every product has a clean name matching its category dish
for cat_name, dishes in official_categories_dishes.items():
    cat_obj = Categorie.objects.filter(nom__icontains=cat_name).first()
    if not cat_obj:
        print(f"Category {cat_name} not found, creating...")
        cat_obj = Categorie.objects.create(nom=cat_name, slug=cat_name.lower().replace(" ", "-"))

    # Re-assign products for this category
    prods = list(Produit.objects.filter(categorie=cat_obj))
    for i, prod in enumerate(prods):
        dish_tuple = dishes[i % len(dishes)]
        prod.nom = dish_tuple[0]
        prod.description = dish_tuple[1]
        prod.save()

print("Category dishes alignment completed!")
