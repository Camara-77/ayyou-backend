import os
import logging
from django.core.exceptions import ValidationError
from django.conf import settings

logger = logging.getLogger('apps')


class CloudinaryFeedService:
    """
    Service dédié à la gestion des médias (vidéos vertical feed) stockés sur Cloudinary.
    Sécurité : Les clés d'API (CLOUDINARY_API_SECRET, API_KEY) restent exclusivement sur le backend Django.
    Règle métier : Durée maximale d'une vidéo = 3 minutes (180 secondes).
    Dossier de stockage : ayyou/feed/
    """
    MAX_DURATION_SECONDS = 180  # 3 minutes

    @classmethod
    def is_configured(cls) -> bool:
        cloud_name = getattr(settings, 'CLOUDINARY_CLOUD_NAME', '')
        api_key = getattr(settings, 'CLOUDINARY_API_KEY', '')
        api_secret = getattr(settings, 'CLOUDINARY_API_SECRET', '')
        return bool(cloud_name and api_key and api_secret)

    @classmethod
    def upload_feed_video(cls, file_obj, duree_secondes: int = None) -> dict:
        """
        Téléverse une vidéo de publication Feed vers Cloudinary dans le dossier ayyou/feed/.
        Valide impérativement que la durée ne dépasse pas 180 secondes (3 min).
        Returns dict with keys: media_url, cloudinary_public_id, duree_video
        """
        if duree_secondes and duree_secondes > cls.MAX_DURATION_SECONDS:
            raise ValidationError("La durée maximale de la vidéo est de 3 minutes (180 secondes).")

        # Validation basique du type de fichier
        content_type = getattr(file_obj, 'content_type', '')
        if content_type and not content_type.startswith('video/'):
            raise ValidationError("Le fichier téléversé doit être une vidéo valide (ex: MP4, WebM, MOV).")

        if not cls.is_configured():
            logger.error("[CLOUDINARY ERROR] Clés d'API Cloudinary non configurées dans settings/.env.")
            raise ValidationError("Configuration Cloudinary manquante. Impossible d'effectuer un téléversement réel.")

        try:
            import cloudinary.uploader
            upload_result = cloudinary.uploader.upload(
                file_obj,
                folder="ayyou/feed",
                resource_type="video"
            )

            public_id = upload_result.get('public_id')
            secure_url = upload_result.get('secure_url') or upload_result.get('url')
            cloudinary_duration = upload_result.get('duration')

            detected_duration = duree_secondes
            if cloudinary_duration:
                detected_duration = int(round(cloudinary_duration))

            if detected_duration and detected_duration > cls.MAX_DURATION_SECONDS:
                # Supprimer immédiatement la vidéo si elle dépasse 180s
                cloudinary.uploader.destroy(public_id, resource_type="video")
                raise ValidationError("La durée maximale de la vidéo est de 3 minutes (180 secondes).")

            dur_sec = detected_duration or 120
            mins = dur_sec // 60
            secs = dur_sec % 60
            duree_formatted = f"{mins}:{secs:02d}"

            return {
                "media_url": secure_url,
                "cloudinary_public_id": public_id,
                "duree_video": duree_formatted
            }

        except ValidationError:
            raise
        except (Exception, ModuleNotFoundError, ImportError) as e:
            logger.error(f"[CLOUDINARY UPLOAD ERROR] {str(e)}")
            raise ValidationError(f"Échec du téléversement réel vers Cloudinary : {str(e)}")

    @classmethod
    def upload_product_image(cls, file_obj) -> dict:
        """
        Téléverse une image de plat/produit vers Cloudinary dans le dossier ayyou/products/.
        Returns dict with keys: image_url, cloudinary_public_id
        """
        content_type = getattr(file_obj, 'content_type', '')
        if content_type and not (content_type.startswith('image/') or content_type == 'application/octet-stream'):
            raise ValidationError("Le fichier téléversé doit être une image valide (ex: JPG, PNG, WebP).")

        if not cls.is_configured():
            logger.error("[CLOUDINARY ERROR] Clés d'API Cloudinary non configurées dans settings/.env.")
            raise ValidationError("Configuration Cloudinary manquante. Impossible d'effectuer un téléversement réel.")

        try:
            import cloudinary.uploader
            upload_result = cloudinary.uploader.upload(
                file_obj,
                folder="ayyou/products",
                resource_type="image"
            )
            public_id = upload_result.get('public_id')
            secure_url = upload_result.get('secure_url') or upload_result.get('url')
            return {
                "image_url": secure_url,
                "cloudinary_public_id": public_id
            }
        except ValidationError:
            raise
        except (Exception, ModuleNotFoundError, ImportError) as e:
            logger.error(f"[CLOUDINARY PRODUCT IMAGE UPLOAD ERROR] {str(e)}")
            raise ValidationError(f"Échec du téléversement réel vers Cloudinary : {str(e)}")





    @classmethod
    def delete_feed_video(cls, public_id: str) -> bool:
        """
        Supprime la vidéo de Cloudinary à l'aide de son public_id.
        """
        if not public_id:
            return False

        if not cls.is_configured():
            logger.info(f"[CLOUDINARY MOCK DELETE] Suppression simulée pour {public_id}")
            return True

        try:
            import cloudinary.uploader
            result = cloudinary.uploader.destroy(public_id, resource_type="video")
            return result.get('result') == 'ok'
        except Exception as e:
            logger.error(f"[CLOUDINARY DELETE ERROR] {str(e)}")
            return False
