# Audit Technique : Logique d'Abonnement avec Essai Gratuit de 1 Mois (Restaurant & Vendeur)

## 1. Vue d'Ensemble
Dans l'application AYYOU, tout nouvel établissement de type **RESTAURANT** ou **VENDEUR** bénéficie automatiquement d'un **essai gratuit d'un (1) mois calendaire** dès sa création.

Pendant cette période d'essai :
- L'établissement est actif (`statut_abonnement = 'ACTIF'`).
- Il a accès à l'ensemble des fonctionnalités de sa plateforme dédiée.
- Aucun paiement immédiat n'est exigé.

À l'issue de la période d'essai (1 mois calendaire) :
- L'abonnement bascule au statut `EXPIRE`.
- L'accès payant est requis à hauteur de **10 000 FCFA / mois** via PayTech.
- Les données et le compte ne sont jamais supprimés.

---

## 2. Implémentation Backend

### A. Modèle `Etablissement` (`apps/catalog/models.py`)
Dans la méthode `save()` du modèle `Etablissement`, lors de la première création (`self.pk is None`), si les dates d'abonnement ne sont pas explicitement spécifiées :
1. `self.date_debut_abonnement` est initialisé à `timezone.now()`.
2. `self.date_expiration_abonnement` est calculé avec `PaymentService.ajouter_un_mois_calendaire(now)`.
3. `self.statut_abonnement` passe immédiatement à `STATUT_ABONNEMENT_ACTIF` (`'ACTIF'`).

### B. Inscription des Professionnels (`apps/pro_api/serializers.py`)
- `RestaurantRegistrationSerializer` : Crée l'utilisateur avec le rôle RESTAURANT et l'établissement associé. L'établissement bénéficie automatiquement de la sauvegarde avec essai gratuit.
- `VendeurRegistrationSerializer` : Crée l'utilisateur avec le rôle VENDEUR et l'établissement associé. L'établissement bénéficie également de l'essai gratuit.

### C. Expiration Automatique (`apps/catalog/management/commands/expire_pro_subscriptions.py`)
La commande Celery/CRON `expire_pro_subscriptions` s'exécute régulièrement pour repérer les abonnements `ACTIF` dont la date d'expiration est dépassée (`date_expiration_abonnement < timezone.now()`) et les fait basculer à `EXPIRE`.

### D. Renouvellement / Paiement PayTech (`apps/payments/services.py`)
- Tarif standard : 10 000 FCFA / mois.
- Méthodes `initier_paiement_abonnement` et `confirmer_paiement_abonnement`.
- Lors de la confirmation d'un paiement valide via PayTech, la date d'expiration est prolongée d'un mois calendaire supplémentaire à partir de la date d'expiration actuelle (ou à partir de `now` si déjà expiré).

---

## 3. Compte Restaurant de Test
Une commande de management dédiée a été créée :
```bash
python manage.py setup_test_restaurant
```

### Identifiants du Compte de Test :
- **Email** : `restaurant.test@ayyou.test`
- **Mot de passe** : `AyyouTest@2026`
- **ID Établissement** : `132` (ou ID auto-attribué)
- **Nom Établissement** : `Chez Loutcha (Test)`
- **Statut Vérification** : `VALIDE` (`est_verifie = True`)
- **Statut Abonnement** : `ACTIF` (Période d'essai d'un mois)

---

## 4. Couverture de Tests Automatisés
Le fichier de test `apps/payments/tests/test_subscription_trial.py` couvre 8 scénarios clés :
1. `test_1_nouveau_restaurant_inscription_essai_gratuit` : Vérifie l'activation immédiate et l'essai d'un mois pour Restaurant.
2. `test_2_nouveau_vendeur_inscription_essai_gratuit` : Vérifie l'activation immédiate et l'essai d'un mois pour Vendeur.
3. `test_3_restaurant_acces_pendant_premier_mois` : Vérifie que le statut reste actif pendant la validité.
4. `test_4_restaurant_apres_expiration` : Vérifie la bascule au statut `EXPIRE` après l'échéance.
5. `test_5_vendeur_apres_expiration` : Vérifie la bascule au statut `EXPIRE` pour Vendeur après l'échéance.
6. `test_6_restaurant_deja_abonne_pas_de_nouvel_essai` : Vérifie que les modifications ultérieures n'écrasent pas les dates d'abonnement existantes.
7. `test_7_restaurant_de_test_valide_et_actif` : Vérifie le bon fonctionnement du compte de test via `setup_test_restaurant`.
8. `test_8_paiement_renouvellement_paytech` : Vérifie la prolongation d'abonnement et la création d'un `AbonnementPro` de 10 000 FCFA lors d'un paiement PayTech.
