from django.contrib import admin
from .models import Notification


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'utilisateur',
        'titre',
        'type_notification',
        'canal',
        'statut',
        'est_lu',
        'created_at',
    )
    list_filter = ('type_notification', 'canal', 'statut', 'est_lu', 'created_at')
    search_fields = ('titre', 'message', 'utilisateur__email', 'utilisateur__numero_telephone')
    readonly_fields = ('created_at', 'updated_at', 'date_lecture')
    ordering = ('-created_at',)
