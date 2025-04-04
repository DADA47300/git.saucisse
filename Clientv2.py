import sys
from time import sleep
from tkinter import *
from tkinter import messagebox
from PodSixNet.Connection import connection, ConnectionListener

# Constantes du plateau de jeu
RADIUS = 20           # Rayon des points circulaires du plateau
XMIN = 30             # Décalage horizontal minimal du plateau
YMIN = 30             # Décalage vertical minimal du plateau
DIST = 50             # Distance entre les points
COLONNES = 9          # Nombre de colonnes du plateau
LIGNES = 7            # Nombre de lignes du plateau
WIDTH = 2 * XMIN + 8 * DIST   # Largeur totale du canvas
HEIGHT = 2 * YMIN + 6 * DIST  # Hauteur totale du canvas

# --- Classe Board --- 
# Représente le plateau de jeu sur lequel les joueurs vont sélectionner des points.
class Board:
    def __init__(self, canvas, client):
        self.canvas = canvas          # Canvas tkinter pour le dessin
        self.client = client          # Référence vers le client pour les échanges réseau
        # Matrice pour stocker les points du plateau
        self.point = [[None for _ in range(LIGNES)] for _ in range(COLONNES)]
        self.selected_points = []     # Liste des points actuellement sélectionnés par le joueur
        self.occupied_points = set()  # Ensemble des points déjà occupés (joués)
        self.my_color = None          # Couleur assignée par le serveur ("red" ou "green")
        self.can_play = False         # Indique si c'est le tour du joueur
        self.draw_board()             # Dessine le plateau dès l'initialisation

    def draw_board(self):
        """Dessine le plateau de jeu en créant des cercles pour les cases jouables."""
        for col in range(COLONNES):
            for ligne in range(LIGNES):
                # Les cases jouables sont définies par une alternance (pour un effet visuel)
                if (col + ligne) % 2 == 0:
                    idPoint = self.canvas.create_oval(
                        XMIN + col * DIST - RADIUS,
                        YMIN + ligne * DIST - RADIUS,
                        XMIN + col * DIST + RADIUS,
                        YMIN + ligne * DIST + RADIUS,
                        fill="blue", tags=f"point_{col}_{ligne}"
                    )
                    self.point[col][ligne] = (idPoint, col, ligne)
                    # Association d'un clic sur le cercle pour sélectionner le point
                    self.canvas.tag_bind(
                        idPoint, "<Button-1>",
                        lambda event, c=col, l=ligne: self.select_point(c, l)
                    )
                else:
                    self.point[col][ligne] = None

    def select_point(self, col, ligne):
        """Gère la sélection d'un point sur le plateau par le joueur."""
        if not self.can_play:  # Si ce n'est pas le tour, on ne fait rien
            return
        if (col, ligne) in self.occupied_points:  # Le point est déjà occupé
            return
        if (col, ligne) not in self.selected_points:
            self.selected_points.append((col, ligne))
            # Utilise self.my_color s'il est défini, sinon une couleur de prévisualisation ("grey")
            preview_color = self.my_color if self.my_color is not None else "grey"
            self.canvas.itemconfig(self.point[col][ligne][0], fill=preview_color)
        # Dès que trois points sont sélectionnés, on vérifie leur validité
        if len(self.selected_points) == 3:
            if self.is_valid_sausage():
                # Si la configuration est valide, dessiner la "saucisse" (les traits entre points)
                self.draw_sausage(self.selected_points, self.my_color if self.my_color else "grey")
                self.occupied_points.update(self.selected_points)
                # Envoi des coordonnées des points au serveur
                connection.Send({"action": "ovals", "ovals": self.selected_points})
            else:
                # Si la sélection n'est pas valide, réinitialiser les points en les remettant en bleu
                for c, l in self.selected_points:
                    self.canvas.itemconfig(self.point[c][l][0], fill="blue")
            self.selected_points = []  # Réinitialise la sélection

    def is_valid_sausage(self):
        """
        Vérifie si les trois points sélectionnés forment une configuration valide.
        La condition ici est que les points doivent être contenus dans une zone de 3x3 (écart max de 2).
        """
        cols = [p[0] for p in self.selected_points]
        lignes = [p[1] for p in self.selected_points]
        return (max(cols) - min(cols) <= 2) and (max(lignes) - min(lignes) <= 2)

    def draw_sausage(self, points, color):
        """
        Dessine des lignes entre les points pour représenter visuellement une "saucisse".
        On relie les deux premiers points puis le deuxième au troisième.
        """
        for i in range(2):
            self.canvas.create_line(
                XMIN + points[i][0] * DIST,
                YMIN + points[i][1] * DIST,
                XMIN + points[i+1][0] * DIST,
                YMIN + points[i+1][1] * DIST,
                width=5, fill=color
            )

    def draw_sausage_points(self, points, color):
        """
        Met à jour le plateau pour indiquer que certains points sont désormais occupés
        et dessine la saucisse correspondante.
        """
        for (col, ligne) in points:
            self.occupied_points.add((col, ligne))
            self.canvas.itemconfig(self.point[col][ligne][0], fill=color)
        self.draw_sausage(points, color)

    def reset(self):
        """Réinitialise le plateau en supprimant toutes les formes et en redessinant le plateau."""
        self.canvas.delete("all")
        self.selected_points = []
        self.occupied_points = set()
        self.draw_board()
        self.can_play = False

