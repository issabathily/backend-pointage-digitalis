# pointage/urls.py
# pointage/urls.py
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import PointageViewSet, AbsenceViewSet, HoraireViewSet, ReportViewSet,QRCodeViewSet, KPIViewSet

router = DefaultRouter()
router.register(r'pointages', PointageViewSet, basename='pointages')
router.register(r'absences', AbsenceViewSet, basename='absences')
router.register(r'horaires', HoraireViewSet, basename='horaires')
router.register(r'reports', ReportViewSet, basename='reports')
router.register(r'qr', QRCodeViewSet, basename='qr')
router.register(r'kpi', KPIViewSet, basename='kpi')
urlpatterns = [
    path('', include(router.urls)),
]

#urlpatterns=[
#path("qr/scan/", QRCodeViewSet.as_view({'post': 'scan'}), name='qr-scan'),
#]

