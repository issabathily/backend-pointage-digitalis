from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from .models import Pointage, Absence, Horaire
from .serializers import PointageSerializer, AbsenceSerializer, HoraireSerializer
from .permissions import IsManagerOrAdmin
from django.contrib.auth import get_user_model
from datetime import timedelta, datetime
from django.utils import timezone
from django.db import models

User = get_user_model()

class PointageViewSet(viewsets.ModelViewSet):
    queryset = Pointage.objects.all()
    serializer_class = PointageSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if user.role in ["ADMIN", "MANAGER"]:
            return Pointage.objects.all().select_related('employe')
        return Pointage.objects.filter(employe=user)

    @action(detail=False, methods=['get'])
    def today(self, request):
        """Récupérer tous les pointages du jour pour le manager"""
        if request.user.role not in ["ADMIN", "MANAGER"]:
            return Response({"error": "Accès refusé"}, status=403)
        
        today = timezone.now().date()
        pointages = Pointage.objects.filter(
            date=today
        ).select_related('employe').order_by('-heure_entree', '-heure_sortie')
        
        serializer = self.get_serializer(pointages, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['post'])
    def scan(self, request):
        """Enregistrer un pointage via scan QR"""
        user_id = request.data.get("user")
        type_pointage = request.data.get("type")
        date_str = request.data.get("date")
        
        try:
            employe = User.objects.get(id=user_id)
        except User.DoesNotExist:
            return Response({"error": "Employé introuvable"}, status=404)
        
        from datetime import datetime
        pointage_date = datetime.strptime(date_str, "%Y-%m-%d").date() if date_str else timezone.now().date()
        
        pointage, created = Pointage.objects.get_or_create(
            employe=employe,
            date=pointage_date
        )
        
        current_time = timezone.now().time()
        
        if type_pointage == "ENTREE":
            if pointage.heure_entree:
                return Response({"error": "Entrée déjà enregistrée"}, status=400)
            pointage.heure_entree = current_time
            if current_time > timezone.now().replace(hour=9, minute=0, second=0, microsecond=0).time():
                pointage.est_retard = True
                pointage.minutes_retard = (current_time.hour * 60 + current_time.minute) - (9 * 60)
        elif type_pointage == "SORTIE":
            # Si l'entrée n'existe pas, la créer automatiquement (cas où l'entrée a été faite manuellement)
            if not pointage.heure_entree:
                pointage.heure_entree = current_time  # Utiliser l'heure actuelle comme entrée par défaut
            if pointage.heure_sortie:
                return Response({"error": "Sortie déjà enregistrée"}, status=400)
            pointage.heure_sortie = current_time
            if current_time > timezone.now().replace(hour=17, minute=0, second=0, microsecond=0).time():
                pointage.heures_sup = (current_time.hour * 60 + current_time.minute) - (17 * 60)
        
        pointage.save()
        return Response({"message": "Pointage enregistré avec succès", "pointage": PointageSerializer(pointage).data})


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

        # Plus de vérification du solde de congé - les employés peuvent faire des demandes à tout moment
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


