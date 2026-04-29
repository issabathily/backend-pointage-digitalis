from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import MeView, UserViewSet, generate_dynamic_qr_view, create_manager_qr_session, get_active_manager_session

router = DefaultRouter()
router.register(r"users", UserViewSet, basename="users")

urlpatterns = [
    path("auth/me/", MeView.as_view(), name="me"),             # GET /api/auth/me/
    path("qr/dynamic/generate/", generate_dynamic_qr_view),    # POST /api/qr/dynamic/generate/
    path("qr/manager/session/create/", create_manager_qr_session),  # POST /api/qr/manager/session/create/
    path("qr/manager/session/active/", get_active_manager_session),  # GET /api/qr/manager/session/active/
    path("", include(router.urls)),                            # /api/users/
]