# --- Interface Lobby ---
# Affiche la liste des joueurs dans le lobby et permet de lancer des défis.
class LobbyFrame(Frame):
    def __init__(self, master, client):
        Frame.__init__(self, master)
        self.client = client 
        self.player_list_frame = Frame(self)
        self.player_list_frame.pack(fill=BOTH, expand=True)
        self.pack(fill=BOTH, expand=True)

    def update_lobby(self, players, my_score, leaderboard):
        # Effacer tous les widgets actuels dans le lobby
        for widget in self.player_list_frame.winfo_children():
            widget.destroy()
        
        # Créer et afficher le leaderboard en haut du lobby
        leaderboard_text = "Leaderboard:\n"
        for i, player in enumerate(leaderboard):
            leaderboard_text += f"{i+1}. {player['nickname']} ({player['score']})\n"
        lb_label = Label(self.player_list_frame, text=leaderboard_text,
                         bg="lightgrey", font=("Helvetica", 12, "bold"))
        lb_label.pack(fill=X, padx=5, pady=5)
        
        # Afficher la liste des joueurs disponibles pour lancer un défi
        for player in players:
            if player["nickname"] == self.client.nickname:
                continue
            diff = abs(my_score - player["score"])
            color = "green" if diff <= 300 else "red"
            btn = Button(self.player_list_frame,
                         text=f"{player['nickname']} ({player['score']})",
                         bg=color,
                         command=lambda p=player: self.challenge_player(p))
            btn.pack(fill=X, padx=5, pady=2)

    def challenge_player(self, player):
        """
        Lance une demande de défi si l'écart de score est acceptable.
        Sinon, affiche un message informatif.
        """
        diff = abs(self.client.my_score - player["score"])
        if diff <= 300:
            self.client.send_challenge(player["nickname"])
        else:
            messagebox.showinfo("Challenge", "Cet adversaire n'est pas compatible.")

# --- Interface Game ---
# Gère l'affichage du jeu (le plateau de jeu) et sa réinitialisation.
class GameFrame(Frame):
    def __init__(self, master, client):
        Frame.__init__(self, master)
        self.client = client
        self.canvas = Canvas(self, width=WIDTH, height=HEIGHT, bg="white")
        self.canvas.pack()
        self.board = Board(self.canvas, client)
        abandon_but = Button(self, text="Abandonner", command=master.abandon_game)
        abandon_but.pack(side=BOTTOM)

        self.pack(fill=BOTH, expand=True)

    def reset(self):
        """Réinitialise le canvas et le plateau de jeu."""
        self.canvas.delete("all")
        self.board.reset()

