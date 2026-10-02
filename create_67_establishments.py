import os
import sys
import django
import random

sys.path.append('c:\\Users\\HP\\Desktop\\Ayyou-backend')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from apps.users.models import Utilisateur, Role, UtilisateurRole
from apps.catalog.models import Categorie, Etablissement

print("==================================================")
print("  CRÉATION DES 67 ÉTABLISSEMENTS DE TEST AYYOU")
print("==================================================")

# Roles mapping
roles_dict = {}
for r_name in [Role.RESTAURANT, Role.VENDEUR]:
    r_obj, _ = Role.objects.get_or_create(nom=r_name, defaults={'description': f'Rôle {r_name}'})
    roles_dict[r_name] = r_obj

def create_owner_account(email, tel, prenom, nom, role_name, password="Password123!"):
    user = Utilisateur.objects.filter(email=email).first()
    if not user:
        user = Utilisateur.objects.filter(numero_telephone=tel).first()
    if not user:
        user = Utilisateur.objects.create_user(
            email=email,
            numero_telephone=tel,
            password=password,
            prenom=prenom,
            nom=nom,
            est_actif=True,
            est_verifie=True
        )
    else:
        user.set_password(password)
        user.save()

    r_obj = roles_dict[role_name]
    UtilisateurRole.objects.get_or_create(utilisateur=user, role=r_obj)
    return user, password

