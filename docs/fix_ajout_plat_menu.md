# Rapport de Correction — Ajout et Modification d'un Plat / Produit dans le Menu AYYOU

**Projet** : AYYOU Application Pro (Restaurant & Vendeur)  
**Date** : 02/10/2026  
**Auteur** : Assistant Antigravity  

---

## 1. Contexte & Diagnostic du Problème

### Symptôme Initial
Lorsqu'un utilisateur connecté sur un profil **RESTAURANT** ou **VENDEUR** remplissait le formulaire d'ajout (`/pro/menu/new`) ou de modification (`/pro/menu/edit/:id`) et cliquait sur **« Enregistrer le plat »** :
1. L'application redirigeait immédiatement et silencieusement vers la page de profil (`/pro/profile`).
2. Aucun message d'erreur ou d'alerte ne s'affichait sur l'interface.
3. Aucun plat/produit n'était créé ni mis à jour dans la base de données PostgreSQL.
4. Le plat n'apparaissait pas dans la liste des plats du menu.

---

## 2. Causes Racines Identifiées lors de l'Audit

| N° | Composant | Cause Racine | Impact |
|---|---|---|---|
| **1** | Backend `permissions.py` | `IsApprovedMerchant` exigeait `statut_verification == 'VALIDE'`. Les marchands nouvellement inscrits ou bénéficiant du mois d'essai gratuit ont leur établissement en statut `EN_ATTENTE`. | DRF retournait une erreur HTTP **403 Forbidden**. |
| **2** | Frontend `pro-menu-edit.component.ts` | La méthode `onFileSelected()` lisait l'image locale via `FileReader.readAsDataURL()`, plaçant la chaîne Base64 (`data:image/png;base64...`) dans `dish.imageUrl`. Si la soumission survenait avant la fin du téléversement Cloudinary, Django DRF l'envoyait au champ `URLField()`. | Django DRF rejetait le payload avec une erreur HTTP **400 Bad Request** (`Enter a valid URL`). |
| **3** | Frontend `pro-menu-edit.component.ts` | Dans `saveDish()`, le callback `error` du `subscribe()` exécutait `this.router.navigate(['/pro/profile'])` sans intercepter la réponse HTTP. | L'erreur était complètement étouffée et l'utilisateur était redirigé vers `/pro/profile` sans aucune explication. |
| **4** | Frontend `pro-menu.service.ts` | `dish.categoryId` n'était pas systématiquement synchronisé avec l'identifiant numérique de la catégorie PostgreSQL réelles lors de la sélection UI des catégories. | Django recevait `categorie: undefined` ou `null`. |

---

## 3. Corrections Implémentées

### A. Backend (`apps/pro_api/`)

#### 1. Mettre à jour `IsApprovedMerchant`, `IsApprovedRestaurant` et `IsApprovedVendeur` dans `permissions.py`
Les classes de permission vérifient désormais que l'utilisateur est un professionnel actif **ET** possède un établissement dont le statut de vérification est `VALIDE` **OU** qui dispose d'un abonnement / mois d'essai actif non expiré (`statut_abonnement == 'ACTIF'` et `date_expiration_abonnement > now`).

```python
class IsApprovedMerchant(permissions.BasePermission):
    def has_permission(self, request, view):
        if not (request.user and request.user.is_authenticated and request.user.est_actif):
            return False

        has_merchant_role = request.user.roles_attribues.filter(
            role__nom__in=[Role.RESTAURANT, Role.VENDEUR]
        ).exists()
        if not has_merchant_role:
            return False

        from apps.catalog.models import Etablissement
        from django.utils import timezone
        from django.db.models import Q
        now = timezone.now()

        return request.user.etablissements.filter(
            Q(statut_verification=Etablissement.STATUT_VALIDE) |
            (Q(statut_abonnement=Etablissement.STATUT_ABONNEMENT_ACTIF) & Q(date_expiration_abonnement__gt=now))
        ).exists()
```

#### 2. Assouplir `get_merchant_etablissement` dans `views_merchant.py`
La fonction utilitaire priorise les établissements validés mais bascule de façon sécurisée (`.first()`) sur le premier établissement du marchand même s'il est en cours de validation ou en période d'essai, éliminant les exceptions `Http404` ou `MultipleObjectsReturned`.

---

### B. Frontend (`Ayyou-frontend`)

#### 1. Filtrage et Nettoyage des URL d'Images (`pro-menu.service.ts`)
Dans `saveDish()`, si `dish.imageUrl` commence par `data:image/` ou n'est pas une URL HTTP/HTTPS valide, le service la remplace automatiquement par l'URL de fallback valide par défaut avant la soumission DRF.

#### 2. Gestion de l'Upload et Désactivation du Submit (`pro-menu-edit.component.ts` & `.html`)
- Ajout des états `isSubmitting: boolean` et `errorMessage: string`.
- Le bouton de soumission est désormais **désactivé** pendant le téléversement de l'image sur Cloudinary (`isUploadingImage`) et pendant la requête d'enregistrement (`isSubmitting`).

#### 3. Bannière d'Affichage d'Erreurs Explicites (`pro-menu-edit.component.html`)
Ajout d'une bannière d'alerte rouge en haut du formulaire qui affiche les erreurs HTTP (400, 403, 500) directement au lieu de rediriger l'utilisateur vers `/pro/profile`.

#### 4. Synchronisation des Catégories (`pro-menu-edit.component.ts`)
Ajout de la méthode `syncCategoryId()` qui effectue une correspondance (insensible à la casse) entre les catégories frontend et le tableau `backendCategories` pour garantir l'envoi de l'ID numérique exact de la catégorie PostgreSQL.

---

## 4. Comparatif Avant / Après

| Scénario | Comportement AVANT | Comportement APRÈS |
|---|---|---|
| **Nouvel établissement (Période d'essai)** | Rejet 403 Forbidden car statut `EN_ATTENTE`. | Accès autorisé pendant le mois d'essai gratuit. |
| **Image locale sélectionnée** | Rejet 400 Bad Request en raison de la chaîne Base64 `data:image/...`. | Envoi de l'URL Cloudinary finale ou fallback HTTPS valide. |
| **Erreur de validation/réseau** | Redirection immédiate et silencieuse vers `/pro/profile`. | Bannière rouge affichée sur la page avec le message d'erreur précis. |
| **Bouton Enregistrer** | Reste cliquable pendant l'upload image, provoquant des race conditions. | Désactivé avec libellé « Téléversement... » puis « Enregistrement... ». |

---

## 5. Résultat des Tests de Validation

### Tests Automatisés Backend Django
- **Commande** : `python manage.py test apps.pro_api.tests apps.payments.tests.test_subscription_trial`
- **Résultat** : `Ran 27 tests in 81.280s - OK` (27/27 tests réussis).

### Compilation Frontend Angular
- **Commande** : `npx ng build --configuration production`
- **Résultat** : Compilation production Angular 19 sans aucune erreur.
