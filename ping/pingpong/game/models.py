from django.db import models

class Room(models.Model):
    room_id = models.CharField(max_length=100, unique=True)
    player1 = models.CharField(max_length=100)
    player2 = models.CharField(max_length=100, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