establishments_data = [
    # 🇸🇳 Cuisine sénégalaise
    ("Teranga Saveurs", "RESTAURANT", "Cuisine sénégalaise • Poissons & fruits de mer", "Cuisine sénégalaise", "Plateau, Dakar"),
    ("Chez Penda", "RESTAURANT", "Cuisine sénégalaise • Tangana • Street food", "Cuisine sénégalaise", "Médina, Dakar"),
    ("Le Baobab Gourmand", "RESTAURANT", "Cuisine sénégalaise • Dibiterie & Grillades", "Cuisine sénégalaise", "Almadies, Dakar"),
    ("Saveurs de Ndar", "VENDEUR", "Cuisine sénégalaise • Poissons & fruits de mer", "Cuisine sénégalaise", "Point E, Dakar"),

    # 🔥 Dibiterie & Grillades
    ("Dibi Dakar", "RESTAURANT", "Dibiterie & Grillades • Street food", "Dibiterie & Grillades", "Grand Yoff, Dakar"),
    ("Le Grill du Sahel", "RESTAURANT", "Dibiterie & Grillades • Cuisine sénégalaise", "Dibiterie & Grillades", "Mermoz, Dakar"),
    ("Braize House", "RESTAURANT", "Dibiterie & Grillades • Poissons & fruits de mer • Street food", "Dibiterie & Grillades", "Almadies, Dakar"),
    ("Dibi Chez Samba", "VENDEUR", "Dibiterie & Grillades • Street food", "Dibiterie & Grillades", "Parcelles Assainies, Dakar"),

    # 🌯 Tangana
    ("Tangana Chez Mame", "RESTAURANT", "Tangana • Cuisine sénégalaise • Street food", "Tangana", "Médina, Dakar"),
    ("Le Petit Tangana", "RESTAURANT", "Tangana • Street food • Fast-Food", "Tangana", "Fann Hock, Dakar"),
    ("Tangana Dakar Centre", "RESTAURANT", "Tangana • Cuisine sénégalaise", "Tangana", "Plateau, Dakar"),
    ("Tangana Express", "VENDEUR", "Tangana • Street food", "Tangana", "HLM 5, Dakar"),

    # 🍔 Fast-Food
    ("Dakar Fast", "RESTAURANT", "Fast-Food • Street food", "Fast-Food", "Sacré-Cœur 3, Dakar"),
    ("Urban Food Dakar", "RESTAURANT", "Fast-Food • Pizza • Street food", "Fast-Food", "Mermoz, Dakar"),
    ("Snack Teranga", "RESTAURANT", "Fast-Food • Cuisine sénégalaise • Street food", "Fast-Food", "Point E, Dakar"),
    ("Fast Chez Awa", "VENDEUR", "Fast-Food • Street food", "Fast-Food", "Ouakam, Dakar"),

    # 🥤 Jus & Boissons locales
    ("Jus du Baobab", "RESTAURANT", "Jus & boissons locales • Fruits", "Jus & Boissons locales", "Hann Maristes, Dakar"),
    ("Dakar Fresh", "RESTAURANT", "Jus & boissons locales • Fruits • Salades & Healthy", "Jus & Boissons locales", "Virage, Almadies"),
    ("Saveurs Tropicales", "RESTAURANT", "Jus & boissons locales • Fruits", "Jus & Boissons locales", "Fann Résidence, Dakar"),
    ("Jus Chez Fatou", "VENDEUR", "Jus & boissons locales • Fruits", "Jus & Boissons locales", "Cité Keur Gorgui, Dakar"),

    # 🐟 Poissons & Fruits de mer
    ("Le Poisson de Dakar", "RESTAURANT", "Poissons & fruits de mer • Cuisine sénégalaise", "Poissons & Fruits de mer", "Ngor, Dakar"),
    ("Océan Saveurs", "RESTAURANT", "Poissons & fruits de mer • Cuisine du monde", "Poissons & Fruits de mer", "Corniche Est, Dakar"),
    ("La Terrasse Marine", "RESTAURANT", "Poissons & fruits de mer • Grillades", "Poissons & Fruits de mer", "Yoff Beach, Dakar"),
    ("Poisson Frais Chez Ali", "VENDEUR", "Poissons & fruits de mer • Grillades", "Poissons & Fruits de mer", "Soumbédioune, Dakar"),

    # 🇨🇮 Cuisine ivoirienne
    ("Maquis Abidjan Dakar", "RESTAURANT", "Cuisine ivoirienne • Grillades • Street food", "Cuisine ivoirienne", "Grand Yoff, Dakar"),
    ("Saveurs de Côte d'Ivoire", "RESTAURANT", "Cuisine ivoirienne • Cuisine du monde", "Cuisine ivoirienne", "Sacre-Coeur 2, Dakar"),
    ("Chez Aya Ivoire", "RESTAURANT", "Cuisine ivoirienne • Fast-Food • Street food", "Cuisine ivoirienne", "Liberté 6, Dakar"),
    ("Ivoire Saveurs", "VENDEUR", "Cuisine ivoirienne • Grillades", "Cuisine ivoirienne", "Cité Fadia, Dakar"),

    # 🍕 Pizza
    ("Dakar Pizza", "RESTAURANT", "Pizza • Fast-Food", "Pizza", "Fann Résidence, Dakar"),
    ("Pizza Teranga", "RESTAURANT", "Pizza • Cuisine sénégalaise • Fast-Food", "Pizza", "Cheikh Anta Diop, Dakar"),
    ("La Piazza Dakar", "RESTAURANT", "Pizza • Cuisine du monde", "Pizza", "Almadies, Dakar"),
    ("Pizza Chez Marième", "VENDEUR", "Pizza • Fast-Food", "Pizza", "Mermoz, Dakar"),

    # 🥐 Boulangerie
    ("Le Fournil de Dakar", "RESTAURANT", "Boulangerie • Pâtisserie • Petit-déjeuner", "Boulangerie", "Plateau, Dakar"),
    ("Boulangerie Teranga", "RESTAURANT", "Boulangerie • Cuisine sénégalaise", "Boulangerie", "Liberté 6, Dakar"),
    ("Au Bon Pain Dakar", "RESTAURANT", "Boulangerie • Pâtisserie • Desserts", "Boulangerie", "Fann Hock, Dakar"),
    ("Pain & Délices", "VENDEUR", "Boulangerie • Petit-déjeuner", "Boulangerie", "Sacré-Cœur 1, Dakar"),

    # 🍰 Pâtisserie
    ("Délices de Dakar", "RESTAURANT", "Pâtisserie • Desserts & Glaces", "Pâtisserie", "Pasteur, Dakar"),
    ("La Maison Sucrée", "RESTAURANT", "Pâtisserie • Boulangerie", "Pâtisserie", "Point E, Dakar"),
    ("Sweet Teranga", "RESTAURANT", "Pâtisserie • Desserts & Glaces • Fruits", "Pâtisserie", "Almadies, Dakar"),
    ("Gâteaux de Khady", "VENDEUR", "Pâtisserie • Desserts & Glaces", "Pâtisserie", "Keur Gorgui, Dakar"),

    # 🍦 Desserts & Glaces
    ("Glaces Dakar", "RESTAURANT", "Desserts & Glaces • Jus & boissons", "Desserts & Glaces", "Avenue Ponty, Dakar"),
    ("Le Paradis Sucré", "RESTAURANT", "Desserts & Glaces • Pâtisserie", "Desserts & Glaces", "Almadies, Dakar"),
    ("Sweet Ice Dakar", "RESTAURANT", "Desserts & Glaces • Fruits", "Desserts & Glaces", "Mermoz, Dakar"),
    ("Douceurs de Dakar", "VENDEUR", "Desserts & Glaces • Pâtisserie", "Desserts & Glaces", "Point E, Dakar"),

    # 🇲🇱 Cuisine malienne
    ("Saveurs du Mali", "RESTAURANT", "Cuisine malienne • Cuisine du monde", "Cuisine malienne", "Médina, Dakar"),
    ("Maïga Cuisine", "RESTAURANT", "Cuisine malienne • Street food", "Cuisine malienne", "Grand Yoff, Dakar"),
    ("Le Bamako Dakar", "RESTAURANT", "Cuisine malienne • Grillades", "Cuisine malienne", "HLM 3, Dakar"),
    ("Chez Aïcha Mali", "VENDEUR", "Cuisine malienne • Street food", "Cuisine malienne", "Colobane, Dakar"),

    # 🇲🇦 Cuisine marocaine
    ("Saveurs de Marrakech", "RESTAURANT", "Cuisine marocaine • Cuisine du monde", "Cuisine marocaine", "Almadies, Dakar"),
    ("Le Riad Dakar", "RESTAURANT", "Cuisine marocaine • Pâtisserie", "Cuisine marocaine", "Fann Résidence, Dakar"),
    ("Tajine & Co", "RESTAURANT", "Cuisine marocaine • Street food", "Cuisine marocaine", "Plateau, Dakar"),
    ("Délices du Maroc", "VENDEUR", "Cuisine marocaine • Pâtisserie", "Cuisine marocaine", "Mermoz, Dakar"),

    # 🥗 Salades & Healthy
    ("Healthy Dakar", "RESTAURANT", "Salades & Healthy • Fruits • Jus", "Salades & Healthy", "Point E, Dakar"),
    ("Green Teranga", "RESTAURANT", "Salades & Healthy • Cuisine sénégalaise", "Salades & Healthy", "Fann Hock, Dakar"),
    ("Dakar Fresh Bowl", "RESTAURANT", "Salades & Healthy • Fruits • Cuisine du monde", "Salades & Healthy", "Almadies, Dakar"),
    ("Healthy Chez Fatima", "VENDEUR", "Salades & Healthy • Fruits", "Salades & Healthy", "Mermoz, Dakar"),

    # 🍜 Cuisine du monde
    ("World Kitchen Dakar", "RESTAURANT", "Cuisine du monde • Fast-Food", "Cuisine du monde", "Almadies, Dakar"),
    ("Le Comptoir International", "RESTAURANT", "Cuisine du monde • Pizza • Pâtisserie", "Cuisine du monde", "Plateau, Dakar"),
    ("Dakar Fusion", "RESTAURANT", "Cuisine du monde • Poissons & fruits de mer", "Cuisine du monde", "Ngor, Dakar"),
    ("World Food Chez Nina", "VENDEUR", "Cuisine du monde • Street food", "Cuisine du monde", "Point E, Dakar"),

    # 🍢 Street food
    ("Street Dakar", "RESTAURANT", "Street food • Fast-Food • Tangana", "Street food", "Médina, Dakar"),
    ("Food Corner Dakar", "RESTAURANT", "Street food • Pizza • Fast-Food", "Street food", "Grand Yoff, Dakar"),
    ("Chez Street Food", "RESTAURANT", "Street food • Grillades • Tangana", "Street food", "Parcelles Assainies, Dakar"),
    ("Street Food Awa", "VENDEUR", "Street food • Cuisine sénégalaise", "Street food", "HLM 5, Dakar"),

    # 🍉 Fruits (3 Vendeurs uniquement)
    ("Fruits Frais Dakar", "VENDEUR", "Fruits • Jus & boissons locales", "Fruits", "Mermoz, Dakar"),
    ("Le Panier Tropical", "VENDEUR", "Fruits • Jus & boissons locales • Healthy", "Fruits", "Almadies, Dakar"),
    ("Marché des Fruits", "VENDEUR", "Fruits • Healthy", "Fruits", "Point E, Dakar"),
]

