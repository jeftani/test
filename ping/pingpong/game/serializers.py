from rest_framework import serializers
from .models import Room

class RoomSerializer(serializers.ModelSerializer):
    class Meta:
        model = Room
        fields = ['room_id', 'player1_name', 'player2_name', 'score_player1', 'score_player2', 'winner', 'created_at']

