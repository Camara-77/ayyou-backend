# 📋 Plan de Décommissionnement PayDunya — AYYOU

> **Statut actuels :** ⏸️ **CONSERVÉ EN MODE STANDBY POUR TRANSITION SECURISEE**  
> **Date de rédaction :** 23 Septembre 2026

---

## 📌 Context & Directives

Conformément à la consigne strict de la Phase 1 :
* **PayDunya n'a pas été supprimé.**
* Les endpoints `/api/payments/initiate/` et `/api/payments/ipn/` restent fonctionnels et accessibles.
* Les clés `PAYDUNYA_*` restent conservées dans `.env` et `config/settings/base.py`.

---

## 🚀 Calendrier de Décommissionnement Post-Validation PayTech

Le décommissionnement définitif de PayDunya s'effectuera en 3 étapes **après validation finale de PayTech en production** :

### Étape 1 : Basculement du Trafic (100% PayTech)
- Basculement complet des flux clients vers PayTech (fait en Phase 1).
- Période d'observation de 14 jours des métriques et notifications IPN PayTech.

### Étape 2 : Nettoyage des Fichiers Backend
1. **Suppression du service client PayDunya** :
   - Supprimer `apps/payments/paydunya_service.py`.
2. **Archivage des scripts de test PayDunya** :
   - Archiver `test_paydunya.py` et `test_phase53_real_sandbox.py`.
3. **Nettoyage des vues & URLs** :
   - Supprimer `InitiatePaydunyaPaiementView` et `PaydunyaIPNView` dans `apps/payments/views.py`.
   - Supprimer les routes associées dans `apps/payments/urls.py`.

### Étape 3 : Nettoyage de la Configuration
1. **Retrait des variables dans `.env`** :
   - Retirer `PAYDUNYA_MASTER_KEY`, `PAYDUNYA_PRIVATE_KEY`, `PAYDUNYA_PUBLIC_KEY`, `PAYDUNYA_TOKEN`, `PAYDUNYA_MODE`.
2. **Retrait des variables dans `config/settings/base.py`** :
   - Retirer les paramètres `PAYDUNYA_*`.
