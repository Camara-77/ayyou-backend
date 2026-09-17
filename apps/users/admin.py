from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils.translation import gettext_lazy as _
from .models import Utilisateur, ProfilClient, Role, UtilisateurRole, ProfilLivreur, DocumentLivreur


class ProfilClientInline(admin.StackedInline):
    model = ProfilClient
    can_delete = False
    verbose_name_plural = _('Profil Client')
    fk_name = 'utilisateur'


class UtilisateurRoleInline(admin.TabularInline):
    model = UtilisateurRole
    extra = 1


@admin.register(Utilisateur)
class UtilisateurAdmin(BaseUserAdmin):
    """
    Administration sécurisée du modèle Utilisateur AYYOU.
    Masque le mot de passe en clair.
    """
    fieldsets = (
        (None, {'fields': ('email', 'password')}),
        (_('Informations personnelles'), {'fields': ('prenom', 'nom', 'numero_telephone')}),
        (_('Statuts & Autorisants'), {'fields': ('est_actif', 'est_verifie', 'is_staff', 'is_superuser', 'groups', 'user_permissions')}),
        (_('Dates clés'), {'fields': ('derniere_connexion', 'date_creation', 'date_modification')}),
    )
    readonly_fields = ('date_creation', 'date_modification', 'derniere_connexion')
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'numero_telephone', 'prenom', 'nom', 'password1', 'password2'),
        }),
    )
    list_display = ('email', 'numero_telephone', 'prenom', 'nom', 'est_actif', 'est_verifie', 'is_staff', 'date_creation')
    list_filter = ('est_actif', 'est_verifie', 'is_staff', 'is_superuser', 'date_creation')
    search_fields = ('email', 'numero_telephone', 'prenom', 'nom')
    ordering = ('-date_creation',)
    inlines = [ProfilClientInline, UtilisateurRoleInline]


@admin.register(ProfilClient)
class ProfilClientAdmin(admin.ModelAdmin):
    list_display = ('utilisateur', 'date_creation', 'date_modification')
    search_fields = ('utilisateur__email', 'utilisateur__numero_telephone', 'utilisateur__prenom', 'utilisateur__nom')
    readonly_fields = ('date_creation', 'date_modification')


@admin.register(Role)
class RoleAdmin(admin.ModelAdmin):
    list_display = ('nom', 'description', 'date_creation')
    search_fields = ('nom', 'description')


@admin.register(UtilisateurRole)
class UtilisateurRoleAdmin(admin.ModelAdmin):
    list_display = ('utilisateur', 'role', 'date_attribution')
    list_filter = ('role', 'date_attribution')
    search_fields = ('utilisateur__email', 'utilisateur__numero_telephone', 'role__nom')


class DocumentLivreurInline(admin.TabularInline):
    model = DocumentLivreur
    extra = 0
    readonly_fields = ('date_creation', 'date_modification')


@admin.register(ProfilLivreur)
class ProfilLivreurAdmin(admin.ModelAdmin):
    list_display = ('utilisateur', 'statut_verification', 'est_disponible', 'type_vehicule', 'immatriculation', 'date_creation')
    list_filter = ('statut_verification', 'est_disponible', 'type_vehicule')
    search_fields = ('utilisateur__email', 'utilisateur__numero_telephone', 'utilisateur__prenom', 'utilisateur__nom', 'immatriculation')
    readonly_fields = ('date_creation', 'date_modification')
    inlines = [DocumentLivreurInline]


@admin.register(DocumentLivreur)
class DocumentLivreurAdmin(admin.ModelAdmin):
    list_display = ('profil_livreur', 'type_document', 'statut', 'date_verification', 'date_creation')
    list_filter = ('type_document', 'statut')
    search_fields = ('profil_livreur__utilisateur__email', 'profil_livreur__utilisateur__nom', 'fichier_url_ou_reference')
    readonly_fields = ('date_creation', 'date_modification')

