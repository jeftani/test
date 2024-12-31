from django.urls import path
from django.views.static import serve
from django.conf import settings
from django.conf.urls.static import static
from . import views
from .views import CreateRoomAPIView
from . import consumers

app_name = 'game'  # This sets the namespace to 'game'

urlpatterns = [
    path('', serve, {'path': 'index.html', 'document_root': settings.BASE_DIR / 'static/game'}),
    path('ws/game/<str:room_code>/', consumers.PingPongGameConsumer.as_asgi(), name='game_ws'),
    path('create-room/', CreateRoomAPIView.as_view(), name='create_room'),
]