class KPIViewSet(viewsets.ViewSet):
    permission_classes = [IsAuthenticated]

    @action(detail=False, methods=['get'])
    def employee(self, request):
        """KPI pour l'employé connecté"""
        user = request.user
        today = timezone.now().date()
        current_month = today.replace(day=1)

        # Pointages du mois pour l'employé
        monthly_pointages = Pointage.objects.filter(
            employe=user,
            date__gte=current_month,
            date__lte=today
        )

        # Jours travaillés ce mois (dates uniques)
        unique_dates = monthly_pointages.values_list('date', flat=True).distinct()
        days_worked = len(unique_dates)

        # Retards ce mois
        monthly_lates = monthly_pointages.filter(est_retard=True).count()

        # Heures sup ce mois (convertir minutes en heures)
        total_overtime_minutes = monthly_pointages.aggregate(
            total=models.Sum('heures_sup')
        )['total'] or 0
        monthly_overtime = round(total_overtime_minutes / 60, 2)

        return Response({
            "days_worked_this_month": days_worked,
            "monthly_lates": monthly_lates,
            "monthly_overtime": monthly_overtime
        })

    @action(detail=False, methods=['get'])
    def employee_monthly_chart(self, request):
        """Données de graphique mensuel pour l'employé"""
        user = request.user
        today = timezone.now().date()
        current_month = today.replace(day=1)

        # Pointages du mois groupés par jour
        from django.db.models import Count
        daily_data = Pointage.objects.filter(
            employe=user,
            date__gte=current_month,
            date__lte=today
        ).values('date').annotate(
            hours_worked=models.Count('id')
        ).order_by('date')

        labels = [str(d['date']) for d in daily_data]
        data = [d['hours_worked'] for d in daily_data]

        return Response({
            "labels": labels,
            "datasets": [{
                "label": "Heures travaillées",
                "data": data,
                "borderColor": "#3b82f6",
                "backgroundColor": "rgba(59, 130, 246, 0.1)",
                "fill": True,
                "tension": 0.4
            }]
        })

    @action(detail=False, methods=['get'])
    def manager(self, request):
        """KPI pour manager/admin - vue globale de l'équipe"""
        user = request.user

        if user.role not in ["ADMIN", "MANAGER"]:
            return Response({"error": "Accès refusé"}, status=403)

        today = timezone.now().date()

        # Pointages du jour
        todays_pointages = Pointage.objects.filter(date=today)

        # Présents aujourd'hui
        present_today = todays_pointages.count()

        # En retard aujourd'hui
        late_today = todays_pointages.filter(est_retard=True).count()

        # Heures sup aujourd'hui
        total_overtime_minutes = todays_pointages.aggregate(
            total=models.Sum('heures_sup')
        )['total'] or 0
        overtime_today = round(total_overtime_minutes / 60, 2)

        # Total employés
        total_employees = User.objects.filter(role="EMPLOYE").count()

        return Response({
            "present_today": present_today,
            "late_today": late_today,
            "overtime_today": overtime_today,
            "total_employees": total_employees
        })

    @action(detail=False, methods=['get'])
    def manager_team_chart(self, request):
        """Graphique de répartition de l'équipe pour manager"""
        user = request.user

        if user.role not in ["ADMIN", "MANAGER"]:
            return Response({"error": "Accès refusé"}, status=403)

        today = timezone.now().date()

        # Répartition: présents, retards, absents
        total_employees = User.objects.filter(role="EMPLOYE").count()
        present = Pointage.objects.filter(date=today).count()
        late = Pointage.objects.filter(date=today, est_retard=True).count()
        absent = total_employees - present

        return Response({
            "labels": ["Présents", "En retard", "Absents"],
            "datasets": [{
                "label": "Répartition équipe",
                "data": [present, late, absent],
                "backgroundColor": ["#10b981", "#f59e0b", "#ef4444"],
                "borderWidth": 0
            }]
        })

    @action(detail=False, methods=['get'])
    def manager_weekly_trend(self, request):
        """Tendance hebdomadaire des pointages pour manager"""
        user = request.user

        if user.role not in ["ADMIN", "MANAGER"]:
            return Response({"error": "Accès refusé"}, status=403)

        today = timezone.now().date()
        week_ago = today - timedelta(days=7)

        # Pointages des 7 derniers jours
        from django.db.models import Count
        daily_data = Pointage.objects.filter(
            date__gte=week_ago,
            date__lte=today
        ).values('date').annotate(
            count=Count('id')
        ).order_by('date')

        labels = [str(d['date']) for d in daily_data]
        data = [d['count'] for d in daily_data]

        return Response({
            "labels": labels,
            "datasets": [{
                "label": "Pointages journaliers",
                "data": data,
                "borderColor": "#8b5cf6",
                "backgroundColor": "rgba(139, 92, 246, 0.1)",
                "fill": True,
                "tension": 0.4
            }]
        })

    @action(detail=False, methods=['get'])
    def attendance_stats(self, request):
        from django.contrib.auth import get_user_model
        User = get_user_model()

        today = timezone.now().date()
        
        # Récupérer tous les employés
        total_employees = User.objects.filter(role='EMPLOYE').count()
        
        # Pointages du jour
        today_pointages = Pointage.objects.filter(date=today)
        
        # Présents (ont pointé aujourd'hui)
        presents = today_pointages.values('employe').distinct().count()
        
        # Retards (pointages avec retard aujourd'hui)
        retards = today_pointages.filter(est_retard=True).count()
        
        # Absents (employés qui n'ont pas pointé aujourd'hui)
        absents = total_employees - presents
        
        # Taux de ponctualité
        taux_ponctualite = ((presents - retards) / total_employees * 100) if total_employees > 0 else 0
        
        return Response({
            "total_employees": total_employees,
            "presents": presents,
            "retards": retards,
            "absents": absents,
            "taux_ponctualite": round(taux_ponctualite, 1)
        })





