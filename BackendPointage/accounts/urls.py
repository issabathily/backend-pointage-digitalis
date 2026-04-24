from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import MeView, UserViewSet, generate_dynamic_qr_view

router = DefaultRouter()
router.register(r"users", UserViewSet, basename="users")

urlpatterns = [
    path("auth/me/", MeView.as_view(), name="me"),             # GET /api/auth/me/
    path("qr/dynamic/generate/", generate_dynamic_qr_view),    # POST /api/qr/dynamic/generate/
    path("", include(router.urls)),                            # /api/users/
]