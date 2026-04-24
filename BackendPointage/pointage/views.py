from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from .models import Pointage, Absence, Horaire
from .serializers import PointageSerializer, AbsenceSerializer, HoraireSerializer
from .permissions import IsManagerOrAdmin
from django.contrib.auth import get_user_model
from datetime import timedelta

User = get_user_model()

class PointageViewSet(viewsets.ModelViewSet):
    queryset = Pointage.objects.all()
    serializer_class = PointageSerializer
    permission_classes = [IsAuthenticated]


def working_days(start_date, end_date):
    """Calcule les jours ouvrables entre deux dates (hors dimanches)."""
    count = 0
    current = start_date
    while current <= end_date:
        if current.weekday() != 6:
            count += 1
        current += timedelta(days=1)
    return count


class AbsenceViewSet(viewsets.ModelViewSet):
    queryset = Absence.objects.all()
    serializer_class = AbsenceSerializer
    permission_classes = [IsAuthenticated]

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    def get_queryset(self):
        user = self.request.user
        if user.role == "ADMIN":
            return Absence.objects.all()
        elif user.role == "MANAGER":
            return Absence.objects.filter(user__role="EMPLOYE") | Absence.objects.filter(user=user)
        return Absence.objects.filter(user=user)

    @action(detail=True, methods=['put'], permission_classes=[IsManagerOrAdmin])
    def valider(self, request, pk=None):
        absence = self.get_object()

        if absence.statut != 'EN_ATTENTE':
            return Response({'error': 'Cette absence a déjà été traitée.'}, status=400)

        # Vérifier le solde si c'est un congé
        if absence.typeAbsence == 'CONGE':
            days = working_days(absence.dateDebut, absence.dateFin)
            user = absence.user
            if user.conge_restant < days:
                return Response({
                    'error': f'Solde insuffisant. {days} jours demandés, {user.conge_restant} restants.'
                }, status=400)
            user.conge_restant -= days
            user.save()

        absence.statut = 'VALIDEE'
        absence.save()
        return Response({'message': 'Absence validée'})

    @action(detail=True, methods=['put'], permission_classes=[IsManagerOrAdmin])
    def rejeter(self, request, pk=None):
        absence = self.get_object()
        absence.statut = 'REFUSEE'
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

    # ==============================
    # 2️⃣ SCAN QR (MANAGER)
    # ==============================
    @action(detail=False, methods=['post'])
    def scan_qr(self, request):

        if request.user.role != "manager":
            return Response({"error": "Accès refusé"}, status=403)

        token = request.data.get("qr_token")

        try:
            session = QRDynamic.objects.get(token=token)
        except QRDynamic.DoesNotExist:
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
    





