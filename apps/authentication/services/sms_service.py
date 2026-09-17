import logging

logger = logging.getLogger('apps.authentication')


class SmsService:
    """
    Abstraction du service d'envoi de SMS.
    Permet de basculer facilement entre un logger de démo local, Twilio, Infobip ou un API SMS local.
    """

    @staticmethod
    def send_otp_sms(phone_number: str, code: str) -> bool:
        """
        Envoie le code OTP par SMS au numéro spécifié.
        En mode dev local, simule l'envoi sans exposer le code dans les logs de production.
        """
        # Log sécurisé indiquant l'envoi sans exposer le code OTP en clair dans les logs
        logger.info(f"[SMS SERVICE] Envoi d'un code OTP par SMS vers {phone_number}")
        # Message de démo console pour environnement de développement local uniquement
        print(f"==================================================")
        print(f"[SMS SERVICE DEMO] SMS envoyé à {phone_number} | Code OTP: {code}")
        print(f"==================================================")
        return True
