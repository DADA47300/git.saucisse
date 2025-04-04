import sys
from time import sleep
from itertools import combinations
from PodSixNet.Server import Server
from PodSixNet.Channel import Channel

# Dimensions du plateau de jeu (pour la validation des coups)
COLONNES = 9
LIGNES = 7

# --- Classe ClientChannel ---
# Gère la connexion individuelle d'un client avec le serveur.
class ClientChannel(Channel):
    nickname = "anonymous"  # Pseudo par défaut

    def Close(self):
        """
        Méthode appelée lorsque le client se déconnecte.
        Le serveur retire le joueur de la liste.
        """
        self._server.remove_player(self)

    def Network_nickname(self, data):
        """
        Reçoit et définit le pseudo du joueur,
        puis met à jour l'affichage du lobby côté serveur.
        """
        self.nickname = data["nickname"]
        self._server.set_player_nickname(self, self.nickname)

    def Network_challenge(self, data):
        """
        Reçoit une demande de défi envoyée par un client et la transmet au serveur.
        """
        target = data["target"]
        self._server.handle_challenge(self, target)

    def Network_challenge_response(self, data):
        """
        Reçoit la réponse à un défi (accept ou decline) et la transmet au serveur.
        """
        challenger = data["challenger"]
        response = data["response"]
        self._server.handle_challenge_response(self, challenger, response)

    def Network_ovals(self, data):
        """
        Reçoit les coordonnées des points joués lors d'une partie
        et les transmet au serveur pour traitement.
        """
        self._server.handle_ovals(self, data["ovals"])

    def Network_abandon(self, data):
        self._server.handle_abandon(self)

