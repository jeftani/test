from django.contrib import admin
from .models import Room

# Optionally, you can customize how the Room model is displayed in the admin
class RoomAdmin(admin.ModelAdmin):
    list_display = ('room_id', 'player1_name', 'player2_name', 'score_player1', 'score_player2', 'winner', 'created_at')
    search_fields = ('room_id', 'player1_name', 'player2_name')
    list_filter = ('created_at', 'winner')

# Register the Room model with the customized RoomAdmin class
admin.site.register(Room, RoomAdmin)
