import os
import base64
import re
import requests
from io import BytesIO


def clean_phone_for_whatsapp(phone: str) -> str:
    """
    Limpia y estandariza el número de teléfono con código de país para WhatsApp.
    Ejemplos en Argentina:
      - '11 5555-1234' -> '5491155551234'
      - '011 15 5555-1234' -> '5491155551234'
      - '+54 9 11 5555-1234' -> '5491155551234'
    """
    if not phone:
        return ""
    
    digits = re.sub(r'\D', '', str(phone).strip())
    
    # Manejar formatos comunes de Argentina
    if digits.startswith('0'):
        digits = digits[1:]
    
    if digits.startswith('15') and len(digits) == 10:
        digits = '11' + digits[2:]
        
    if len(digits) == 10:
        # Número local de 10 dígitos (ej: 1155551234) -> agregar 549
        digits = '549' + digits
    elif len(digits) == 12 and digits.startswith('54') and not digits.startswith('549'):
        # 541155551234 -> convertir a 5491155551234
        digits = '549' + digits[2:]
        
    return digits


class WhatsAppService:
    @staticmethod
    def get_provider():
        """Detecta el proveedor configurado en las variables de entorno."""
        provider = os.getenv("WHATSAPP_PROVIDER", "").strip().lower()
        if provider:
            return provider
        if os.getenv("WHATSAPP_ACCESS_TOKEN") and os.getenv("WHATSAPP_PHONE_NUMBER_ID"):
            return "meta"
        if os.getenv("WHATSAPP_GATEWAY_URL"):
            return "evolution"
        if os.getenv("TWILIO_ACCOUNT_SID"):
            return "twilio"
        return "none"

    @classmethod
    def enviar_factura_pdf(cls, telefono: str, pdf_bytes: bytes, filename: str, caption: str):
        """
        Envía un archivo PDF de factura adjunto al número de WhatsApp indicado.
        
        Retorna:
            tuple: (bool: success, str: message_or_error)
        """
        clean_phone = clean_phone_for_whatsapp(telefono)
        if not clean_phone:
            return False, "El número de teléfono del cliente no es válido o está vacío."

        provider = cls.get_provider()

        if provider == "none":
            return False, (
                "No hay credenciales de WhatsApp configuradas en el archivo .env. "
                "Configura WHATSAPP_ACCESS_TOKEN y WHATSAPP_PHONE_NUMBER_ID (Meta Cloud API) "
                "o WHATSAPP_GATEWAY_URL (Gateway QR)."
            )

        try:
            if provider == "meta":
                return cls._send_via_meta(clean_phone, pdf_bytes, filename, caption)
            elif provider in ("evolution", "gateway"):
                return cls._send_via_evolution(clean_phone, pdf_bytes, filename, caption)
            elif provider == "twilio":
                return cls._send_via_twilio(clean_phone, caption)
            else:
                return False, f"Proveedor de WhatsApp '{provider}' no reconocido."
        except Exception as e:
            return False, f"Error al procesar el envío de WhatsApp: {str(e)}"

    @classmethod
    def _send_via_meta(cls, phone: str, pdf_bytes: bytes, filename: str, caption: str):
        """Envío mediante Meta WhatsApp Cloud API oficial."""
        token = os.getenv("WHATSAPP_ACCESS_TOKEN", "").strip()
        phone_number_id = os.getenv("WHATSAPP_PHONE_NUMBER_ID", "").strip()
        api_version = os.getenv("WHATSAPP_API_VERSION", "v20.0").strip()

        if not token or not phone_number_id:
            return False, "Faltan configurar WHATSAPP_ACCESS_TOKEN y/o WHATSAPP_PHONE_NUMBER_ID en .env."

        # 1. Subir el archivo PDF a los servidores de Meta
        upload_url = f"https://graph.facebook.com/{api_version}/{phone_number_id}/media"
        headers_upload = {
            "Authorization": f"Bearer {token}"
        }
        files = {
            "file": (filename, pdf_bytes, "application/pdf")
        }
        data = {
            "messaging_product": "whatsapp",
            "type": "application/pdf"
        }

        try:
            resp_upload = requests.post(upload_url, headers=headers_upload, files=files, data=data, timeout=30)
        except requests.RequestException as e:
            return False, f"Error de conexión al subir PDF a Meta: {str(e)}"

        if resp_upload.status_code not in (200, 201):
            try:
                err_data = resp_upload.json()
                err_msg = err_data.get("error", {}).get("message", resp_upload.text)
            except Exception:
                err_msg = resp_upload.text
            return False, f"Error de Meta al subir el PDF ({resp_upload.status_code}): {err_msg}"

        media_id = resp_upload.json().get("id")
        if not media_id:
            return False, "Meta no retornó un ID de archivo válido para el PDF."

        # 2. Enviar el mensaje con el documento adjunto
        messages_url = f"https://graph.facebook.com/{api_version}/{phone_number_id}/messages"
        headers_msg = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }
        payload = {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": phone,
            "type": "document",
            "document": {
                "id": media_id,
                "caption": caption,
                "filename": filename
            }
        }

        try:
            resp_msg = requests.post(messages_url, headers=headers_msg, json=payload, timeout=30)
        except requests.RequestException as e:
            return False, f"Error de conexión al enviar mensaje a Meta: {str(e)}"

        if resp_msg.status_code not in (200, 201):
            try:
                err_data = resp_msg.json()
                err_msg = err_data.get("error", {}).get("message", resp_msg.text)
            except Exception:
                err_msg = resp_msg.text
            return False, f"Error de Meta al enviar documento ({resp_msg.status_code}): {err_msg}"

        return True, "Comprobante en PDF enviado con éxito vía Meta WhatsApp API."

    @classmethod
    def _send_via_evolution(cls, phone: str, pdf_bytes: bytes, filename: str, caption: str):
        """Envío mediante Evolution API / Gateway QR autohospedado."""
        gateway_url = os.getenv("WHATSAPP_GATEWAY_URL", "").rstrip("/")
        api_key = os.getenv("WHATSAPP_GATEWAY_APIKEY", "").strip()
        instance = os.getenv("WHATSAPP_GATEWAY_INSTANCE", "default").strip()

        if not gateway_url:
            return False, "Falta configurar WHATSAPP_GATEWAY_URL en .env."

        endpoint = f"{gateway_url}/message/sendMedia/{instance}"
        headers = {
            "Content-Type": "application/json"
        }
        if api_key:
            headers["apikey"] = api_key

        b64_data = base64.b64encode(pdf_bytes).decode("utf-8")
        media_base64 = f"data:application/pdf;base64,{b64_data}"

        payload = {
            "number": phone,
            "mediaMessage": {
                "mediatype": "document",
                "fileName": filename,
                "caption": caption,
                "media": media_base64
            }
        }

        try:
            resp = requests.post(endpoint, headers=headers, json=payload, timeout=30)
        except requests.RequestException as e:
            return False, f"Error de conexión al Gateway de WhatsApp: {str(e)}"

        if resp.status_code not in (200, 201):
            return False, f"Error del Gateway ({resp.status_code}): {resp.text}"

        return True, "Comprobante en PDF enviado con éxito vía WhatsApp Gateway."

    @classmethod
    def _send_via_twilio(cls, phone: str, caption: str):
        """Envío mediante Twilio."""
        account_sid = os.getenv("TWILIO_ACCOUNT_SID", "").strip()
        auth_token = os.getenv("TWILIO_AUTH_TOKEN", "").strip()
        from_number = os.getenv("TWILIO_WHATSAPP_NUMBER", "").strip()

        if not account_sid or not auth_token or not from_number:
            return False, "Faltan credenciales de Twilio en .env."

        url = f"https://api.twilio.com/2010-04-01/Accounts/{account_sid}/Messages.json"
        data = {
            "From": f"whatsapp:{from_number}",
            "To": f"whatsapp:+{phone}",
            "Body": caption
        }

        try:
            resp = requests.post(url, data=data, auth=(account_sid, auth_token), timeout=30)
        except requests.RequestException as e:
            return False, f"Error de conexión con Twilio: {str(e)}"

        if resp.status_code not in (200, 201):
            return False, f"Error de Twilio ({resp.status_code}): {resp.text}"

        return True, "Mensaje enviado con éxito vía Twilio WhatsApp."
