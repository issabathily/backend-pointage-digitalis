from rest_framework import serializers
from .models import Pointage, Absence, Horaire

class PointageSerializer(serializers.ModelSerializer):
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
