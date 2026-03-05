from rest_framework import viewsets
from .models import Pointage, Absence, Horaire
from .serializers import PointageSerializer, AbsenceSerializer, HoraireSerializer
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

class PointageViewSet(viewsets.ModelViewSet):
    queryset = Pointage.objects.all()
    serializer_class = PointageSerializer
    permission_classes = [IsAuthenticated]
"""
class AbsenceViewSet(viewsets.ModelViewSet):
    queryset = Absence.objects.all()
    serializer_class = AbsenceSerializer
    #permission_classes = [IsAuthenticated]
"""
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from .models import Absence
from .serializers import AbsenceSerializer
from .permissions import IsManagerOrAdmin

class AbsenceViewSet(viewsets.ModelViewSet):

    queryset = Absence.objects.all()
    serializer_class = AbsenceSerializer
    permission_classes = [IsAuthenticated]

    # 👇 Valider une absence
    @action(detail=True, methods=['put'], permission_classes=[IsManagerOrAdmin])
    def valider(self, request, pk=None):
        absence = self.get_object()
        absence.statut = 'VALIDE'
        absence.save()
        return Response({'message': 'Absence validée'})

    # 👇 Rejeter une absence
    @action(detail=True, methods=['put'], permission_classes=[IsManagerOrAdmin])
    def rejeter(self, request, pk=None):
        absence = self.get_object()
        absence.statut = 'REJETE'
        absence.save()
        return Response({'message': 'Absence rejetée'})
    
   
class HoraireViewSet(viewsets.ModelViewSet):
    queryset = Horaire.objects.all()
    serializer_class = HoraireSerializer
    permission_classes = [IsAuthenticated]

class ReportViewSet(viewsets.ViewSet):
    permission_classes = [IsAuthenticated]

    def list(self, request):
        return Response({"message": "Rapports globaux ou mensuels"})
    
import qrcode
from io import BytesIO
from django.core.files.base import ContentFile
from django.utils import timezone
from datetime import time
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from .models import QRCodeSession, Pointage,QRDynamic
from django.contrib.auth import get_user_model

User = get_user_model()

class QRCodeViewSet(viewsets.ViewSet):
    permission_classes = [IsAuthenticated]

    # ==============================
    # 1️⃣ GENERER QR DYNAMIQUE
    # ==============================
    @action(detail=False, methods=['post'])
    def generate_qr(self, request):

        
        if request.user.role != "manager":
            return Response({"error": "Accès refusé"}, status=403)

        employe_id = request.data.get("employe_id")
        type_pointage = request.data.get("type")  # ENTREE ou SORTIE

        employe = User.objects.get(id=employe_id)

        session = QRCodeSession.objects.create(
            employe=employe,
            type_pointage=type_pointage
        )

        qr_data = str(session.token)

        qr = qrcode.make(qr_data)
        buffer = BytesIO()
        qr.save(buffer, format='PNG')

        return Response({
            "qr_token": qr_data,
            "expires_at": session.expires_at
        })
    """
    # ==============================
    # 2️⃣ SCAN QR (MANAGER)
    # ==============================
    @action(detail=False, methods=['post'])
    def scan_qr(self, request):

        if request.user.role != "manager":
            return Response({"error": "Accès refusé"}, status=403)

        token = request.data.get("qr_token")

        try:
            session = QRCodeSession.objects.get(token=token)
        except  QRCodeSession.DoesNotExist:
            return Response({"error": "QR invalide"}, status=404)

        if session.is_used:
            return Response({"error": "QR déjà utilisé"}, status=400)

        if timezone.now() > session.expires_at:
            return Response({"error": "QR expiré"}, status=400)

        employe = session.employe
        today = timezone.now().date()

        pointage, created = Pointage.objects.get_or_create(
            employe=employe,
            date=today
        )

        current_time = timezone.now().time()

        # ===== ENTREE =====
        if session.type_pointage == "ENTREE":

            if pointage.heure_entree:
                return Response({"error": "Entrée déjà enregistrée"}, status=400)

            pointage.heure_entree = current_time

            # RETARD si > 09:00
            if current_time > time(9, 0):
                pointage.est_retard = True
                pointage.minutes_retard = (
                    current_time.hour * 60 + current_time.minute
                ) - (9 * 60)

        # ===== SORTIE =====
        if session.type_pointage == "SORTIE":

            if not pointage.heure_entree:
                return Response({"error": "Entrée non enregistrée"}, status=400)

            if pointage.heure_sortie:
                return Response({"error": "Sortie déjà enregistrée"}, status=400)

            pointage.heure_sortie = current_time

            # HEURES SUP > 17:00
            if current_time > time(17, 0):
                pointage.heures_sup = (
                    current_time.hour * 60 + current_time.minute
                ) - (17 * 60)

        pointage.save()
        session.is_used = True
        session.save()

        return Response({"message": "Pointage enregistré avec succès"})
    





