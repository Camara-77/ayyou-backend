import os
import sys
import json
import django
from decimal import Decimal

# Setup Django Environment
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.base')
django.setup()

from django.conf import settings
if 'testserver' not in settings.ALLOWED_HOSTS:
    settings.ALLOWED_HOSTS.append('testserver')

from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from apps.catalog.models import Categorie, Produit, Etablissement
from apps.orders.models import Commande, SousCommande, LigneCommande
from apps.payments.models import Paiement, Facture
from apps.payments.paytech_service import PayTechService
from apps.payments.services import PaymentService

Utilisateur = get_user_model()


def run_paytech_e2e_tests():
    print("=" * 80)
    print("EXECUTION DES TESTS PAYTECH PHASE 1 -- ENCAISSEMENT & INTEGRATION E2E")
    print("=" * 80)

    results = {
        'creation_pending': False,
        'montant_serveur': False,
        'reference_unique': False,
        'paytech_api_real_call': False,
        'paytech_api_error_detail': '',
        'ipn_success': False,
        'ipn_failure': False,
        'ipn_cancellation': False,
        'ipn_duplicate_idempotency': False,
        'mauvais_montant_ou_ref': False,
        'payment_already_paid': False,
        'missing_keys_protection': False,
        'e2e_full_flow': False,
    }

    client = APIClient()

    # 1. Préparation des données de test
    user, _ = Utilisateur.objects.get_or_create(
        email='client_paytech@ayyou.com',
        defaults={
            'numero_telephone': '+221770001122',
            'prenom': 'Moussa',
            'nom': 'Sall',
            'mode_actif': Utilisateur.MODE_CLIENT,
            'est_actif': True
        }
    )
    user.set_password('password123')
    user.save()
    client.force_authenticate(user=user)

    owner, _ = Utilisateur.objects.get_or_create(
        email='owner_paytech@ayyou.com',
        defaults={'numero_telephone': '+221779998877', 'prenom': 'Owner', 'nom': 'Resto', 'mode_actif': Utilisateur.MODE_CLIENT}
    )

    etablissement, _ = Etablissement.objects.get_or_create(
        proprietaire=owner,
        defaults={'nom': 'Le Teranga Resto', 'adresse': 'Plateau, Dakar', 'type_etablissement': 'RESTAURANT'}
    )

    categorie, _ = Categorie.objects.get_or_create(nom='Plats Principaux')
    produit, _ = Produit.objects.get_or_create(
        nom='Thieboudienne Penda Mbaye',
        etablissement=etablissement,
        defaults={'prix_base': Decimal('3500.00'), 'categorie': categorie, 'est_disponible': True, 'image_url': 'http://example.com/thieb.jpg'}
    )


    # 2. Création d'une commande
    commande = Commande.objects.create(
        utilisateur=user,
        statut=Commande.STATUT_EN_ATTENTE_PAIEMENT,
        sous_total=Decimal('7000.00'),
        frais_livraison=Decimal('1500.00'), # Livreur net souhaité: 1500 FCFA
        total=Decimal('8500.00'),
        adresse_livraison='Résidence Teranga, Plateau, Dakar',
        nom_destinataire='Moussa Sall',
        telephone_destinataire='+221770001122'
    )
    sc = SousCommande.objects.create(
        commande=commande,
        etablissement=etablissement,
        statut=Commande.STATUT_EN_ATTENTE_PAIEMENT,
        sous_total=Decimal('7000.00')
    )
    LigneCommande.objects.create(
        sous_commande=sc,
        produit=produit,
        nom_produit_snapshot=produit.nom,
        quantite=2,
        prix_unitaire=Decimal('3500.00'),
        total_ligne=Decimal('7000.00')
    )

    print(f"\n[1/13] Commande de test #{commande.id} creee. Sous-total: {commande.sous_total} FCFA, Frais livreur net: {commande.frais_livraison} FCFA")

    # TEST : Calcul serveur du montant avec frais PayTech
    calculs = PayTechService.calculer_montant_total_serveur(commande)
    # 1500 / (1 - 0.015) = 1523 FCFA brut -> Total = 7000 + 1523 = 8523 FCFA
    print(f"       Calculs Serveur PayTech: Plats={calculs['sous_total_plats']} FCFA | Livreur Net={calculs['frais_livreur_net']} FCFA | Livraison Brut={calculs['frais_livraison_brut']} FCFA | Total Client={calculs['montant_total']} FCFA")
    if calculs['montant_total'] == Decimal('8523.00'):
        results['montant_serveur'] = True
        print("       [OK] Calcul du montant total avec frais de livraison brut serveur valide.")
    else:
        print(f"       [FAIL] Calcul serveur errone: {calculs['montant_total']}")

    # TEST : Endpoint Initiate PayTech
    token = ''
    paiement = None
    init_res = client.post('/api/payments/paytech/initiate/', {
        'commande_id': commande.id,
        'methode': 'WAVE'
    }, format='json')


    print(f"\n[2/13] Endpoint Initiate PayTech (POST /api/payments/paytech/initiate/): HTTP {init_res.status_code}")
    if init_res.status_code == 201:
        data = init_res.data
        paiement_id = data.get('payment_id')
        ref = data.get('reference')
        token = data.get('token')
        redirect_url = data.get('redirect_url')

        print(f"       Payment ID: {paiement_id} | Reference: {ref} | Token: {token}")
        print(f"       Redirect URL: {redirect_url}")

        paiement = Paiement.objects.get(pk=paiement_id)
        if paiement.statut == Paiement.STATUT_INITIE:
            results['creation_pending'] = True
            print("       [OK] Paiement cree en etat INITIE (PENDING).")

        if ref and ref.startswith('PAY-'):
            results['reference_unique'] = True
            print("       [OK] Reference unique conforme megeneree.")

        if redirect_url and 'paytech.sn' in redirect_url:
            results['paytech_api_real_call'] = True
            print("       [OK] Appel API PayTech TEST reussi avec obtention d'une redirect_url PayTech reelle.")
        else:
            results['paytech_api_error_detail'] = f"Reponse sans URL valide: {data}"
            print(f"       [PARTIAL] URL de redirection PayTech: {redirect_url}")
    else:
        print(f"       [FAIL] POST initiate a echoue: {init_res.data}")
        results['paytech_api_error_detail'] = str(init_res.data)

    # TEST : Protection absence de clés
    print("\n[3/13] Test de protection en cas d'absence de cles API...")
    original_key = getattr(settings, 'PAYTECH_API_KEY', '')
    settings.PAYTECH_API_KEY = ''
    fail_res = PayTechService.create_payment(Paiement(id=999, reference='TEST-NOKEY'), commande)
    if not fail_res['success'] and fail_res['code'] == 'MISSING_KEYS':
        results['missing_keys_protection'] = True
        print("       [OK] Erreur propre retournee en cas d'absence de cle API PayTech.")
    settings.PAYTECH_API_KEY = original_key

    # TEST : Rejet IPN avec signature ou référence invalide
    print("\n[4/13] Test IPN avec reference invalide...")
    paiement = Paiement.objects.filter(commande=commande).first()
    ipn_bad_ref = client.post('/api/payments/paytech/ipn/', {
        'token': token or 'dummy_token',
        'ref_command': 'INVALID-REF-9999',
        'type_event': 'sale_complete',
        'custom_field': json.dumps({'paiement_id': paiement.id if paiement else 0})
    }, format='json')
    if ipn_bad_ref.status_code == 400:
        results['mauvais_montant_ou_ref'] = True
        print("       [OK] IPN avec reference invalide me-rejete avec HTTP 400.")

    # TEST : IPN Succès (confirmation du paiement)
    print("\n[5/13] Test IPN Succes (Webhook Serveur a Serveur)...")
    ipn_ok = client.post('/api/payments/paytech/ipn/', {
        'token': token or paiement.transaction_externe,
        'ref_command': paiement.reference,
        'type_event': 'sale_complete',
        'custom_field': json.dumps({'paiement_id': paiement.id, 'commande_id': commande.id})
    }, format='json')

    print(f"       IPN Success Response: HTTP {ipn_ok.status_code} -> {ipn_ok.data}")
    paiement.refresh_from_db()
    commande.refresh_from_db()

    if ipn_ok.status_code == 200 and paiement.statut == Paiement.STATUT_PAYE:
        results['ipn_success'] = True
        print(f"       [OK] Paiement marque PAYE et Commande #{commande.id} statut = {commande.statut}")

    # TEST : IDEMPOTENCE IPN Dupliqué
    print("\n[6/13] Test d'IDEMPOTENCE IPN (Envoi d'une notification dupliquee)...")
    ipn_dup = client.post('/api/payments/paytech/ipn/', {
        'token': token or paiement.transaction_externe,
        'ref_command': paiement.reference,
        'type_event': 'sale_complete',
        'custom_field': json.dumps({'paiement_id': paiement.id, 'commande_id': commande.id})
    }, format='json')

    if ipn_dup.status_code == 200 and ipn_dup.data.get('status') == 'already_confirmed':
        results['ipn_duplicate_idempotency'] = True
        print("       [OK] IPN duplique traite de maniere idempotente (HTTP 200 status='already_confirmed').")

    # TEST : Paiement déjà payé ne peut plus être modifié
    print("\n[7/13] Test de protection d'un paiement deja PAID...")
    try:
        PaymentService.echouer_paiement(paiement, "Test motif")
        print("       [FAIL] Transition interdite autorisee.")
    except Exception as e:
        results['payment_already_paid'] = True
        print(f"       [OK] Protection validee ({e}).")

    # TEST : IPN Échec & Annulation sur un second paiement de test
    print("\n[8/13] Test IPN Annulation et Echec sur une nouvelle commande...")
    cmd2 = Commande.objects.create(
        utilisateur=user, statut=Commande.STATUT_EN_ATTENTE_PAIEMENT,
        sous_total=Decimal('5000.00'), frais_livraison=Decimal('1000.00'), total=Decimal('6000.00')
    )
    p2 = PaymentService.initier_paiement(cmd2, 'WAVE')

    ipn_cancel = client.post('/api/payments/paytech/ipn/', {
        'token': 'TOKEN_CANCEL_TEST',
        'ref_command': p2.reference,
        'type_event': 'sale_canceled',
        'custom_field': json.dumps({'paiement_id': p2.id})
    }, format='json')
    p2.refresh_from_db()
    if ipn_cancel.status_code == 200 and p2.statut == Paiement.STATUT_ANNULE:
        results['ipn_cancellation'] = True
        print("       [OK] IPN d'annulation traite avec succes.")

    cmd3 = Commande.objects.create(
        utilisateur=user, statut=Commande.STATUT_EN_ATTENTE_PAIEMENT,
        sous_total=Decimal('4000.00'), frais_livraison=Decimal('1000.00'), total=Decimal('5000.00')
    )
    p3 = PaymentService.initier_paiement(cmd3, 'ORANGE_MONEY')
    ipn_fail = client.post('/api/payments/paytech/ipn/', {
        'token': 'TOKEN_FAIL_TEST',
        'ref_command': p3.reference,
        'type_event': 'sale_failed',
        'custom_field': json.dumps({'paiement_id': p3.id})
    }, format='json')
    p3.refresh_from_db()
    if ipn_fail.status_code == 200 and p3.statut == Paiement.STATUT_ECHOUE:
        results['ipn_failure'] = True
        print("       [OK] IPN d'echec traite avec succes.")

    # TEST : Cycle de vie E2E complet Restaurant (Sans Payouts)
    print("\n[9/13] Test du cycle de vie Restaurant post-paiement...")
    sc1 = commande.sous_commandes.first()
    sc1.statut = Commande.STATUT_EN_PREPARATION
    sc1.save()
    print(f"       Sous-commande #{sc1.id} passee a EN_PREPARATION")

    sc1.statut = Commande.STATUT_PRETE
    sc1.save()
    print(f"       Sous-commande #{sc1.id} passee a PRETE")

    if sc1.statut == Commande.STATUT_PRETE and hasattr(commande, 'livraison'):
        results['e2e_full_flow'] = True
        print(f"       [OK] Parcours E2E complet valide : Paiement PayTech -> Commande PAYEE -> Livraison creee (ID {commande.livraison.id}) -> Sous-commande PRETE.")

    print("\n" + "=" * 80)
    print("RESULTAT RECAPITULATIF DES TESTS PAYTECH PHASE 1")
    print("=" * 80)
    for k, v in results.items():
        if k == 'paytech_api_error_detail':
            continue
        status_icon = "[PASSED]" if v else "[FAILED / NOT EXECUTED]"
        print(f" - {k:<30} : {status_icon}")
    print("=" * 80)

    return results

if __name__ == '__main__':
    run_paytech_e2e_tests()
