from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.urls import reverse
import random
import string

class CreateRoomAPIView(APIView):
    def post(self, request, *args, **kwargs):
        player1 = request.data.get("player1")
        player2 = request.data.get("player2")

        if not player1 or not player2:
            return Response({"error": "Both player names are required."}, status=status.HTTP_400_BAD_REQUEST)

        # Generate a random room code with only alphanumeric characters
        def generate_room_code(length=6):
            """Generates a random room code with the specified length."""
            letters_and_digits = string.ascii_letters + string.digits
            return ''.join(random.choice(letters_and_digits) for _ in range(length))

        room_name = generate_room_code()

        # Construct WebSocket URL
        ws_url = reverse('game:game_ws', kwargs={'room_code': room_name})

        # Send WebSocket URL back to both players
        return Response({
            "message": "Room created successfully!",
            "room_name": room_name,
            "ws_url": f"ws://127.0.0.1:8000{ws_url}"
        }, status=status.HTTP_201_CREATED)