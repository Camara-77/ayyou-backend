import json
from rest_framework.test import APIClient
from apps.orders.models import RepasPlanifie
from apps.catalog.models import Produit, Etablissement, Categorie
from django.contrib.auth import get_user_model

Utilisateur = get_user_model()

print('==================================================')
print('AUDIT & VALIDATION FONCTIONNELLE RÉELLE PLANIFICATION')
print('==================================================')

# 1. Verification des Categories BDD
cats = list(Categorie.objects.all())
print(f'[TEST 2 CATÉGORIES BDD] Total catégories réelles en BDD: {len(cats)}')
for c in cats[:5]:
    print(f' - ID: {c.id} | Nom: {c.nom}')

# 2. Recherche d un Produit reel en BDD
dibi_prod = Produit.objects.filter(nom__icontains='Dibi').first()
if not dibi_prod:
    dibi_prod = Produit.objects.first()

print(f'[TEST 3 PRODUIT RÉEL] ID: {dibi_prod.id} | Nom: {dibi_prod.nom} | Prix: {dibi_prod.prix_base} | Resto: {dibi_prod.etablissement.nom} (ID:{dibi_prod.etablissement.id})')

# 3. Restos associes
restos = list(Etablissement.objects.filter(produits=dibi_prod))
if not restos:
    restos = [dibi_prod.etablissement]
print(f'[TEST 5 ÉTABLISSEMENTS] Total disponibles pour {dibi_prod.nom}: {len(restos)}')
for r in restos[:3]:
    print(f' - ID: {r.id} | Nom: {r.nom} | Adresse: {r.adresse}')

# Setup Clients Authentifies
user_a = Utilisateur.objects.get(email='pro.owner@ayyou.sn')
user_b = Utilisateur.objects.get(email='restaurant.test@ayyou.test')

client_a = APIClient()
client_a.force_authenticate(user=user_a)

client_b = APIClient()
client_b.force_authenticate(user=user_b)

# TEST 9: POST /api/orders/planning/ - Creation reelle
payload = {
    'produit': dibi_prod.id,
    'etablissement': dibi_prod.etablissement.id,
    'date_planifiee': '2026-10-15',
    'creneau': 'MIDI',
    'prix_total': str(dibi_prod.prix_base * 2),
    'quantite': 2,
    'instructions': 'Moins de sel'
}

res_post = client_a.post('/api/orders/planning/', payload, format='json')
print(f'[TEST 9 POST API] Code HTTP: {res_post.status_code}')
print(f'[TEST 9 RÉPONSE] {json.dumps(res_post.data, indent=2, ensure_ascii=False)}')
assert res_post.status_code == 201

created_id = res_post.data['id']
print(f'[TEST 9 CREATED ID] RepasPlanifie ID: {created_id}')

# TEST 10: VERIFICATION POSTGRESQL IMMÉDIATE
meal_db = RepasPlanifie.objects.get(id=created_id)
print(f'[TEST 10 BDD POSTGRESQL] ID:{meal_db.id} | User:{meal_db.utilisateur.email} | Produit:{meal_db.produit.nom} | Resto:{meal_db.etablissement.nom} | Date:{meal_db.date_planifiee} | Creneau:{meal_db.creneau} | Prix:{meal_db.prix_total} | Qte:{meal_db.quantite} | Statut:{meal_db.statut}')

assert meal_db.id == created_id
assert meal_db.produit.id == dibi_prod.id
assert str(meal_db.date_planifiee) == '2026-10-15'
assert meal_db.creneau == 'MIDI'
assert meal_db.quantite == 2

# TEST 11: REFRESH / LISTING API
res_list = client_a.get('/api/orders/planning/')
ids_in_list = [r['id'] for r in res_list.data.get('repas', [])]
assert created_id in ids_in_list
print(f'[TEST 11 REFRESH API] Repas ID {created_id} présent dans la liste GET Mon Planning : {created_id in ids_in_list}')

# TEST 12: MODIFICATION IN-SITU (PATCH /api/orders/planning/{id}/)
print(f'[TEST 12 MODIFICATION - AVANT] ID: {meal_db.id} | Date: {meal_db.date_planifiee} | Creneau: {meal_db.creneau}')
patch_payload = {
    'date_planifiee': '2026-10-16',
    'creneau': 'SOIR'
}
res_patch = client_a.patch(f'/api/orders/planning/{created_id}/', patch_payload, format='json')
print(f'[TEST 12 PATCH API] Code HTTP: {res_patch.status_code}')
assert res_patch.status_code == 200

meal_db.refresh_from_db()
print(f'[TEST 12 MODIFICATION - APRÈS] ID: {meal_db.id} | Date: {meal_db.date_planifiee} | Creneau: {meal_db.creneau}')
assert meal_db.id == created_id
assert str(meal_db.date_planifiee) == '2026-10-16'
assert meal_db.creneau == 'SOIR'
print('[PASS TEST 12] MÊME ID CONSERVÉ EN BDD APRES PATCH!')

# TEST 13: SÉCURITÉ USER B
res_sec_get = client_b.get(f'/api/orders/planning/{created_id}/')
res_sec_patch = client_b.patch(f'/api/orders/planning/{created_id}/', {'creneau': 'MATIN'}, format='json')
res_sec_del = client_b.delete(f'/api/orders/planning/{created_id}/')
print(f'[TEST 13 SÉCURITÉ USER B] GET:{res_sec_get.status_code} | PATCH:{res_sec_patch.status_code} | DELETE:{res_sec_del.status_code}')
assert res_sec_get.status_code == 404
assert res_sec_patch.status_code == 404
assert res_sec_del.status_code == 404

# TEST 14: ERREURS API (Donnees invalides)
res_err1 = client_a.post('/api/orders/planning/', {'produit': 999999, 'etablissement': dibi_prod.etablissement.id, 'date_planifiee': '2026-10-15', 'creneau': 'MIDI'}, format='json')
res_err2 = client_a.post('/api/orders/planning/', {'produit': dibi_prod.id, 'etablissement': dibi_prod.etablissement.id, 'date_planifiee': 'invalid-date', 'creneau': 'MIDI'}, format='json')
print(f'[TEST 14 ERREURS API] Produit Inexistant:{res_err1.status_code} | Date Invalide:{res_err2.status_code}')
assert res_err1.status_code == 400
assert res_err2.status_code == 400

# Cleaning up test object
meal_db.delete()
print('[PASS] Nettoyage de l\'enregistrement de test temporaire effectué!')
