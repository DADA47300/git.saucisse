import sys
from time import sleep
from itertools import combinations
from PodSixNet.Server import Server
from PodSixNet.Channel import Channel

# Constantes du plateau
COLONNES = 9
LIGNES = 7

class ClientChannel(Channel):
    nickname = "anonymous"

    def Close(self):
        self._server.DelPlayer(self)

    def Network_nickname(self, data):
        self.nickname = data["nickname"]
        self._server.PrintPlayers()
        # Dès qu'un joueur se connecte, on lui envoie sa couleur (s'il est assigné)
        # (L'assignation se fait dans MyServer.AddPlayer)

    def Network_ovals(self, data):
        """
        Le client envoie la liste de points formant sa "saucisse".
        On met à jour le plateau, on retransmet le coup à tous les joueurs,
        et on passe au tour suivant après vérification.
        """
        print(f"[SERVER] {self.nickname} played ovals: {data['ovals']}")
        idx = self._server.get_player_index(self)
        if idx is None:
            return
        player_color = self._server.players[idx]["color"]
        # Met à jour le plateau pour chaque point joué
        for (col, ligne) in data["ovals"]:
            if (col + ligne) % 2 == 0 and self._server.board[col][ligne] is None:
                self._server.board[col][ligne] = player_color
        # Retransmet à tous le coup joué
        self._server.SendToAll({
            "action": "ovals",
            "ovals": data["ovals"],
            "who": self.nickname,
            "color": player_color
        })
        # Passe au tour suivant et vérifie si le joueur suivant a un coup possible
        self._server.next_turn()

class MyServer(Server):
    channelClass = ClientChannel

    def __init__(self, mylocaladdr):
        Server.__init__(self, localaddr=mylocaladdr)
        self.players = []  # Liste de dicts : {"channel": <Channel>, "color": "red" ou "green"}
        self.current_player_index = 0
        # Initialisation du plateau : seules les cases jouables ((col+ligne)%2==0) sont à None
        self.board = [
            [None if (col + ligne) % 2 == 0 else "N/A" for ligne in range(LIGNES)]
            for col in range(COLONNES)
        ]
        print("[SERVER] Server launched")

    def Connected(self, channel, addr):
        self.AddPlayer(channel)

    def AddPlayer(self, player):
        """
        Assigne la couleur selon l'ordre d'arrivée et stocke le joueur.
        Dès que 2 joueurs sont connectés, la partie démarre.
        """
        print("[SERVER] New Player connected")
        color = "red" if len(self.players) == 0 else "green"
        self.players.append({
            "channel": player,
            "color": color
        })
        # Envoie la couleur assignée au joueur
        player.Send({"action": "set_color", "color": color})
        if len(self.players) == 2:
            self.StartGame()

    def PrintPlayers(self):
        print("[SERVER] Players' nicknames:", [p["channel"].nickname for p in self.players])

    def DelPlayer(self, player):
        print("[SERVER] Deleting Player " + player.nickname + " at " + str(player.addr))
        idx = self.get_player_index(player)
        if idx is not None:
            self.players.pop(idx)

    def get_player_index(self, channel):
        for i, p in enumerate(self.players):
            if p["channel"] == channel:
                return i
        return None

    def StartGame(self):
        """
        Démarre la partie en donnant la main au premier joueur.
        """
        self.current_player_index = 0
        first_player = self.players[self.current_player_index]["channel"]
        first_player.Send({"action": "your_turn"})
        print("[SERVER] Game started. It's", self.players[self.current_player_index]["channel"].nickname, "turn.")

    def next_turn(self):
        """
        Passe la main à l'autre joueur et vérifie automatiquement si ce dernier
        a au moins un coup possible. Sinon, le joueur adverse gagne.
        """
        self.current_player_index = 1 - self.current_player_index
        if not self.has_valid_move():
            winning_idx = 1 - self.current_player_index
            winner = self.players[winning_idx]["channel"].nickname
            self.SendToAll({"action": "game_over", "winner": winner})
            print(f"[SERVER] No valid move for {self.players[self.current_player_index]['channel'].nickname}. {winner} wins!")
        else:
            next_player = self.players[self.current_player_index]["channel"]
            next_player.Send({"action": "your_turn"})
            print("[SERVER] It's now", next_player.nickname, "turn.")

    def has_valid_move(self):
        """
        Vérifie s'il existe une combinaison de 3 cases libres jouables formant une saucisse valide.
        Une case jouable est une case dont (col+ligne)%2 == 0 et non occupée (None).
        """
        free = []
        for col in range(COLONNES):
            for ligne in range(LIGNES):
                if (col + ligne) % 2 == 0 and self.board[col][ligne] is None:
                    free.append((col, ligne))
        if len(free) < 3:
            return False
        for combo in combinations(free, 3):
            cols = [p[0] for p in combo]
            lignes = [p[1] for p in combo]
            if max(cols) - min(cols) <= 2 and max(lignes) - min(lignes) <= 2:
                return True
        return False

    def SendToAll(self, data):
        for p in self.players:
            p["channel"].Send(data)

    def Launch(self):
        while True:
            self.Pump()
            sleep(0.001)

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python3", sys.argv[0], "host:port")
        host, port = "localhost", "31425"
    else:
        host, port = sys.argv[1].split(":")
    s = MyServer((host, int(port)))
    s.Launch()