# --- Client réseau ---
# Gère la communication avec le serveur et les réponses aux événements réseau.
class Client(ConnectionListener):
    def __init__(self, host, port, lobby_callback, game_callback, nickname):
        self.lobby_callback = lobby_callback  # Fonction de rappel pour mettre à jour le lobby
        self.game_callback = game_callback    # Fonction de rappel pour passer en mode jeu
        self.nickname = nickname              # Pseudo du joueur
        self.my_score = 1000                  # Score initial du joueur
        self.Connect((host, int(port)))       # Connexion au serveur
        self.state = "ACTIVE"                 # État du client
        # Envoi du pseudo au serveur dès la connexion
        connection.Send({"action": "nickname", "nickname": nickname})

    def Loop(self):
        """Boucle principale pour gérer la communication réseau."""
        connection.Pump()
        self.Pump()

    def send_challenge(self, target_nickname):
        """Envoie une demande de défi à un joueur ciblé."""
        connection.Send({"action": "challenge", "target": target_nickname})

    def send_abandon(self):
        from PodSixNet.Connection import connection
        connection.Send({"action": "abandon"})

    def Network_lobby_update(self, data):
        """
        Reçoit la mise à jour du lobby depuis le serveur,
        met à jour le score et affiche la liste des joueurs.
        """
        self.my_score = data.get("my_score", self.my_score)
        # On passe maintenant aussi data["leaderboard"] au callback du lobby
        self.lobby_callback(data["players"], self.my_score, data.get("leaderboard", []))

    def Network_challenge_request(self, data):
        """
        Reçoit une demande de défi depuis un autre joueur.
        Si le défi est forcé, la réponse est automatique,
        sinon on demande confirmation à l'utilisateur.
        """
        challenger = data["from"]
        challenger_score = data["from_score"]
        target_score = data["target_score"]
        forced = data["forced"]
        if forced:
            response = "accept"
        else:
            res = messagebox.askquestion("Demande de défi", f"{challenger} ({challenger_score}) vous propose un défi. Acceptez-vous ?")
            response = "accept" if res=="yes" else "decline"
        connection.Send({"action": "challenge_response", "challenger": challenger, "response": response})

    def Network_challenge_declined(self, data):
        """Notifie l'utilisateur que son défi a été refusé."""
        target = data["target"]
        messagebox.showinfo("Challenge", f"{target} a refusé votre défi.")

    def Network_start_game(self, data):
        """Lance la partie en définissant la couleur du joueur et en appelant le callback de jeu."""
        self.my_color = data["set_color"]
        self.game_callback(data)

    def Network_your_turn(self, data):
        """
        Indique que c'est le tour du joueur actif.
        Met à jour l'interface de jeu en conséquence.
        """
        self.game_callback({
            "action": "your_turn",
            "your_turn": True,
            "opponent": data.get("opponent", "")
        })

    def Network_opponent_turn(self, data):
        """
        Informe que c'est le tour de l'adversaire après le coup du joueur.
        """
        self.game_callback({
            "action": "opponent_turn",
            "your_turn": False,
            "opponent": data.get("opponent", "")
        })

    def Network_ovals(self, data):
        """Reçoit les coordonnées des points joués par un joueur et met à jour le plateau."""
        self.game_callback(data)

    def Network_game_over(self, data):
        """Gère la fin de la partie en affichant le gagnant et en revenant au lobby."""
        winner = data["winner"]
        messagebox.showinfo("Fin de partie", f"{winner} a gagné!")
        self.game_callback({"action": "return_to_lobby"})

    def Network_error(self, data):
        """Affiche une boîte de dialogue en cas d'erreur signalée par le serveur."""
        messagebox.showerror("Erreur", data["message"])

    def Network_connected(self, data):
        """Confirme la connexion au serveur (affichage dans la console)."""
        print("[CLIENT] Connected to server")

    def Network_disconnected(self, data):
        """Informe l'utilisateur de la déconnexion du serveur et termine le programme."""
        messagebox.showinfo("Déconnexion", "Le serveur est déconnecté")
        exit()

