import os
import tempfile
import subprocess
import logging
from django.core.files.uploadedfile import UploadedFile

logger = logging.getLogger(__name__)


class TranscriptionService:
    """
    Service de transcription vocale (Audio -> Texte) basé sur le modèle Whisper (openai/whisper-base).
    Exécuté sur CPU avec chargement différé en mémoire (Singleton) et conversion automatique via FFmpeg.
    """
    _pipeline = None
    MAX_FILE_SIZE_BYTES = 10 * 1024 * 1024  # 10 Mo max
    MAX_DURATION_SECONDS = 30               # 30 secondes max

    @classmethod
    def get_pipeline(cls):
        """
        Charge et retourne le pipeline ASR Whisper (openai/whisper-base) en Singleton.
        """
        if cls._pipeline is None:
            logger.info("Chargement du modèle Whisper (openai/whisper-base)...")
            from transformers import pipeline
            cls._pipeline = pipeline(
                "automatic-speech-recognition",
                model="openai/whisper-base",
                device=-1  # CPU
            )
            logger.info("Modèle Whisper chargé avec succès.")
        return cls._pipeline

    @classmethod
    def convert_to_wav(cls, input_path: str, output_path: str) -> bool:
        """
        Convertit n'importe quel format audio (webm, ogg, mp4, etc.) en WAV 16kHz mono via FFmpeg.
        """
        try:
            cmd = [
                "ffmpeg",
                "-y",
                "-i", input_path,
                "-ar", "16000",
                "-ac", "1",
                "-c:a", "pcm_s16le",
                output_path
            ]
            res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=15)
            return res.returncode == 0 and os.path.exists(output_path)
        except Exception as e:
            logger.error(f"Erreur de conversion FFmpeg: {e}")
            return False

    @classmethod
    def transcribe(cls, audio_file: UploadedFile) -> dict:
        """
        Transcrit un fichier audio uploadé.
        Retourne dict {"status": "success", "text": "..."} ou {"status": "error", "message": "..."}.
        """
        if not audio_file:
            return {"status": "error", "message": "Aucun fichier audio fourni."}

        # 1. Validation de la taille du fichier (max 10 Mo)
        if audio_file.size > cls.MAX_FILE_SIZE_BYTES:
            return {"status": "error", "message": "Le fichier audio est trop volumineux (10 Mo maximum)."}

        input_temp = None
        output_temp = None

        try:
            # Save uploaded audio to temp input file
            ext = os.path.splitext(audio_file.name)[1] or '.webm'
            with tempfile.NamedTemporaryFile(delete=False, suffix=ext) as f_in:
                for chunk in audio_file.chunks():
                    f_in.write(chunk)
                input_temp = f_in.name

            # Generate temp WAV file path
            output_temp = input_temp + "_16k.wav"

            # Convert to WAV 16kHz via FFmpeg
            converted = cls.convert_to_wav(input_temp, output_temp)
            target_path = output_temp if converted else input_temp

            # Transcribe with Whisper pipeline
            pipe = cls.get_pipeline()
            result = pipe(
                target_path,
                generate_kwargs={"language": "french"}
            )

            transcribed_text = ""
            if isinstance(result, dict):
                transcribed_text = result.get("text", "").strip()
            elif isinstance(result, list) and len(result) > 0:
                transcribed_text = result[0].get("text", "").strip()

            if not transcribed_text:
                return {
                    "status": "error",
                    "message": "Aucun texte n'a pu être extrait du message vocal. Veuillez réenregistrer."
                }

            return {
                "status": "success",
                "text": transcribed_text
            }

        except Exception as e:
            logger.error(f"Erreur lors de la transcription Whisper: {e}")
            return {
                "status": "error",
                "message": "Impossible de traiter le fichier audio. Veuillez essayer en écrivant votre demande."
            }

        finally:
            # Nettoyage strict et immédiat des fichiers temporaires
            for p in [input_temp, output_temp]:
                if p and os.path.exists(p):
                    try:
                        os.remove(p)
                    except Exception:
                        pass
