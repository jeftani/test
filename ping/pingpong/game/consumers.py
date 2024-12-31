import json
import random
import asyncio
from channels.generic.websocket import AsyncWebsocketConsumer

class PingPongGameConsumer(AsyncWebsocketConsumer):
    players = {}  # Tracks connected players by channel_name
    shared_game_state = {
        'player1': {'x': 50, 'y': 150, 'width': 10, 'height': 100, 'speed': 20},
        'player2': {'x': 540, 'y': 150, 'width': 10, 'height': 100, 'speed': 20},
        'ball': {'x': 300, 'y': 200, 'radius': 10, 'vx': 3, 'vy': 3},
        'score': {'player1': 0, 'player2': 0},
    }
    is_ball_moving = False

    async def connect(self):

        # Extract the room code from the scope
        self.room_code = self.scope['url_route']['kwargs']['room_code']
        self.room_group_name = f"game_{self.room_code}"
        
        # Add the WebSocket connection to the room group
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )

        await self.accept()

        # Assign the player role (Player 1 or Player 2)
        if len(self.players.get(self.room_group_name, [])) < 2:
            self.players.setdefault(self.room_group_name, []).append(self.channel_name)
            player_role = 'player1' if len(self.players[self.room_group_name]) == 1 else 'player2'
            await self.send(text_data=json.dumps({'role': player_role}))
        else:
            # Additional connections become spectators
            await self.send(text_data=json.dumps({'role': 'spectator'}))

        # Send the current game state
        await self.send_game_state()

        # Start ball movement if two players are connected and it hasn't started
        if len(self.players[self.room_group_name]) == 2 and not self.is_ball_moving:
            self.is_ball_moving = True
            asyncio.create_task(self.ball_movement_loop())

    async def disconnect(self, close_code):
        # Remove player from the players list
        if self.channel_name in self.players.get(self.room_group_name, []):
            self.players[self.room_group_name].remove(self.channel_name)

        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )

        # Reset the game state if all players disconnect
        if not self.players[self.room_group_name]:
            self.is_ball_moving = False
            self.reset_game()

    async def receive(self, text_data):
        data = json.loads(text_data)
        action = data.get('action', '')
        player_role = data.get('role', '')

        if action == 'move_up' or action == 'move_down':
            self.update_player_position(player_role, action)

        # Broadcast the updated state
        await self.send_game_state()

    async def send_game_state(self):
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'game_update',
                'game_state': self.shared_game_state,
            }
        )

    async def game_update(self, event):
        # Send updated game state to WebSocket
        await self.send(text_data=json.dumps({'gameState': event['game_state']}))

    async def ball_movement_loop(self):
        while self.is_ball_moving:
            self.update_ball_position()
            await self.send_game_state()
            await asyncio.sleep(0.03)

    def update_player_position(self, player, action):
        if player == 'player1':
            if action == 'move_up' and self.shared_game_state['player1']['y'] > 0:
                self.shared_game_state['player1']['y'] -= self.shared_game_state['player1']['speed']
            elif action == 'move_down' and self.shared_game_state['player1']['y'] < 400 - self.shared_game_state['player1']['height']:
                self.shared_game_state['player1']['y'] += self.shared_game_state['player1']['speed']
        elif player == 'player2':
            if action == 'move_up' and self.shared_game_state['player2']['y'] > 0:
                self.shared_game_state['player2']['y'] -= self.shared_game_state['player2']['speed']
            elif action == 'move_down' and self.shared_game_state['player2']['y'] < 400 - self.shared_game_state['player2']['height']:
                self.shared_game_state['player2']['y'] += self.shared_game_state['player2']['speed']

    def update_ball_position(self):
        ball = self.shared_game_state['ball']
        ball['x'] += ball['vx']
        ball['y'] += ball['vy']

        # Handle ball collisions with walls
        if ball['y'] - ball['radius'] <= 0 or ball['y'] + ball['radius'] >= 400:
            ball['vy'] *= -1

        # Handle ball collisions with paddles
        if self.check_paddle_collision('player1') or self.check_paddle_collision('player2'):
            ball['vx'] *= -1

        # Handle scoring
        if ball['x'] - ball['radius'] <= 0:
            self.shared_game_state['score']['player2'] += 1
            self.reset_ball()
        elif ball['x'] + ball['radius'] >= 600:
            self.shared_game_state['score']['player1'] += 1
            self.reset_ball()

    def check_paddle_collision(self, player):
        paddle = self.shared_game_state[player]
        ball = self.shared_game_state['ball']
        return (
            paddle['x'] < ball['x'] < paddle['x'] + paddle['width'] and paddle['y'] < ball['y'] < paddle['y'] + paddle['height']
        )

    def reset_ball(self):
        ball = self.shared_game_state['ball']
        ball['x'], ball['y'] = 300, 200
        ball['vx'], ball['vy'] = random.choice([-3, 3]), random.choice([-3, 3])

    def reset_game(self):
        self.shared_game_state = {
            'player1': {'x': 50, 'y': 150, 'width': 10, 'height': 100, 'speed': 20},
            'player2': {'x': 540, 'y': 150, 'width': 10, 'height': 100, 'speed': 20},
            'ball': {'x': 300, 'y': 200, 'radius': 10, 'vx': 3, 'vy': 3},
            'score': {'player1': 0, 'player2': 0},
        }
