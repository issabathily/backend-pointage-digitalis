from rest_framework import viewsets, status
from rest_framework.views import APIView
from rest_framework.response import Response
from django.contrib.auth import get_user_model, authenticate
from .serializers import UserSerializer
from rest_framework.permissions import IsAdminUser, IsAuthenticated
from rest_framework_simplejwt.tokens import RefreshToken

User = get_user_model()

# CRUD utilisateurs
class UserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [IsAdminUser]  # seul admin peut gérer les users

# Login JWT
class LoginView(APIView):
    def post(self, request):
        email = request.data.get('email')
        password = request.data.get('password')
        user = authenticate(request, username=email, password=password)
        if user:
            refresh = RefreshToken.for_user(user)
            return Response({
                'access': str(refresh.access_token),
                'refresh': str(refresh),
                'role': UserSerializer(user).role,
                'user_'

            })
        return Response({'error': 'Email ou mot de passe invalide'}, status=status.HTTP_401_UNAUTHORIZED)

# Récupérer utilisateur connecté
class MeView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response(UserSerializer(request.user).data)
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from .models import User
from .services.qr_service import generate_dynamic_qr
from django.http import HttpResponse


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def generate_dynamic_qr_view(request):

    if request.user.role != "ADMIN":
        return Response({"error": "Accès refusé"}, status=403)

    user_id = request.data.get("user_id")
    type_pointage = request.data.get("type")  # ENTREE ou SORTIE

    try:
        user = User.objects.get(id=user_id)

        result = generate_dynamic_qr(user, type_pointage)

        response = HttpResponse(
            result["qr_image"],
            content_type="image/png"
        )

        response["Content-Disposition"] = f'inline; filename="{result["file_name"]}"'

        return response

    except User.DoesNotExist:
        return Response({"error": "Employé introuvable"}, status=404)