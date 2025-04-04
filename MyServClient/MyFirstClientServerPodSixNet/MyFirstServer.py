import sys
from time import sleep
from PodSixNet.Server import Server
from PodSixNet.Channel import Channel

COLONNES = 9
LIGNES = 7

class ClientChannel(Channel):
    nickname = "anonymous"

    def Close(self):
        self._server.DelPlayer(self)

    def Network_newPoint(self, data):
        print(f"Player {self.nickname} played at {data['newPoint']}")
        self._server.process_move(self, data)  # Handle the move on the server side

    def Network_nickname(self, data):
        self.nickname = data["nickname"]
        self._server.PrintPlayers()
        self.Send({"action": "start", "game_state": self._server.game_state})  # Send game state to the player

class MyServer(Server):
    channelClass = ClientChannel

    def __init__(self, mylocaladdr):
        Server.__init__(self, localaddr=mylocaladdr)
        self.players = []
        self.game_state = {
            'board': [[None for _ in range(LIGNES)] for _ in range(COLONNES)],  # Board state
            'current_player': 1,  # Player 1 starts
            'saucisse_posee': {1: False, 2: False}
        }
        print('Server launched')

    def Connected(self, channel, addr):
        self.AddPlayer(channel)

    def AddPlayer(self, player):
        print("New Player connected")
        self.players.append(player)
        if len(self.players) == 2:  # Start the game when two players are connected
            self.StartGame()

    def PrintPlayers(self):
        print("players' nicknames :", [p.nickname for p in self.players])

    def DelPlayer(self, player):
        print("Deleting Player " + player.nickname + " at " + str(player.addr))
        self.players.remove(player)

    def StartGame(self):
        """Start the game by notifying both players."""
        for player in self.players:
            player.Send({"action": "start", "game_state": self.game_state})  # Send the game state to both players

    def process_move(self, player, data):
        """Process the move made by the player."""
        # Get the move and validate
        col, ligne = data["newPoint"]
        if self.game_state['board'][col][ligne] is None:  # If the spot is empty
            self.game_state['board'][col][ligne] = self.game_state['current_player']  # Set the move
            self.game_state['saucisse_posee'][self.game_state['current_player']] = True
            self.game_state['current_player'] = 2 if self.game_state['current_player'] == 1 else 1
            # Notify all players of the move
            self.SendToAll({"action": "update_board", "game_state": self.game_state})
            # Check if the game is over
            self.check_winner()

    def check_winner(self):
        """Check if there is a winner or if the game ends."""
        for player in self.players:
            if all([self.game_state['board'][col][ligne] == player for col in range(COLONNES) for ligne in range(LIGNES)]):
                self.SendToAll({"action": "game_over", "winner": player.nickname})

    def SendToAll(self, data):
        """Send data to all connected players."""
        for player in self.players:
            player.Send(data)

    def Launch(self):
        while True:
            self.Pump()
            sleep(0.001)

if len(sys.argv) != 2:
    print("Please use: python3", sys.argv[0], "host:port")
    host, port = "localhost", "31425"
else:
    host, port = sys.argv[1].split(":")
s = MyServer((host, int(port)))
s.Launch()