# --- Fenêtre Client complète ---
# Définit la fenêtre principale qui gère le passage entre le lobby et le jeu.
class ClientWindow(Tk):
    def __init__(self, host, port, nickname):
        Tk.__init__(self)
        self.title(nickname)
        self.nickname = nickname
        self.my_score = 1000
        self.lobby_size = "400x300"
        self.game_size = f"{WIDTH}x{HEIGHT+70}"
        # Création du client réseau avant l'affichage du lobby
        self.status_label = Label(self, text="Lobby...")
        self.status_label.pack(side=TOP, pady=5)
        self.client = Client(host, int(port), self.update_lobby, self.handle_game_message, nickname)
        self.lobby_frame = LobbyFrame(self, self.client)
        self.lobby_frame.pack(fill=BOTH, expand=True)
        self.game_frame = None

    def update_lobby(self, players, my_score, leaderboard):
        """Met à jour l'affichage du lobby avec le nouveau score et la liste des joueurs."""
        self.my_score = my_score
        self.status_label.config(text="Lobby")
        self.geometry(self.lobby_size)
        

        if self.lobby_frame:
            self.lobby_frame.update_lobby(players, my_score, leaderboard)

    def handle_game_message(self, data):
        """
        Gère les différents messages reçus du serveur en fonction de l'action :
         - Début de partie et changement de tour
         - Mise à jour du plateau avec les points joués
         - Retour au lobby en fin de partie
        """
        action = data.get("action", "")
        if action in ["start_game", "your_turn", "opponent_turn"]:
            # Création du plateau de jeu s'il n'existe pas déjà
            if self.game_frame is None:
                self.lobby_frame.pack_forget()
                self.game_frame = GameFrame(self, self.client)
                self.game_frame.pack(fill=BOTH, expand=True)
                self.geometry(self.game_size)
            # Mise à jour de l'indicateur de tour en fonction des données reçues
            self.game_frame.board.can_play = data.get("your_turn", False)
            if data.get("your_turn", False):
                turn = "À toi de jouer"
            else:
                turn = f"Au tour de {data.get('opponent', '')}"
            self.status_label.config(text=turn)
        elif action == "ovals":
            # Mise à jour du plateau avec les points joués par l'adversaire
            if self.game_frame:
                self.game_frame.board.draw_sausage_points(data["ovals"], data["color"])
                self.status_label.config(text=f"Au tour de {data.get('opponent', '')}")
        elif action == "return_to_lobby":
            self.return_to_lobby()
        else:
            pass

    def return_to_lobby(self):
        """Retourne à l'affichage du lobby après la fin d'une partie."""
        if self.game_frame:
            self.game_frame.pack_forget()
            self.game_frame.destroy()
            self.game_frame = None
        self.lobby_frame.pack(fill=BOTH, expand=True)
        self.status_label.config(text="Lobby")

    def abandon_game(self):
        if self.game_frame is not None:
            # Envoie le message d'abandon au serveur
            from PodSixNet.Connection import connection
            connection.Send({"action": "abandon"})
            # Optionnel : afficher un message d'information
            messagebox.showinfo("Abandon", "Vous avez abandonné la partie. L'adversaire gagne.")
            # Retour au lobby
            self.return_to_lobby()
        else:
            messagebox.showinfo("Abandon", "Vous n'êtes pas en jeu.")

    def myMainLoop(self):
        """Boucle principale de l'interface qui met à jour l'affichage et le client réseau."""
        while self.client.state != "DEAD":
            self.update()
            self.client.Loop()
            sleep(0.001)

if __name__ == "__main__":
    # Vérifie les arguments pour la connexion au serveur
    if len(sys.argv) != 2:
        print("Usage: python3 Client.py host:port")
        host, port = "localhost", "31425"
    else:
        host, port = sys.argv[1].split(":")
    # Demande du pseudo à l'utilisateur
    nickname = input("Entrez votre pseudo : ").rstrip("\n")
    window = ClientWindow(host, port, nickname)
    window.myMainLoop()
