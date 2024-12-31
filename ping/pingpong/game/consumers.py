import json
import random
import asyncio
from channels.generic.websocket import AsyncWebsocketConsumer
from django.core.cache import cache
from .models import Room  # Import the Room model to save the match history
from channels.db import database_sync_to_async #with the database 


class PingPongGameConsumer(AsyncWebsocketConsumer):
    is_ball_moving = False

    async def connect(self):
        self.room_code = self.scope['url_route']['kwargs']['room_code']
        self.room_group_name = f"game_{self.room_code}"

        # Add the WebSocket connection to the room group
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )

        await self.accept()

        players = await self.get_players()
        if len(players) < 2:
            players.append(self.channel_name)
            await self.set_players(players)
            player_role = 'player1' if len(players) == 1 else 'player2'
            await self.send(text_data=json.dumps({'role': player_role}))
        else:
            await self.send(text_data=json.dumps({'role': 'spectator'}))

        game_state = await self.get_game_state()
        if not game_state:
            await self.reset_game()

        await self.send_game_state()

        if len(players) == 2 and not self.is_ball_moving:
            self.is_ball_moving = True
            asyncio.create_task(self.ball_movement_loop())

    async def disconnect(self, close_code):
        players = await self.get_players()
        if self.channel_name in players:
            players.remove(self.channel_name)
            await self.set_players(players)

        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )

        if not players:
            self.is_ball_moving = False
            await self.reset_game()

    async def receive(self, text_data):
        data = json.loads(text_data)
        action = data.get('action', '')
        player_role = data.get('role', '')

        if action in ['move_up', 'move_down']:
            await self.update_player_position(player_role, action)

        await self.send_game_state()

    async def send_game_state(self):
        game_state = await self.get_game_state()
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'game_update',
                'game_state': game_state,
            }
        )

    async def game_update(self, event):
        await self.send(text_data=json.dumps({'gameState': event['game_state']}))

    async def ball_movement_loop(self):
        while self.is_ball_moving:
            await self.update_ball_position()
            await self.send_game_state()
            await asyncio.sleep(0.03)

    async def update_player_position(self, player, action):
        game_state = await self.get_game_state()
        if player == 'player1':
            if action == 'move_up' and game_state['player1']['y'] > 0:
                game_state['player1']['y'] -= game_state['player1']['speed']
            elif action == 'move_down' and game_state['player1']['y'] < 400 - game_state['player1']['height']:
                game_state['player1']['y'] += game_state['player1']['speed']
        elif player == 'player2':
            if action == 'move_up' and game_state['player2']['y'] > 0:
                game_state['player2']['y'] -= game_state['player2']['speed']
            elif action == 'move_down' and game_state['player2']['y'] < 400 - game_state['player2']['height']:
                game_state['player2']['y'] += game_state['player2']['speed']
        await self.set_game_state(game_state)

    async def update_ball_position(self):
        game_state = await self.get_game_state()
        ball = game_state['ball']
        ball['x'] += ball['vx']
        ball['y'] += ball['vy']

        if ball['y'] - ball['radius'] <= 0 or ball['y'] + ball['radius'] >= 400:
            ball['vy'] *= -1

        if await self.check_paddle_collision(game_state, 'player1') or await self.check_paddle_collision(game_state, 'player2'):
            ball['vx'] *= -1

        if ball['x'] - ball['radius'] <= 0:
            game_state['score']['player2'] += 1
            await self.reset_ball(game_state)
        elif ball['x'] + ball['radius'] >= 600:
            game_state['score']['player1'] += 1
            await self.reset_ball(game_state)

        # Check if a player reached a score of 4 to end the match
        if game_state['score']['player1'] >= 4:
            await self.end_match('player1', game_state)
        elif game_state['score']['player2'] >= 4:
            await self.end_match('player2', game_state)

        await self.set_game_state(game_state)

    async def check_paddle_collision(self, game_state, player):
        paddle = game_state[player]
        ball = game_state['ball']
        return (
            paddle['x'] < ball['x'] < paddle['x'] + paddle['width'] and paddle['y'] < ball['y'] < paddle['y'] + paddle['height']
        )

    async def reset_ball(self, game_state):
        ball = game_state['ball']
        ball['x'], ball['y'] = 300, 200
        ball['vx'], ball['vy'] = random.choice([-3, 3]), random.choice([-3, 3])
        await self.set_game_state(game_state)

    async def reset_game(self):
        game_state = {
            'player1': {'x': 50, 'y': 150, 'width': 10, 'height': 100, 'speed': 20},
            'player2': {'x': 540, 'y': 150, 'width': 10, 'height': 100, 'speed': 20},
            'ball': {'x': 300, 'y': 200, 'radius': 10, 'vx': 3, 'vy': 3},
            'score': {'player1': 0, 'player2': 0},
        }
        await self.set_game_state(game_state)

    async def end_match(self, winner, game_state):
        # Update the winner in game state
        game_state['winner'] = winner

        # Save the match history in the database asynchronously
        await self.save_match_history(winner, game_state)

        # Stop the ball and notify players
        self.is_ball_moving = False
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'match_ended',
                'winner': winner,
                'score': game_state['score']
            }
        )

    async def match_ended(self, event):
        # Send match result to WebSocket
        await self.send(text_data=json.dumps({
            'matchEnded': True,
            'winner': event['winner'],
            'score': event['score']
        }))

    # Asynchronously save match history to the database
    @database_sync_to_async
    def save_match_history(self, winner, game_state):
        try:
            room = Room.objects.get(room_id=self.room_code)
            room.winner = winner
            room.score_player1 = game_state['score']['player1']
            room.score_player2 = game_state['score']['player2']
            room.save()  # Save the updated Room object
        except Room.DoesNotExist:
            print(f"Room with code {self.room_code} does not exist.")


    # Redis helpers using Django's cache system
    async def get_game_state(self):
        return cache.get(f"game_state_{self.room_code}")

    async def set_game_state(self, game_state):
        cache.set(f"game_state_{self.room_code}", game_state)

    async def get_players(self):
        return cache.get(f"players_{self.room_group_name}") or []

    async def set_players(self, players):
        cache.set(f"players_{self.room_group_name}", players)

    async def get_room(self):
        # Fetch the room object from the database
        return await sync_to_async(Room.objects.get)(room_id=self.room_code)
