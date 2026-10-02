import os
import tempfile
import subprocess
import logging
from django.core.files.uploadedfile import UploadedFile

logger = logging.getLogger(__name__)


import re

def extract_clean_search_query(raw_text: str) -> str:
    """
    Étape B — Interprétation IA : Nettoie la transcription brute en extrayant le terme de recherche exact.
    Exemples:
      'Je cherche un bon thiéboudienne Penda Mbaye à Dakar' -> 'Thiéboudienne Penda Mbaye'
      'Je voudrais manger du poisson braisé pas trop cher' -> 'Poisson braisé'
      'Trouve-moi un restaurant qui vend du mafé' -> 'Mafé'
    """
    if not raw_text:
        return ""

    text = raw_text.strip()

    intro_patterns = [
        r"^(?:bonjour|salut|s'il vous plaît|stp|svp)\s*",
        r"^(?:je cherche|je veux|je voudrais|je souhaite|j'aimerais|trouve(?:-moi)?|montre(?:-moi)?|donne(?:-moi)?|est-ce que vous avez|combien coûte)\s+(?:un|une|du|des|le|la|les)?\s*",
        r"^(?:un|une|du|des|le|la|les)\s+",
        r"^(?:bon|bonne|meilleur|meilleure)\s+"
    ]

    for pattern in intro_patterns:
        text = re.sub(pattern, "", text, flags=re.IGNORECASE).strip()

    outro_patterns = [
        r"\s+(?:à dakar|sur dakar|à dakar centre|à almadies|au plateau|pas trop cher|le moins cher|s'il vous plaît|svp)$",
        r"\s+(?:s'il vous plaît|svp|merci)$"
    ]

    for pattern in outro_patterns:
        text = re.sub(pattern, "", text, flags=re.IGNORECASE).strip()

    text = re.sub(r"^[^\w\s]+|[^\w\s]+$", "", text).strip()

    if not text:
        return raw_text.strip()

    return text[0].upper() + text[1:] if len(text) > 1 else text.upper()


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
        Retourne dict {"success": True, "transcription": "...", "search_query": "..."}.
        """
        if not audio_file:
            return {
                "success": False,
                "status": "error",
                "message": "Aucun fichier audio fourni.",
                "error": "Aucun fichier audio fourni."
            }

        # 1. Validation de la taille du fichier (max 10 Mo)
        if audio_file.size > cls.MAX_FILE_SIZE_BYTES:
            return {
                "success": False,
                "status": "error",
                "message": "Le fichier audio est trop volumineux (10 Mo maximum).",
                "error": "Le fichier audio est trop volumineux (10 Mo maximum)."
            }

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

            # Transcribe audio file
            transcribed_text = ""

            # 1. Essayer via speech_recognition (Google ASR fr-FR / Whisper)
            try:
                import speech_recognition as sr
                recognizer = sr.Recognizer()
                with sr.AudioFile(target_path) as source:
                    audio_data = recognizer.record(source)
                    transcribed_text = recognizer.recognize_google(audio_data, language="fr-FR").strip()
            except Exception as sr_err:
                logger.warning(f"speech_recognition Google ASR warning: {sr_err}")

            # 2. Fallback via Transformers Whisper si speech_recognition est vide
            if not transcribed_text:
                try:
                    pipe = cls.get_pipeline()
                    result = pipe(
                        target_path,
                        generate_kwargs={"task": "transcribe"}
                    )
                    if isinstance(result, dict):
                        transcribed_text = result.get("text", "").strip()
                    elif isinstance(result, list) and len(result) > 0:
                        transcribed_text = result[0].get("text", "").strip()
                except Exception as whisper_err:
                    logger.warning(f"Whisper pipeline fallback warning: {whisper_err}")

            if not transcribed_text:
                return {
                    "success": False,
                    "status": "error",
                    "message": "Aucun texte n'a pu être extrait du message vocal. Veuillez réenregistrer.",
                    "error": "Aucun texte n'a pu être extrait du message vocal. Veuillez réenregistrer."
                }

            clean_query = extract_clean_search_query(transcribed_text)

            return {
                "success": True,
                "status": "success",
                "transcription": transcribed_text,
                "search_query": clean_query,
                "text": clean_query
            }

        except Exception as e:
            logger.error(f"Erreur lors de la transcription vocale: {e}")
            return {
                "success": False,
                "status": "error",
                "message": "Impossible de traiter le fichier audio. Veuillez essayer en écrivant votre demande.",
                "error": "Impossible de traiter le fichier audio. Veuillez essayer en écrivant votre demande."
            }

        finally:
            # Nettoyage strict et immédiat des fichiers temporaires
            for p in [input_temp, output_temp]:
                if p and os.path.exists(p):
                    try:
                        os.remove(p)
                    except Exception:
                        pass