# --- Classe MyServer ---
# Gère l'ensemble des joueurs, les demandes de défi et le déroulement des parties.
class MyServer(Server):
    channelClass = ClientChannel  # Utilise ClientChannel pour la communication

    def __init__(self, localaddr):
        Server.__init__(self, localaddr=localaddr)
        # Liste des joueurs sous forme de dictionnaires :
        # { "channel": <Channel>, "nickname": str, "score": int, "inGame": bool, "eliminated": bool, "color": str }
        self.players = []
        # Liste des parties actives, chaque partie est un dictionnaire :
        # { "p1": idx, "p2": idx, "board": board, "currentPlayer": idx }
        self.games = []
        print("[SERVER] Server launched")
        self.update_lobby()

    # --- Gestion des joueurs ---

    def Connected(self, channel, addr):
        """Méthode appelée lors d'une nouvelle connexion d'un client."""
        print(f"[SERVER] New connection from {addr}")
        self.add_new_player(channel)

    def add_new_player(self, channel):
        """Ajoute un nouveau joueur à la liste des joueurs et met à jour le lobby."""
        self.players.append({
            "channel": channel,
            "nickname": channel.nickname,
            "score": 1000,
            "inGame": False,
            "eliminated": False,
            "color": None
        })
        self.update_lobby()

    def remove_player(self, channel):
        """
        Retire un joueur de la liste lors de la déconnexion.
        Si le joueur était en partie, la partie est terminée et l'adversaire est déclaré vainqueur.
        """
        idx = self.get_player_index(channel)
        if idx is not None:
            game = self.get_game_for_channel(channel)
            if game:
                # Identification de l'adversaire pour terminer la partie
                other = game["p1"] if game["p2"] == idx else game["p2"]
                self.send_to_game(game, {"action": "game_over", "winner": self.players[other]["nickname"]})
                self.end_game(game)
            print(f"[SERVER] Removing player {self.players[idx]['nickname']}")
            self.players.pop(idx)
        self.update_lobby()

    def get_player_index(self, channel):
        """Renvoie l'indice du joueur dans la liste en fonction du canal."""
        for i, p in enumerate(self.players):
            if p["channel"] == channel:
                return i
        return None

    def set_player_nickname(self, channel, nickname):
        """
        Met à jour le pseudo d'un joueur et rafraîchit le lobby.
        """
        idx = self.get_player_index(channel)
        if idx is not None:
            self.players[idx]["nickname"] = nickname
        self.update_lobby()

    # --- Gestion du Lobby ---
    def update_lobby(self):
    # Construire la liste des joueurs disponibles (non en partie)
        lobby_list = []
        for p in self.players:
            if not p["inGame"]:
                lobby_list.append({"nickname": p["nickname"], "score": p["score"]})
        
        # Calculer le leaderboard en triant tous les joueurs par score décroissant
        sorted_players = sorted(self.players, key=lambda p: p["score"], reverse=True)
        leaderboard_list = [{"nickname": p["nickname"], "score": p["score"]} for p in sorted_players[:3]]
        
        # Envoyer le message à chaque joueur non engagé
        for p in self.players:
            if not p["inGame"]:
                p["channel"].Send({
                    "action": "lobby_update",
                    "players": lobby_list,
                    "my_score": p["score"],
                    "leaderboard": leaderboard_list
                })

    # --- Gestion des demandes de défi ---
    def handle_challenge(self, challenger_channel, target_nickname):
        """
        Gère la demande de défi d'un joueur (challenger) envers un autre joueur (cible).
        Vérifie la disponibilité et la compatibilité des scores avant d'envoyer la demande.
        """
        challenger_idx = self.get_player_index(challenger_channel)
        target_idx = None
        for i, p in enumerate(self.players):
            if p["nickname"] == target_nickname and not p["inGame"] and not p["eliminated"]:
                target_idx = i
                break
        if target_idx is None:
            challenger_channel.Send({"action": "error", "message": "Le joueur ciblé n'est pas disponible."})
            return
        challenger_score = self.players[challenger_idx]["score"]
        target_score = self.players[target_idx]["score"]
        diff = abs(challenger_score - target_score)
        if diff > 300:
            challenger_channel.Send({"action": "error", "message": "Écart de score trop élevé."})
            return
        # Si l'écart est inférieur à 200, le défi est forcé
        forced = diff < 200
        self.players[target_idx]["channel"].Send({
            "action": "challenge_request",
            "from": self.players[challenger_idx]["nickname"],
            "from_score": challenger_score,
            "target_score": target_score,
            "forced": forced
        })

    def handle_challenge_response(self, challenged_channel, challenger_nickname, response):
        """
        Gère la réponse à une demande de défi.
        En cas d'acceptation, lance une partie. Sinon, notifie le challenger.
        """
        challenged_idx = self.get_player_index(challenged_channel)
        challenger_idx = None
        for i, p in enumerate(self.players):
            if p["nickname"] == challenger_nickname:
                challenger_idx = i
                break
        if challenger_idx is None:
            challenged_channel.Send({"action": "error", "message": "Le joueur ayant envoyé le défi est introuvable."})
            return
        if response == "accept":
            self.start_game(challenger_idx, challenged_idx)
        else:
            self.players[challenger_idx]["channel"].Send({
                "action": "challenge_declined",
                "target": self.players[challenged_idx]["nickname"]
            })
        self.update_lobby()

    # --- Gestion des parties (match) ---
    def start_game(self, p1Index, p2Index):
        """
        Initialise une nouvelle partie entre deux joueurs.
        Le challenger reçoit la couleur "red" et commence, l'autre reçoit "green".
        """
        self.players[p1Index]["inGame"] = True
        self.players[p2Index]["inGame"] = True
        self.players[p1Index]["color"] = "red"
        self.players[p2Index]["color"] = "green"
        # Création d'un plateau virtuel pour la partie (les cases non jouables sont marquées "N/A")
        board = [[None if (col+ligne)%2==0 else "N/A" for ligne in range(LIGNES)] for col in range(COLONNES)]
        game = {
            "p1": p1Index,
            "p2": p2Index,
            "board": board,
            "currentPlayer": p1Index
        }
        self.games.append(game)
        self.players[p1Index]["channel"].Send({
            "action": "start_game",
            "set_color": "red",
            "your_turn": True,
            "opponent": self.players[p2Index]["nickname"]
        })
        self.players[p2Index]["channel"].Send({
            "action": "start_game",
            "set_color": "green",
            "your_turn": False,
            "opponent": self.players[p1Index]["nickname"]
        })
        self.update_lobby()

    def get_game_for_channel(self, channel):
        """
        Renvoie la partie en cours dans laquelle le joueur est impliqué,
        ou None s'il n'est pas en jeu.
        """
        idx = self.get_player_index(channel)
        for game in self.games:
            if game["p1"] == idx or game["p2"] == idx:
                return game
        return None

    def handle_ovals(self, channel, points):
        """
        Gère le coup joué par un joueur (les points sélectionnés) :
         - Vérifie que c'est bien son tour
         - Met à jour le plateau de jeu virtuel
         - Envoie l'information à l'adversaire
         - Passe le tour au joueur suivant
        """
        game = self.get_game_for_channel(channel)
        if not game:
            return
        player_idx = self.get_player_index(channel)
        if player_idx != game["currentPlayer"]:
            channel.Send({"action": "error", "message": "Ce n'est pas votre tour."})
            return
        color = self.players[player_idx]["color"]
        board = game["board"]
        for (col, ligne) in points:
            if board[col][ligne] is None:
                board[col][ligne] = color
        self.send_to_game(game, {
            "action": "ovals",
            "ovals": points,
            "who": self.players[player_idx]["nickname"],
            "color": color
        })
        self.next_turn(game)

    def next_turn(self, game):
        """
        Passe le tour au joueur adverse.
        Vérifie également s'il reste des mouvements valides,
        sinon déclare le gagnant.
        """
        p1 = game["p1"]
        p2 = game["p2"]
        current = game["currentPlayer"]
        other = p2 if current == p1 else p1
        game["currentPlayer"] = other
        if not self.has_valid_move(game["board"]):
            # Si aucun mouvement valide n'est possible pour l'adversaire,
            # le joueur précédent gagne la partie
            winner_idx = current
            loser_idx = other
            self.declare_winner(game, winner_idx, loser_idx)
        else:
            self.players[other]["channel"].Send({
                "action": "your_turn",
                "opponent": self.players[current]["nickname"]
            })
            self.players[current]["channel"].Send({
                "action": "opponent_turn",
                "opponent": self.players[other]["nickname"]
            })

    def has_valid_move(self, board):
        """
        Vérifie si le plateau possède encore une combinaison de 3 points
        formant une configuration valide (dans une zone de 3x3).
        """
        free = []
        for col in range(COLONNES):
            for ligne in range(LIGNES):
                if board[col][ligne] is None:
                    free.append((col, ligne))
        if len(free) < 3:
            return False
        # Vérifie toutes les combinaisons possibles de 3 points libres
        for combo in combinations(free, 3):
            cols = [p[0] for p in combo]
            lignes = [p[1] for p in combo]
            if (max(cols) - min(cols) <= 2) and (max(lignes) - min(lignes) <= 2):
                return True
        return False

    def declare_winner(self, game, winner_idx, loser_idx):
        """
        Déclare le gagnant de la partie, met à jour les scores et termine la partie.
        """
        winner_name = self.players[winner_idx]["nickname"]
        self.send_to_game(game, {"action": "game_over", "winner": winner_name})
        self.update_scores(winner_idx, loser_idx)
        self.end_game(game)

    def update_scores(self, winner_idx, loser_idx):
        """
        Met à jour les scores des joueurs après une partie.
        Le gagnant gagne un certain nombre de points, et le perdant les perd.
        """
        score_w = self.players[winner_idx]["score"]
        score_l = self.players[loser_idx]["score"]
        diff = abs(score_w - score_l)
        gain = 100 + diff // 3
        self.players[winner_idx]["score"] += gain
        self.players[loser_idx]["score"] -= gain
        print(f"[SERVER] Score update: {self.players[winner_idx]['nickname']} +{gain}, {self.players[loser_idx]['nickname']} -{gain}")

    def handle_abandon(self, channel):
        game = self.get_game_for_channel(channel)
        if game:
            player_idx = self.get_player_index(channel)
            # Identifie l'adversaire
            opponent_idx = game["p1"] if game["p2"] == player_idx else game["p2"]
            # Envoie un message indiquant la fin de la partie, avec l'adversaire déclaré vainqueur
            self.send_to_game(game, {"action": "game_over", "winner": self.players[opponent_idx]["nickname"]})
            self.update_scores(opponent_idx, player_idx)
            # Termine la partie
            self.end_game(game)

    def end_game(self, game):
        """
        Termine la partie en réinitialisant l'état des joueurs et en retirant la partie de la liste.
        """
        for idx in [game["p1"], game["p2"]]:
            if not self.players[idx]["eliminated"]:
                self.players[idx]["inGame"] = False
            self.players[idx]["color"] = None
        if game in self.games:
            self.games.remove(game)
        self.update_lobby()

    def send_to_game(self, game, data):
        """
        Envoie un message à tous les joueurs impliqués dans une partie.
        """
        for idx in [game["p1"], game["p2"]]:
            self.players[idx]["channel"].Send(data)

    def Launch(self):
        """Boucle principale du serveur qui traite les messages entrants."""
        while True:
            self.Pump()
            sleep(0.001)

if __name__ == "__main__":
    # Vérifie les arguments pour la connexion du serveur
    if len(sys.argv) != 2:
        print(f"Usage: python3 {sys.argv[0]} host:port")
        host, port = "localhost", "31425"
    else:
        host, port = sys.argv[1].split(":")
    s = MyServer((host, int(port)))
    s.Launch()