all_credentials = []

for idx, (nom, type_etab, specs, main_cat_name, location) in enumerate(establishments_data, start=1):
    slug_name = nom.lower().replace(" ", "_").replace("'", "").replace("•", "").replace("&", "et")
    email = f"owner.{slug_name}{idx}@ayyou.sn"
    tel = f"+22177{3000000 + idx}"
    
    role_name = Role.RESTAURANT if type_etab == "RESTAURANT" else Role.VENDEUR
    owner_user, pwd = create_owner_account(email, tel, "Gérant", nom, role_name)

    cat_obj = Categorie.objects.filter(nom__icontains=main_cat_name).first()

    etab = Etablissement.objects.create(
        nom=nom,
        type_etablissement=type_etab,
        proprietaire=owner_user,
        logo_url=cat_obj.image_url if cat_obj and cat_obj.image_url else 'https://images.unsplash.com/photo-1555396273-367ea4eb4db5?w=500',
        couverture_url=cat_obj.image_url if cat_obj and cat_obj.image_url else 'https://images.unsplash.com/photo-1517248135467-4c7edcad34c4?w=500',
        slogan=f"Spécialité : {specs}",
        description=f"Bienvenue chez {nom}, votre étape gourmande pour : {specs}.",
        adresse=location,
        telephone=tel,
        specialite=specs,
        statut=Etablissement.STATUT_OUVERT,
        statut_verification=Etablissement.STATUT_VALIDE,
        est_verifie=True,
        note_moyenne=round(random.uniform(4.4, 4.9), 2),
        nombre_avis=random.randint(20, 150)
    )

    all_credentials.append({
        "id": etab.id,
        "type": type_etab,
        "nom": nom,
        "email": email,
        "tel": tel,
        "pwd": pwd,
        "specialite": specs,
        "adresse": location
    })

