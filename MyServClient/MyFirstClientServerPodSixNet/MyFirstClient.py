import sys
from PodSixNet.Connection import connection, ConnectionListener
from tkinter import *
from tkinter import messagebox
from time import sleep

RADIUS = 20
XMIN = 30
YMIN = 30
DIST = 50
COLONNES = 9
LIGNES = 7
WIDTH = 2 * XMIN + 8 * DIST
HEIGHT = 2 * YMIN + 6 * DIST

# Classe du plateau de jeu
class Board:
    def __init__(self, canvas):
        self.canvas = canvas
        self.point = [[None for _ in range(LIGNES)] for _ in range(COLONNES)]
        self.selected_points = []
        self.sausages = []
        self.occupied_points = set()
        self.current_player = 1
        self.draw_board()

    def draw_board(self):
        """Dessine le plateau avec les points."""
        for col in range(COLONNES):
            for ligne in range(LIGNES):
                if (col + ligne) % 2 == 0:
                    idPoint = self.canvas.create_oval(
                        XMIN + col * DIST - RADIUS, YMIN + ligne * DIST - RADIUS,
                        XMIN + col * DIST + RADIUS, YMIN + ligne * DIST + RADIUS,
                        fill="blue", tags=f"point_{col}_{ligne}"
                    )
                    self.point[col][ligne] = (idPoint, col, ligne)
                    self.canvas.tag_bind(idPoint, "<Button-1>", lambda event,
                                         col=col, ligne=ligne: self.select_point(col, ligne))
                else:
                    self.point[col][ligne] = None

    def select_point(self, col, ligne):
        """Ajoute un point sélectionné et gère la création de saucisses."""
        if (col, ligne) in self.occupied_points:
            return
        if (col, ligne) not in self.selected_points:
            self.selected_points.append((col, ligne))
            color = "red" if self.current_player == 1 else "green"
            self.canvas.itemconfig(self.point[col][ligne][0], fill=color)

        if len(self.selected_points) == 3:
            if self.is_valid_sausage():
                self.draw_sausage()
                self.occupied_points.update(self.selected_points)
                self.send_move()  # Send the move to the server
            else:
                for col, ligne in self.selected_points:
                    self.canvas.itemconfig(self.point[col][ligne][0], fill="blue")
            self.selected_points = []

    def is_valid_sausage(self):
        """Vérifie si les 3 points sélectionnés forment une saucisse valide."""
        col_values = [p[0] for p in self.selected_points]
        ligne_values = [p[1] for p in self.selected_points]
        return max(col_values) - min(col_values) <= 2 and max(ligne_values) - min(ligne_values) <= 2

    def draw_sausage(self):
        """Dessine une saucisse entre les points sélectionnés."""
        color = "red" if self.current_player == 1 else "green"
        for i in range(2):
            self.canvas.create_line(
                XMIN + self.selected_points[i][0] * DIST,
                YMIN + self.selected_points[i][1] * DIST,
                XMIN + self.selected_points[i+1][0] * DIST,
                YMIN + self.selected_points[i+1][1] * DIST,
                width=5, fill=color
            )

    def send_move(self):
        """Send the move to the server."""
        col, ligne = self.selected_points[0]  # Assuming the first point in the selection
        connection.Send({"action": "newPoint", "newPoint": (col, ligne)})

class Game:
    def __init__(self, canvas):
        self.board = Board(canvas)
        self.current_player = 1

    def update_game_state(self, game_state):
        """Update the game state based on server updates."""
        self.board = game_state["board"]
        self.current_player = game_state["current_player"]

    def show_winner(self, winner):
        """Display a message when a winner is found."""
        messagebox.showinfo("Fin de la partie", f"Le joueur {winner} a gagné!")
        self.quit()

class Client(ConnectionListener):
    def __init__(self, host, port, window):
        self.window = window
        self.Connect((host, port))
        self.state = "ACTIVE"
        print("Client started")
        print("Ctrl-C to exit")
        print("Enter your nickname: ")
        nickname = input().rstrip("\n")
        self.nickname = nickname
        connection.Send({"action": "nickname", "nickname": nickname})

    def Network_connected(self, data):
        print("You are now connected to the server")

    def Loop(self):
        connection.Pump()
        self.Pump()

    def quit(self):
        self.window.destroy()
        self.state = "DEAD"

    def Network_start(self, data):
        self.state = "ACTIVE"
        self.window.game.update_game_state(data["game_state"])

    def Network_newPoint(self, data):
        (x, y) = data["newPoint"]
        self.window.white_board_canvas.create_oval(x - RADIUS, y - RADIUS, x + RADIUS, y + RADIUS)
        self.window.white_board_canvas.update()

    def Network_game_over(self, data):
        """Handle the end of the game."""
        self.window.game.show_winner(data["winner"])

class Game:
    def __init__(self, canvas):
        self.board = Board(canvas)
        self.current_player = 1

    def update_game_state(self, game_state):
        """Update the game state based on server updates."""
        self.board = game_state["board"]
        self.current_player = game_state["current_player"]

    def show_winner(self, winner):
        """Display a message when a winner is found."""
        messagebox.showinfo("Fin de la partie", f"Le joueur {winner} a gagné!")
        self.quit()

    def send_move(self, col, ligne):
        """Send the move to the server."""
        connection.Send({"action": "newPoint", "newPoint": (col, ligne)})

class ClientWindow(Tk):
    def __init__(self, host, port):
        Tk.__init__(self)
        self.client = Client(host, int(port), self)
        self.white_board_canvas = Canvas(self, width=WIDTH, height=HEIGHT, bg='white')
        self.white_board_canvas.pack(side=TOP)
        quit_but = Button(self, text='Quitter', command=self.client.quit)
        quit_but.pack(side=BOTTOM)
        self.game = Game(self.white_board_canvas)

    def myMainLoop(self):
        while self.client.state != "DEAD":
            self.update()
            self.client.Loop()
            sleep(0.001)
        exit()


if len(sys.argv) != 2:
    print("Please use: python3", sys.argv[0], "host:port")
    host, port = "localhost", "31425"
else:
    host, port = sys.argv[1].split(":")
client_window = ClientWindow(host, port)
client_window.myMainLoop()
