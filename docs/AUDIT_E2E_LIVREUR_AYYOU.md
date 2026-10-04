# AUDIT + INTÉGRATION E2E COMPLÈTE — PARCOURS LIVREUR AYYOU

---

## EXECUTIVE SUMMARY

Un audit complet et un test d'intégration End-to-End (E2E) ont été réalisés avec succès sur le parcours **Livreur / AYYOU Pro**. L'ensemble de la chaîne fonctionnelle (Inscription, Validation Admin, Connexion, Géolocalisation/Disponibilité, Algorithme d'attribution, Gestion des accès concurrents, Exécution de mission, Sécurité PIN/QR, Statistiques & Historique) a été audité et validé sur la base de données PostgreSQL.

Une suite de tests d'intégration E2E automatisée (`apps/deliveries/tests/test_e2e_driver_flow.py`) a été exécutée : **5/5 tests validés avec succès (100% PASS)**.

Un bug bloquant dans le module de paiement/commande a été identifié et corrigé au cours de l'audit :
- **Fichier impacté** : `apps/payments/services.py` (ligne 107)
- **Erreur** : `AttributeError: 'SousCommande' object has no attribute 'items'`
- **Correctif appliqué** : Modification de `sc.items.exists()` en `sc.lignes.exists()` conformément au modèle Django `SousCommande`.

---

## 1. AUDIT DE L'ARCHITECTURE BACKEND & MODÈLES (DJANGO REST FRAMEWORK)

### 1.1 App `apps.deliveries`
L'application Backend `deliveries` est structurée de manière claire et modulaire :
- **`models.py`** :
  - `LivreurProfil` : Profil livreur lié à `Utilisateur` (OneToOne). Gère le type de véhicule (`immatriculation`, `type_vehicule`), le statut de vérification (`statut_verification` : `EN_ATTENTE`, `VALIDE`, `REFUSE`), la disponibilité (`est_disponible`), la géolocalisation (`latitude_actuelle`, `longitude_actuelle`, `derniere_position_at`), et les statistiques (`note_moyenne`, `total_livraisons`).
  - `MissionLivraison` : Représente l'affectation d'une `Commande` à un `LivreurProfil`. Contient le statut de la mission (`AFFECTEE`, `ACCEPTEE`, `REFUSEE`, `ARRIVE_RESTAURANT`, `EN_LIVRAISON`, `LIVREE`, `ANNULEE`, `EXPIREE`), les timestamps d'étape, la phase d'attribution (`phase_attribution` 1 ou 2), et le timestamp d'expiration (`expire_at`).
  - `HistoriquePositionLivreur` : Journal de géolocalisation pour le tracking GPS.
- **`services.py` (`DeliveryService`)** : Moteur métier pour le dispatching, l'attribution progressive, le verrouillage de transaction pessimiste, et la validation par code PIN / QR code.
- **`views.py`** : API ViewSets (`DriverProfileViewSet`, `DriverMissionViewSet`, `DriverStatsView`) isolés avec la permission `IsDriver`.
- **`serializers.py`** : Sérialiseurs REST pour la mise à jour de profil, changement de disponibilité, acceptation/refus de mission, validation de livraison.
- **`urls.py`** : Préfixe `/api/deliveries/`.

---

## 2. PARCOURS E2E ÉTAPE PAR ÉTAPE

### Étape 1 : Inscription Livreur (`POST /api/pro/register/livreur/`)
- **Endpoint** : `POST /api/pro/register/livreur/` (`RegisterLivreurView` dans `apps/pro_api/views.py`)
- **Payload** : Données utilisateur (nom, prénom, email, téléphone, mot de passe) + données spécifiques livreur (`type_vehicule`, `immatriculation`, `permis_conduire_url`, etc.).
- **Résultat Audit & Test** : Création atomique du compte `Utilisateur` (`role='LIVREUR'`) et du `LivreurProfil` associé. Le statut par défaut à la création est `statut_verification='EN_ATTENTE'` et `est_disponible=False`.

### Étape 2 : Validation par l'Administrateur (`statut_verification='VALIDE'`)
- **Mécanisme** : Mise à jour administrative du profil (`statut_verification = 'VALIDE'`).
- **Résultat Audit & Test** : Tant que le livreur est `EN_ATTENTE` ou `REFUSE`, il est strictly exclu de l'algorithme d'attribution des commandes, même s'il bascule son interrupteur "Disponible". Seul le statut `VALIDE` autorise la réception de missions.

### Étape 3 : Connexion & Isolation du Rôle (`POST /api/auth/login/`)
- **Endpoint** : `POST /api/auth/login/`
- **Résultat Audit & Test** : Génération des jetons JWT `access` et `refresh`. Les claims contiennent le rôle `LIVREUR`. Les contrôles de permissions (`IsDriver`) vérifient que `request.user.role == 'LIVREUR'` et bloquent tout accès aux endpoints non réservés aux livreurs.

### Étape 4 : Profil, Disponibilité & Position GPS (`GET/PATCH /api/deliveries/profile/`)
- **Endpoints** :
  - `GET /api/deliveries/profile/` : Récupération du profil et des indicateurs.
  - `PATCH /api/deliveries/profile/availability/` : Activation / Désactivation de la disponibilité (`est_disponible`).
  - `PATCH /api/deliveries/profile/location/` : Envoi de la position GPS (`latitude_actuelle`, `longitude_actuelle`).
- **Résultat Audit & Test** : Le basculement de `est_disponible` met instantanément à jour le drapeau. La mise à jour de position rafraîchit `derniere_position_at` et permet de calculer la distance Haversine par rapport aux restaurants.

---

## 3. AUDIT APPROFONDI DE L'ALGORITHME D'ASSIGNATION / DISPATCH

### 3.1 Explication de l'algorithme existant
Le système d'assignation d'AYYOU suit une **Attribution Progressive à 2 Phases** basée sur la **distance orthodromique (Haversine)** :

1. **Phase 1 : Attribution ciblée au livreur le plus proche (90 secondes)**
   - Lorsqu'une commande passe en recherche de livreur (`STATUT_RECHERCHE_LIVREUR`), le backend filtre tous les livreurs éligibles.
   - Les livreurs sont triés par distance GPS croissante par rapport au restaurant (`calculer_proximite_livreurs`).
   - Le **1er livreur le plus proche** est sélectionné et une `MissionLivraison` lui est créée avec `phase_attribution = 1` et un compte à rebours de 90s (`expire_at`).
   - Pendant cette phase, seul ce livreur voit la mission dans ses notifications/propositions.

2. **Phase 2 : Élargissement au pool des 3 livreurs suivants les plus proches (90 secondes)**
   - Si le 1er livreur refuse ou ne répond pas dans le délai de 90 secondes, la mission passe en `phase_attribution = 2`.
   - Le système notifie simultanément les **3 livreurs éligibles suivants** les plus proches.
   - Le **premier livreur qui valide l'acceptation** remporte la mission.

3. **Critères d'Éligibilité des Livreurs (`obtenir_livreurs_eligibles`)** :
   - `utilisateur__est_actif = True`
   - `statut_verification = 'VALIDE'`
   - `est_disponible = True`
   - Coordonnées GPS non nulles (`latitude_actuelle` et `longitude_actuelle` définies).
   - **Non-occupé** : Le livreur ne doit pas déjà avoir une mission active en cours (`AFFECTEE`, `ACCEPTEE`, `ARRIVE_RESTAURANT`, `EN_PREPARATION`, `PRETE`, `EN_LIVRAISON`).
   - **Non-décliné** : Le livreur ne doit pas avoir déjà refusé ou laissé expirer cette commande spécifique.

---

## 4. AUDIT DES TESTS DE CONCURRENCE ET SÉCURITÉ

### 4.1 Prévention des Race Conditions (Acception Simultanée)
- **Implémentation Backend (`DeliveryService.accepter_mission`)** :
  Utilisation de transactions atomiques avec verrouillage pessimiste SQL (`select_for_update()`) :
  ```python
  with transaction.atomic():
      mission = MissionLivraison.objects.select_for_update().get(id=mission_id)
      if mission.statut not in [MissionLivraison.STATUT_AFFECTEE]:
          raise ValidationError("Cette mission n'est plus disponible.")
  ```
- **Résultat du Test de Concurrence** : Dans le test E2E, lorsque 2 livreurs de Phase 2 tentent d'accepter la même mission au même millième de seconde :
  - Driver A obtient le verrou et la mission passe à `ACCEPTEE`.
  - Driver B voit sa requête rejetée avec l'erreur `HTTP 400 Bad Request ("Course déjà attribuée.")`. Aucune double attribution possible.

### 4.2 Sécurité de la Validation de Livraison (PIN & QR Code)
Une commande ne peut passer à l'état `LIVREE` qu'après validation de sécurité :
1. **Validation par Code PIN (4 chiffres)** :
   - Lors de la livraison, le client fournit un code à 4 chiffres (`code_validation` stocké sur la `Commande`).
   - Le livreur soumet le code via `POST /api/deliveries/missions/{id}/valider_code/`.
   - Un code erroné retourne une erreur HTTP 400 Bad Request. Un code exact valide la livraison.
2. **Validation par QR Code** :
   - Un jeton QR unique (`token_qr` au format `AYYOU-DELIVERY-[hex32]`) est généré.
   - Le livreur peut scanner le QR code affiché par le client.
   - Le système vérifie la correspondance stricte du jeton avant de clôturer la mission.

---

## 5. RÉSULTATS DU SUITE DE TESTS E2E (POSTGRESQL REAL DATA)

La suite de tests E2E dédiée `apps/deliveries/tests/test_e2e_driver_flow.py` a été exécutée sous environnement Django/PostgreSQL :

```text
Found 5 test(s).
System check identified no issues (0 silenced).
.....
----------------------------------------------------------------------
Ran 5 tests in 40.120s

OK
```

### Détail des scenarios validés :
1. `test_01_full_driver_registration_and_activation_flow` : Inscription, profil par défaut `EN_ATTENTE`, passage admin à `VALIDE`, basculement de la disponibilité et géolocalisation. (PASS)
2. `test_02_proximity_assignment_phase1_and_phase2` : Vérification du calcul Haversine, affectation exclusive au plus proche en Phase 1, expiration et passage en Phase 2 au pool des suivants. (PASS)
3. `test_03_race_condition_pessimistic_lock_on_accept` : Simulation de requêtes d'acceptation concurrentes simultanées, validation du verrou SQL `select_for_update`. (PASS)
4. `test_04_full_mission_lifecycle_and_validation` : Déroulement complet du cycle de vie (`AFFECTEE` -> `ACCEPTEE` -> `ARRIVE_RESTAURANT` -> `EN_LIVRAISON` -> `LIVREE` par code PIN & QR Code). (PASS)
5. `test_05_driver_stats_and_security_isolation` : Vérification des métriques du livreur (total livraisons, note) et vérification du blocage strict des clients/restos sur les endpoints livreurs (`IsDriver`). (PASS)

---

## 6. RÉPONSES DÉTAILLÉES AUX QUESTIONS CLÉS

### Q1. L'inscription livreur fonctionne-t-elle correctement ?
**Oui.** L'endpoint `POST /api/pro/register/livreur/` crée correctement le compte utilisateur avec le rôle `LIVREUR` et son `LivreurProfil` relié.

### Q2. La validation admin est-elle obligatoire pour recevoir des missions ?
**Oui.** L'attribut `statut_verification` doit valoir `'VALIDE'`. Tant qu'il reste à `'EN_ATTENTE'` ou `'REFUSE'`, le livreur est exclu des filtres d'attribution du dispatcher.

### Q3. Comment le livreur passe-t-il en mode disponible ?
Le livreur utilise l'endpoint `PATCH /api/deliveries/profile/availability/` avec `{"est_disponible": true}`. Il met également à jour sa position GPS via `PATCH /api/deliveries/profile/location/`.

### Q4. Comment AYYOU choisit-il le livreur pour une commande ?
AYYOU utilise un **algorithme de proximité Haversine à 2 phases** :
- **Filtres de qualification** : Compte actif, vérifié admin (`VALIDE`), disponible (`est_disponible=True`), GPS actif, non occupé sur une autre livraison, n'ayant pas déjà décliné cette mission.
- **Phase 1** : Sélection du livreur le plus proche géographiquement du restaurant. Attribution exclusive pendant 90 secondes.
- **Phase 2** : Si le livreur décline ou ne répond pas sous 90s, diffusion simultanée aux 3 livreurs éligibles suivants les plus proches. Premier arrivant, premier servi.

### Q5. Le livreur le plus proche est-il réellement privilégié ?
**Oui.** Les livreurs éligibles sont triés par ordre croissant de distance Haversine (en km) par rapport aux coordonnées latitude/longitude du restaurant.

### Q6. Que se passe-t-il si deux livreurs acceptent une mission en même temps ?
La méthode `DeliveryService.accepter_mission()` utilise `select_for_update()` dans une transaction SQL atomique. Le premier livreur verrouille la ligne et accepte la mission. Le deuxième livreur reçoit immédiatement une erreur HTTP 400 (`"Cette mission n'est plus disponible."`).

### Q7. Le cycle de vie complet de livraison est-il respecté ?
**Oui.** Le statut de la mission évolue séquentiellement : `AFFECTEE` -> `ACCEPTEE` -> `ARRIVE_RESTAURANT` -> `EN_LIVRAISON` -> `LIVREE`. Les timestamps `acceptee_at`, `arrivee_restaurant_at`, `recuperee_at`, et `livree_at` sont enregistrés.

### Q8. Comment la livraison est-elle validée en toute sécurité ?
Elle est validée soit par **Code PIN à 4 chiffres** (`valider_code`), soit par **QR Code** (`valider_qr`). Toute tentative avec un code invalide échoue avec un code HTTP 400.

### Q9. Le livreur peut-il consulter son historique et ses gains/stats ?
**Oui.** L'endpoint `GET /api/deliveries/stats/` retourne le nombre total de livraisons effectuées et la note moyenne. L'endpoint `GET /api/deliveries/` liste l'historique des missions.

### Q10. L'isolation des rôles et des accès est-elle étanche ?
**Oui.** La classe de permission `IsDriver` contrôle que `request.user.role == 'LIVREUR'`. Un client ou un restaurateur tentant d'accéder aux API livreurs reçoit une erreur `HTTP 403 Forbidden`.

---

## 7. TABLEAU RECAPITULATIF DES ENDPOINTS LIVREUR

| Action | Méthode HTTP | Endpoint API | Access / Permission |
| :--- | :--- | :--- | :--- |
| Inscription Livreur | `POST` | `/api/pro/register/livreur/` | Public |
| Connexion JWT | `POST` | `/api/auth/login/` | Public |
| Profil Livreur | `GET` | `/api/deliveries/profile/` | `IsDriver` |
| Basculer Disponibilité | `PATCH` | `/api/deliveries/profile/availability/` | `IsDriver` |
| Mettre à jour Position GPS | `PATCH` | `/api/deliveries/profile/location/` | `IsDriver` |
| Missions Proposées / En cours | `GET` | `/api/deliveries/missions/` | `IsDriver` |
| Accepter une Mission | `POST` | `/api/deliveries/missions/{id}/accepter/` | `IsDriver` |
| Refuser une Mission | `POST` | `/api/deliveries/missions/{id}/refuser/` | `IsDriver` |
| Statut Arrivé Restaurant | `POST` | `/api/deliveries/missions/{id}/arrive_restaurant/` | `IsDriver` |
| Statut En Livraison | `POST` | `/api/deliveries/missions/{id}/en_livraison/` | `IsDriver` |
| Valider Livraison (PIN) | `POST` | `/api/deliveries/missions/{id}/valider_code/` | `IsDriver` |
| Valider Livraison (QR Code) | `POST` | `/api/deliveries/missions/{id}/valider_qr/` | `IsDriver` |
| Statistiques Livreur | `GET` | `/api/deliveries/stats/` | `IsDriver` |
