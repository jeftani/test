# game/routing.py
from django.urls import path
from .consumers import PingPongGameConsumer

websocket_urlpatterns = [
    path('api/ws/game/<str:room_code>/', PingPongGameConsumer.as_asgi(),name='game_ws'), 
]