import qrcode
import json
import hmac
import hashlib
from io import BytesIO
from django.conf import settings
from django.core.files.base import ContentFile
from BackendPointage.accounts.models import QRDynamic

SECRET_KEY = settings.SECRET_KEY


def (user, type_pointage):
generate_dynamic_qr
    # Création session QR en base
    qr_session = QRDynamic.objects.create(
        employe=user,
        type_pointage=type_pointage
    )

    payload = {
        "token": str(qr_session.token),
        "user_id": user.id,
        "nom": user.nom,
        "prenom": user.prenom,
        "type": type_pointage,
        "created_at": str(qr_session.created_at)
    }

    payload_json = json.dumps(payload)

    signature = hmac.new(
        SECRET_KEY.encode(),
        payload_json.encode(),
        hashlib.sha256
    ).hexdigest()

    final_payload = {
        "data": payload,
        "signature": signature
    }

    qr_data = json.dumps(final_payload)

    qr = qrcode.make(qr_data)

    buffer = BytesIO()
    qr.save(buffer, format="PNG")

    file_name = f"dynamic_qr_{user.id}_{type_pointage}.png"

    return {
        "qr_image": buffer.getvalue(),
        "token": qr_session.token,
        "expires_at": qr_session.expires_at,
        "file_name": file_name
    }