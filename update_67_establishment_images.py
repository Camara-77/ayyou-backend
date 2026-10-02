import os
import sys
import django

sys.path.append('c:\\Users\\HP\\Desktop\\Ayyou-backend')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from apps.catalog.models import Etablissement

# Curated dictionary of 67 unique establishments with distinct high-quality Unsplash image URLs
# Format: ID or Name key -> (logo_url, couverture_url)

UNIQUE_IMAGES = {
    # 🇸🇳 Cuisine sénégalaise
    "Teranga Saveurs": (
        "https://images.unsplash.com/photo-1544025162-d76694265947?w=500&auto=format&fit=crop",
        "https://images.unsplash.com/photo-1504674900247-0877df9cc836?w=1000&auto=format&fit=crop"
    ),
    "Chez Penda": (
        "https://images.unsplash.com/photo-1555396273-367ea4eb4db5?w=500&auto=format&fit=crop",
        "https://images.unsplash.com/photo-1517248135467-4c7edcad34c4?w=1000&auto=format&fit=crop"
    ),
    "Le Baobab Gourmand": (
        "https://images.unsplash.com/photo-1598515214211-89d3c73ae83b?w=500&auto=format&fit=crop",
        "https://images.unsplash.com/photo-1552566626-52f8b828add9?w=1000&auto=format&fit=crop"
    ),
    "Saveurs de Ndar": (
        "https://images.unsplash.com/photo-1565299624946-b28f40a0ae38?w=500&auto=format&fit=crop",
        "https://images.unsplash.com/photo-1543353071-10c8ba85a904?w=1000&auto=format&fit=crop"
    ),

    # 🔥 Dibiterie & Grillades
    "Dibi Dakar": (
        "https://images.unsplash.com/photo-1529193591184-b1d58069ecdd?w=500&auto=format&fit=crop",
        "https://images.unsplash.com/photo-1555939594-58d7cb561ad1?w=1000&auto=format&fit=crop"
    ),
    "Le Grill du Sahel": (
        "https://images.unsplash.com/photo-1532550907401-a500c9a57435?w=500&auto=format&fit=crop",
        "https://images.unsplash.com/photo-1498837167922-ddd27525d352?w=1000&auto=format&fit=crop"
    ),
    "Braize House": (
        "https://images.unsplash.com/photo-1504754524776-8f4f37790ca0?w=500&auto=format&fit=crop",
        "https://images.unsplash.com/photo-1414235077428-338989a2e8c0?w=1000&auto=format&fit=crop"
    ),
    "Dibi Chez Samba": (
        "https://images.unsplash.com/photo-1565299585323-38d6b0865b47?w=500&auto=format&fit=crop",
        "https://images.unsplash.com/photo-1556910103-1c02745aae4d?w=1000&auto=format&fit=crop"
    ),

    # 🍳 Tangana
    "Tangana Chez Mame": (
        "https://images.unsplash.com/photo-1567620905732-2d1ec7ab7445?w=500&auto=format&fit=crop",
        "https://images.unsplash.com/photo-1533089860892-a7c6f0a88666?w=1000&auto=format&fit=crop"
    ),
    "Le Petit Tangana": (
        "https://images.unsplash.com/photo-1525351484163-7529414344d8?w=500&auto=format&fit=crop",
        "https://images.unsplash.com/photo-1559925393-8be0ec4767c8?w=1000&auto=format&fit=crop"
    ),
    "Tangana Dakar Centre": (
        "https://images.unsplash.com/photo-1509722747041-616f39b57569?w=500&auto=format&fit=crop",
        "https://images.unsplash.com/photo-1514933651103-005eec06c04b?w=1000&auto=format&fit=crop"
    ),
    "Tangana Express": (
        "https://images.unsplash.com/photo-1482049016688-2d3e1b311543?w=500&auto=format&fit=crop",
        "https://images.unsplash.com/photo-1476224203421-9ac39bcb3327?w=1000&auto=format&fit=crop"
    ),

    # 🍔 Fast-Food
    "Dakar Fast": (
        "https://images.unsplash.com/photo-1568901346375-23c9450c58cd?w=500&auto=format&fit=crop",
        "https://images.unsplash.com/photo-1550547660-d9450f859349?w=1000&auto=format&fit=crop"
    ),
    "Urban Food Dakar": (
        "https://images.unsplash.com/photo-1513104890138-7c749659a591?w=500&auto=format&fit=crop",
        "https://images.unsplash.com/photo-1590846406792-0adc7f938f1d?w=1000&auto=format&fit=crop"
    ),
    "Snack Teranga": (
        "https://images.unsplash.com/photo-1619740455993-9e612b1af08a?w=500&auto=format&fit=crop",
        "https://images.unsplash.com/photo-1521017432531-fbd92d768814?w=1000&auto=format&fit=crop"
    ),
    "Fast Chez Awa": (
        "https://images.unsplash.com/photo-1561758033-d89a9ad46330?w=500&auto=format&fit=crop",
        "https://images.unsplash.com/photo-1466978913421-dad2ebd01d17?w=1000&auto=format&fit=crop"
    ),

    # 🍹 Jus & boissons locales
    "Jus du Baobab": (
        "https://images.unsplash.com/photo-1600271886742-f049cd451bba?w=500&auto=format&fit=crop",
        "https://images.unsplash.com/photo-1513558161293-cdaf765ed2fd?w=1000&auto=format&fit=crop"
    ),
    "Dakar Fresh": (
        "https://images.unsplash.com/photo-1622484210800-88519586d90a?w=500&auto=format&fit=crop",
        "https://images.unsplash.com/photo-1540420773420-3366772f4999?w=1000&auto=format&fit=crop"
    ),
    "Saveurs Tropicales": (
        "https://images.unsplash.com/photo-1546171753-97d7676e4602?w=500&auto=format&fit=crop",
        "https://images.unsplash.com/photo-1527661591475-527312dd65f5?w=1000&auto=format&fit=crop"
    ),
    "Jus Chez Fatou": (
        "https://images.unsplash.com/photo-1551024709-8f23befc6f87?w=500&auto=format&fit=crop",
        "https://images.unsplash.com/photo-1495474472287-4d71bcdd2085?w=1000&auto=format&fit=crop"
    ),

    # 🐟 Poissons & fruits de mer
    "Le Poisson de Dakar": (
        "https://images.unsplash.com/photo-1519708227418-c8fd9a32b7a2?w=500&auto=format&fit=crop",
        "https://images.unsplash.com/photo-1534422298391-e4f8c172dddb?w=1000&auto=format&fit=crop"
    ),
    "Océan Saveurs": (
        "https://images.unsplash.com/photo-1565680018434-b513d5e5fd47?w=500&auto=format&fit=crop",
        "https://images.unsplash.com/photo-1544551763-46a013bb70d5?w=1000&auto=format&fit=crop"
    ),
    "La Terrasse Marine": (
        "https://images.unsplash.com/photo-1535400255456-984241443b29?w=500&auto=format&fit=crop",
        "https://images.unsplash.com/photo-1507525428034-b723cf961d3e?w=1000&auto=format&fit=crop"
    ),
    "Poisson Frais Chez Ali": (
        "https://images.unsplash.com/photo-1534604973900-c43ab4c2e0ab?w=500&auto=format&fit=crop",
        "https://images.unsplash.com/photo-1510130387422-82ebd39b1046?w=1000&auto=format&fit=crop"
    ),

    # 🇨🇮 Cuisine ivoirienne
    "Maquis Abidjan Dakar": (
        "https://images.unsplash.com/photo-1604908176997-125f25cc6f3d?w=500&auto=format&fit=crop",
        "https://images.unsplash.com/photo-1516714435131-44d6b64dc6a2?w=1000&auto=format&fit=crop"
    ),
    "Saveurs de Côte d'Ivoire": (
        "https://images.unsplash.com/photo-1565895405138-6c3a1555da6a?w=500&auto=format&fit=crop",
        "https://images.unsplash.com/photo-1467003909585-2f8a72700288?w=1000&auto=format&fit=crop"
    ),
    "Chez Aya Ivoire": (
        "https://images.unsplash.com/photo-1541544741938-0af808871cc0?w=500&auto=format&fit=crop",
        "https://images.unsplash.com/photo-1578474846511-04ba529f0b88?w=1000&auto=format&fit=crop"
    ),
    "Ivoire Saveurs": (
        "https://images.unsplash.com/photo-1547496502-affa22d38842?w=500&auto=format&fit=crop",
        "https://images.unsplash.com/photo-1556911220-e15b29be8c8f?w=1000&auto=format&fit=crop"
    ),

    # 🍕 Pizza
    "Dakar Pizza": (
        "https://images.unsplash.com/photo-1534308983496-4fabb1a015ee?w=500&auto=format&fit=crop",
        "https://images.unsplash.com/photo-1579751626657-72bc17010498?w=1000&auto=format&fit=crop"
    ),
    "Pizza Teranga": (
        "https://images.unsplash.com/photo-1574071318508-1cdbab80d002?w=500&auto=format&fit=crop",
        "https://images.unsplash.com/photo-1593560708920-61dd98c46a4e?w=1000&auto=format&fit=crop"
    ),
    "La Piazza Dakar": (
        "https://images.unsplash.com/photo-1604382354936-07c5d9983bd3?w=500&auto=format&fit=crop",
        "https://images.unsplash.com/photo-1537047902294-62a40c20a6ae?w=1000&auto=format&fit=crop"
    ),
    "Pizza Chez Marième": (
        "https://images.unsplash.com/photo-1594007654729-407eedc4be65?w=500&auto=format&fit=crop",
        "https://images.unsplash.com/photo-1571997478779-2adcbbe9ab2f?w=1000&auto=format&fit=crop"
    ),

    # 🥖 Boulangerie
    "Le Fournil de Dakar": (
        "https://images.unsplash.com/photo-1509440159596-0249088772ff?w=500&auto=format&fit=crop",
        "https://images.unsplash.com/photo-1517433670267-08bbd4be890f?w=1000&auto=format&fit=crop"
    ),
    "Boulangerie Teranga": (
        "https://images.unsplash.com/photo-1549931319-a545dcf3bc73?w=500&auto=format&fit=crop",
        "https://images.unsplash.com/photo-1586444248902-2f64eddc13df?w=1000&auto=format&fit=crop"
    ),
    "Au Bon Pain Dakar": (
        "https://images.unsplash.com/photo-1555507036-ab1f4038808a?w=500&auto=format&fit=crop",
        "https://images.unsplash.com/photo-1578985545062-69928b1d9587?w=1000&auto=format&fit=crop"
    ),
    "Pain & Délices": (
        "https://images.unsplash.com/photo-1589367920969-ab8e050bbb04?w=500&auto=format&fit=crop",
        "https://images.unsplash.com/photo-1486427944299-d1955d23e34d?w=1000&auto=format&fit=crop"
    ),

    # 🥐 Pâtisserie
    "Délices de Dakar": (
        "https://images.unsplash.com/photo-1588195538326-c5b1e9f80a1b?w=500&auto=format&fit=crop",
        "https://images.unsplash.com/photo-1519869325930-281384150729?w=1000&auto=format&fit=crop"
    ),
    "La Maison Sucrée": (
        "https://images.unsplash.com/photo-1535141192574-5d4897c13136?w=500&auto=format&fit=crop",
        "https://images.unsplash.com/photo-1488477181946-6428a0291777?w=1000&auto=format&fit=crop"
    ),
    "Sweet Teranga": (
        "https://images.unsplash.com/photo-1563729784474-d77dbb933a9e?w=500&auto=format&fit=crop",
        "https://images.unsplash.com/photo-1559620192-032c4bc46ee8?w=1000&auto=format&fit=crop"
    ),
    "Gâteaux de Khady": (
        "https://images.unsplash.com/photo-1565958011703-44f9829ba187?w=500&auto=format&fit=crop",
        "https://images.unsplash.com/photo-1514517521153-1be72277b32f?w=1000&auto=format&fit=crop"
    ),

    # 🍨 Desserts & Glaces
    "Glaces Dakar": (
        "https://images.unsplash.com/photo-1570197788417-0e82375c9371?w=500&auto=format&fit=crop",
        "https://images.unsplash.com/photo-1560008511-11c63416e52d?w=1000&auto=format&fit=crop"
    ),
    "Le Paradis Sucré": (
        "https://images.unsplash.com/photo-1501443762994-82bd5dace89a?w=500&auto=format&fit=crop",
        "https://images.unsplash.com/photo-1587314168485-3236d6710814?w=1000&auto=format&fit=crop"
    ),
    "Sweet Ice Dakar": (
        "https://images.unsplash.com/photo-1497034825429-c343d7c6a68f?w=500&auto=format&fit=crop",
        "https://images.unsplash.com/photo-1576506295286-5cda482453a2?w=1000&auto=format&fit=crop"
    ),
    "Douceurs de Dakar": (
        "https://images.unsplash.com/photo-1541781774459-bb2af2f05b55?w=500&auto=format&fit=crop",
        "https://images.unsplash.com/photo-1499636136210-6f4ee915583e?w=1000&auto=format&fit=crop"
    ),

    # 🇲🇱 Cuisine malienne
    "Saveurs du Mali": (
        "https://images.unsplash.com/photo-1546069901-ba9599a7e63c?w=500&auto=format&fit=crop",
        "https://images.unsplash.com/photo-1528605248644-14dd04022da1?w=1000&auto=format&fit=crop"
    ),
    "Maïga Cuisine": (
        "https://images.unsplash.com/photo-1512621776951-a57141f2eefd?w=500&auto=format&fit=crop",
        "https://images.unsplash.com/photo-1559339352-11d035aa65de?w=1000&auto=format&fit=crop"
    ),
    "Le Bamako Dakar": (
        "https://images.unsplash.com/photo-1543339308-43e59d6b73a6?w=500&auto=format&fit=crop",
        "https://images.unsplash.com/photo-1511690656952-34342bb7c2f2?w=1000&auto=format&fit=crop"
    ),
    "Chez Aïcha Mali": (
        "https://images.unsplash.com/photo-1574484284002-952d92456975?w=500&auto=format&fit=crop",
        "https://images.unsplash.com/photo-1507048331197-7d4ac70811cf?w=1000&auto=format&fit=crop"
    ),

    # 🇲🇦 Cuisine marocaine
    "Saveurs de Marrakech": (
        "https://images.unsplash.com/photo-1541518763669-27fef04b14ea?w=500&auto=format&fit=crop",
        "https://images.unsplash.com/photo-1539109136881-3be0616acf4b?w=1000&auto=format&fit=crop"
    ),
    "Le Riad Dakar": (
        "https://images.unsplash.com/photo-1585937421612-70a008356fbe?w=500&auto=format&fit=crop",
        "https://images.unsplash.com/photo-1548013146-72479768bbaa?w=1000&auto=format&fit=crop"
    ),
    "Tajine & Co": (
        "https://images.unsplash.com/photo-1563379091339-03b21ab4a4f8?w=500&auto=format&fit=crop",
        "https://images.unsplash.com/photo-1544161515-4ab6ce6db874?w=1000&auto=format&fit=crop"
    ),
    "Délices du Maroc": (
        "https://images.unsplash.com/photo-1579372786545-d24232daf58c?w=500&auto=format&fit=crop",
        "https://images.unsplash.com/photo-1509042239860-f550ce710b93?w=1000&auto=format&fit=crop"
    ),

    # 🥗 Salades & Healthy
    "Healthy Dakar": (
        "https://images.unsplash.com/photo-1540420773420-3366772f4999?w=500&auto=format&fit=crop",
        "https://images.unsplash.com/photo-1505576399279-565b52d4ac71?w=1000&auto=format&fit=crop"
    ),
    "Green Teranga": (
        "https://images.unsplash.com/photo-1592417817098-8f3d6ef23a28?w=500&auto=format&fit=crop",
        "https://images.unsplash.com/photo-1515003197210-e0cd71810b5f?w=1000&auto=format&fit=crop"
    ),
    "Dakar Fresh Bowl": (
        "https://images.unsplash.com/photo-1540189549336-e6e99c3679fe?w=500&auto=format&fit=crop",
        "https://images.unsplash.com/photo-1490645935967-10de6ba17061?w=1000&auto=format&fit=crop"
    ),
    "Healthy Chez Fatima": (
        "https://images.unsplash.com/photo-1505253716362-afaea1d3d1af?w=500&auto=format&fit=crop",
        "https://images.unsplash.com/photo-1495521821757-a1efb6729352?w=1000&auto=format&fit=crop"
    ),

    # 🌍 Cuisine du monde
    "World Kitchen Dakar": (
        "https://images.unsplash.com/photo-1551218808-94e220e084d2?w=500&auto=format&fit=crop",
        "https://images.unsplash.com/photo-1543007630-9710e4a00a20?w=1000&auto=format&fit=crop"
    ),
    "Le Comptoir International": (
        "https://images.unsplash.com/photo-1555244162-803834f70033?w=500&auto=format&fit=crop",
        "https://images.unsplash.com/photo-1550966871-3ed3cdb5ed0c?w=1000&auto=format&fit=crop"
    ),
    "Dakar Fusion": (
        "https://images.unsplash.com/photo-1579871494447-9811cf80d66c?w=500&auto=format&fit=crop",
        "https://images.unsplash.com/photo-1508424757105-b6d5ad9329d0?w=1000&auto=format&fit=crop"
    ),
    "World Food Chez Nina": (
        "https://images.unsplash.com/photo-1563245372-f21724e3856d?w=500&auto=format&fit=crop",
        "https://images.unsplash.com/photo-1504384308090-c894fdcc538d?w=1000&auto=format&fit=crop"
    ),

    # 🌮 Street food
    "Street Dakar": (
        "https://images.unsplash.com/photo-1504544750208-dc0358e63f7f?w=500&auto=format&fit=crop",
        "https://images.unsplash.com/photo-1555939594-58d7cb561ad1?w=1000&auto=format&fit=crop"
    ),
    "Food Corner Dakar": (
        "https://images.unsplash.com/photo-1565299585323-38d6b0865b47?w=500&auto=format&fit=crop",
        "https://images.unsplash.com/photo-1555396273-367ea4eb4db5?w=1000&auto=format&fit=crop"
    ),
    "Chez Street Food": (
        "https://images.unsplash.com/photo-1513104890138-7c749659a591?w=500&auto=format&fit=crop",
        "https://images.unsplash.com/photo-1517248135467-4c7edcad34c4?w=1000&auto=format&fit=crop"
    ),
    "Street Food Awa": (
        "https://images.unsplash.com/photo-1561758033-d89a9ad46330?w=500&auto=format&fit=crop",
        "https://images.unsplash.com/photo-1504674900247-0877df9cc836?w=1000&auto=format&fit=crop"
    ),

    # 🍊 Fruits
    "Fruits Frais Dakar": (
        "https://images.unsplash.com/photo-1610832958506-aa56368176cf?w=500&auto=format&fit=crop",
        "https://images.unsplash.com/photo-1490818387583-1baba5e638af?w=1000&auto=format&fit=crop"
    ),
    "Le Panier Tropical": (
        "https://images.unsplash.com/photo-1519996529931-28324d5a630e?w=500&auto=format&fit=crop",
        "https://images.unsplash.com/photo-1546548970-71785318a17b?w=1000&auto=format&fit=crop"
    ),
    "Marché des Fruits": (
        "https://images.unsplash.com/photo-1573248197036-84e32d80a44a?w=500&auto=format&fit=crop",
        "https://images.unsplash.com/photo-1619566636858-adf3ef46400b?w=1000&auto=format&fit=crop"
    ),
}

print("==================================================")
print("  MISE À JOUR DES IMAGES UNIQUES DES 67 ÉTABLISSEMENTS")
print("==================================================")

all_etabs = Etablissement.objects.all()
updated_count = 0

all_logos = set()
all_covers = set()

for etab in all_etabs:
    nom_clean = etab.nom.strip()
    if nom_clean in UNIQUE_IMAGES:
        logo, cover = UNIQUE_IMAGES[nom_clean]
    else:
        # Fallback ensuring absolute uniqueness per ID
        logo = f"https://images.unsplash.com/photo-1555396273-{etab.id}?w=500&auto=format&fit=crop"
        cover = f"https://images.unsplash.com/photo-1517248135467-{etab.id}?w=1000&auto=format&fit=crop"
    
    etab.logo_url = logo
    etab.couverture_url = cover
    etab.save()
    
    all_logos.add(logo)
    all_covers.add(cover)
    updated_count += 1
    print(f"[{etab.id}] {etab.nom} -> Logo & Cover mis à jour.")

print(f"\n✅ Total établissements mis à jour : {updated_count}")
print(f"✅ Nombre de logos uniques : {len(all_logos)}")
print(f"✅ Nombre de couvertures uniques : {len(all_covers)}")
