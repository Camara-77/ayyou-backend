# Documentation — Intégration du Module Planning Client (« MON PLANNING »)

**Projet** : Application Client AYYOU  
**Date** : 02/10/2026  
**Auteur** : Assistant Antigravity  

---

## 1. Contexte & Périmètre

Dans le cadre du nouveau parcours de planification client de l'application AYYOU, nous avons intégré l'écran principal : **« MON PLANNING »**.

Cet écran est accessible à tout utilisateur Client connecté depuis le bouton **Calendrier / Planning** situé dans le header principal à côté de la cloche de notification.

---

## 2. Architecture & Modèle de Données PostgreSQL

Conformément à la règle **Sans Mock**, toutes les données affichées sur le calendrier et la liste des repas proviennent directement de la base de données PostgreSQL via une API REST Django.

### Modèle Django : `RepasPlanifie` (`apps/orders/models.py`)

```python
class RepasPlanifie(models.Model):
    utilisateur = models.ForeignKey(Utilisateur, on_delete=models.CASCADE, related_name='repas_planifies')
    produit = models.ForeignKey(Produit, on_delete=models.CASCADE, related_name='repas_planifies')
    etablissement = models.ForeignKey(Etablissement, on_delete=models.CASCADE, related_name='repas_planifies')
    variante = models.ForeignKey(VarianteProduit, null=True, blank=True, on_delete=models.SET_NULL)
    date_planifiee = models.DateField(db_index=True)
    creneau = models.CharField(max_length=20, choices=[('MATIN', 'Petit-déjeuner'), ('MIDI', 'Déjeuner'), ('SOIR', 'Dîner'), ('EN_CAS', 'En-cas')])
    statut = models.CharField(max_length=30, choices=[('PLANIFIE', 'Planifié'), ('COMMANDE', 'Commande créée'), ('ANNULE', 'Annulé')], default='PLANIFIE')
    prix_total = models.DecimalField(max_digits=10, decimal_places=2)
    quantite = models.PositiveIntegerField(default=1)
    instructions = models.TextField(blank=True, default='')
    date_creation = models.DateTimeField(auto_now_add=True)
    date_modification = models.DateTimeField(auto_now=True)
```

---

## 3. Endpoints API REST Backend

| Méthode | Route API | Description |
|---|---|---|
| **GET** | `/api/orders/planning/?annee=YYYY&mois=MM` | Récupère tous les repas du mois et la liste `dates_avec_repas` pour les points rouges du calendrier. |
| **GET** | `/api/orders/planning/?annee=YYYY&mois=MM&date=YYYY-MM-DD` | Récupère les repas du jour sélectionné. |
| **POST** | `/api/orders/planning/` | Enregistre un nouveau repas planifié. |
| **GET** | `/api/orders/planning/{id}/` | Consultation d'un repas planifié. |
| **DELETE** | `/api/orders/planning/{id}/` | Annulation d'un repas planifié. |

### Commande de Données Réelles de Test
- **Commande** : `python manage.py setup_test_planning`
- **Action** : Génère des repas planifiés réels en base pour le client de test pour vérifier immédiatement le calendrier dynamique avec PostgreSQL.

---

## 4. Composants & Intégration Frontend (`Ayyou-frontend`)

1. **Header Client (`AppHeaderComponent`)** :
   - Fichiers : `src/app/features/client/components/app-header/`
   - Ajout du bouton icône Calendrier à côté du bouton de notification.
2. **Page Planning (`PlanningComponent`)** :
   - Route : `/planning` (`authGuard`)
   - Fichiers : `src/app/features/client/pages/planning/` (`.ts`, `.html`, `.scss`)
   - Reproduction à 100% du design de la maquette (Rouge `#E51A29`, sélecteur Jour/Semaine/Mois, grille mensuelle dynamique, points rouges sous les jours avec repas, mise en valeur du jour sélectionné, affichage des repas et boutons d'action).
3. **Services & Interfaces** :
   - Service : `PlanningService` (`src/app/core/services/planning.service.ts`)
   - Interfaces : `PlannedMeal`, `PlanningMonthResponse` (`src/app/core/models/planning.ts`)

---

## 5. Résultat des Tests & Validation

- **Tests Backend Django** : `python manage.py test apps.orders` -> **OK**
- **Compilation Angular 19** : `npx ng build --configuration production` -> **Compilation Réussie** dans `dist/ayyou/`.
