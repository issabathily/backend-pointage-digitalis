from rest_framework import serializers
from .models import Pointage, Absence, Horaire

class PointageSerializer(serializers.ModelSerializer):
    user_nom = serializers.CharField(source='employe.nom', read_only=True)
    user_prenom = serializers.CharField(source='employe.prenom', read_only=True)
    
    class Meta:
        model = Pointage
        fields = '__all__'

"""
class AbsenceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Absence
        fields = '__all__'
"""
""""""

class AbsenceSerializer(serializers.ModelSerializer):

    class Meta:
        model = Absence
        fields = '__all__'
        read_only_fields = ['statut', 'user']
        
class HoraireSerializer(serializers.ModelSerializer):
    class Meta:
        model = Horaire
        fields = '__all__'
