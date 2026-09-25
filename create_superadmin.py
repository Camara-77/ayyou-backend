import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from apps.users.models import Utilisateur, Role, UtilisateurRole

email = 'admin@ayyou.com'
password = 'Password123!'

user, created = Utilisateur.objects.get_or_create(
    email=email,
    defaults={
        'numero_telephone': '+221770000000',
        'prenom': 'Super',
        'nom': 'Admin',
        'is_staff': True,
        'is_superuser': True,
        'est_actif': True,
        'est_verifie': True,
    }
)

user.set_password(password)
user.is_staff = True
user.is_superuser = True
user.est_actif = True
user.est_verifie = True
user.save()

role_admin, _ = Role.objects.get_or_create(nom='ADMINISTRATEUR')
UtilisateurRole.objects.get_or_create(utilisateur=user, role=role_admin)

print(f"Super Admin OK : {user.email}")