print(f"Total Établissements créés: {len(all_credentials)}")

# Write full credentials table to artifact
artifact_path = r"C:\Users\HP\.gemini\antigravity\brain\1f2cd0a4-e39b-4ef8-b924-e7e0bc2d34a3\credentials_67_etablissements.md"
with open(artifact_path, "w", encoding="utf-8") as f:
    f.write("# 🔑 Identifiants de Connexion des 67 Établissements AYYOU\n\n")
    f.write("> [!IMPORTANT]\n")
    f.write("> Tous les 67 comptes ci-dessous ont été enregistrés et activés avec le rôle correspondant (`RESTAURANT` ou `VENDEUR`). Le mot de passe par défaut est `Password123!`.\n\n")

    f.write("## 🍽️ Restaurants (47 Établissements Physique)\n\n")
    f.write("| ID | Nom de l'Établissement | Email de Connexion | Téléphone | Mot de Passe | Spécialités Multi-Catégories | Adresse |\n")
    f.write("| :--- | :--- | :--- | :--- | :--- | :--- | :--- |\n")
    for c in all_credentials:
        if c["type"] == "RESTAURANT":
            f.write(f"| {c['id']} | **{c['nom']}** | `{c['email']}` | `{c['tel']}` | `{c['pwd']}` | {c['specialite']} | {c['adresse']} |\n")

    f.write("\n\n## 🏠 Vendeurs à Domicile & Artisans (20 Établissements)\n\n")
    f.write("| ID | Nom du Vendeur | Email de Connexion | Téléphone | Mot de Passe | Spécialités Multi-Catégories | Adresse |\n")
    f.write("| :--- | :--- | :--- | :--- | :--- | :--- | :--- |\n")
    for c in all_credentials:
        if c["type"] == "VENDEUR":
            f.write(f"| {c['id']} | **{c['nom']}** | `{c['email']}` | `{c['tel']}` | `{c['pwd']}` | {c['specialite']} | {c['adresse']} |\n")

print(f"Rapport d'identifiants écrit sur : {artifact_path}")
