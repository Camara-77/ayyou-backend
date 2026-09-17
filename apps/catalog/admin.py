from django.contrib import admin
from .models import Categorie, Etablissement, Produit, VarianteProduit, OptionProduit, PublicationFeed, LikeProduit

@admin.register(Categorie)
class CategorieAdmin(admin.ModelAdmin):
    list_display = ('nom', 'slug', 'est_active', 'ordre', 'date_creation')
    prepopulated_fields = {'slug': ('nom',)}

@admin.register(Etablissement)
class EtablissementAdmin(admin.ModelAdmin):
    list_display = ('nom', 'type_etablissement', 'statut', 'note_moyenne', 'est_verifie', 'date_creation')
    list_filter = ('type_etablissement', 'statut', 'est_verifie')
    search_fields = ('nom', 'adresse', 'specialite')

@admin.register(Produit)
class ProduitAdmin(admin.ModelAdmin):
    list_display = ('nom', 'etablissement', 'categorie', 'prix_base', 'est_disponible', 'stock_disponible', 'stock_ayyou_reserve')
    list_filter = ('est_disponible', 'categorie', 'etablissement')
    search_fields = ('nom', 'description')

admin.site.register(VarianteProduit)
admin.site.register(OptionProduit)
admin.site.register(PublicationFeed)
admin.site.register(LikeProduit)
