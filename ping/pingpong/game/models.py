# models.py
from django.db import models

class Room(models.Model):
    room_id = models.CharField(max_length=100, unique=True)  # Room identifier
    player1_name = models.CharField(max_length=100)
    player2_name = models.CharField(max_length=100, blank=True, null=True)  # Second player can be empty initially
    score_player1 = models.IntegerField(default=0)  # Score for player 1
    score_player2 = models.IntegerField(default=0)  # Score for player 2
    winner = models.CharField(max_length=100, blank=True, null=True)  # Winner name, can be null until the game ends
    created_at = models.DateTimeField(auto_now_add=True)  # When the room was created

    def __str__(self):
        return f"Room {self.room_id} - {self.player1_name} vs {self.player2_name if self.player2_name else 'Waiting for Player 2'} | Score: {self.score_player1}-{self.score_player2} | Winner: {self.winner if self.winner else 'Not decided yet'}"
