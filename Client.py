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

class Board:
    def __init__(self, canvas, client):
        self.canvas = canvas
        self.client = client
        self.point = [[None for _ in range(LIGNES)] for _ in range(COLONNES)]
        self.selected_points = []
        self.occupied_points = set()
        self.my_color = None  # Couleur assignée par le serveur
        self.can_play = False # Indique si c'est le tour du joueur
        self.draw_board()

    def draw_board(self):
        """Dessine le plateau avec les points cliquables."""
        for col in range(COLONNES):
            for ligne in range(LIGNES):
                if (col + ligne) % 2 == 0:
                    idPoint = self.canvas.create_oval(
                        XMIN + col * DIST - RADIUS, YMIN + ligne * DIST - RADIUS,
                        XMIN + col * DIST + RADIUS, YMIN + ligne * DIST + RADIUS,
                        fill="blue", tags=f"point_{col}_{ligne}"
                    )
                    self.point[col][ligne] = (idPoint, col, ligne)
                    self.canvas.tag_bind(
                        idPoint, "<Button-1>",
                        lambda event, c=col, l=ligne: self.select_point(c, l)
                    )
                else:
                    self.point[col][ligne] = None

    def select_point(self, col, ligne):
        """Gère la sélection d'un point si c'est le tour du joueur."""
        if not self.can_play:
            return
        if (col, ligne) in self.occupied_points:
            return
        if (col, ligne) not in self.selected_points:
            self.selected_points.append((col, ligne))
            # Colore le point avec la couleur assignée
            if self.my_color:
                self.canvas.itemconfig(self.point[col][ligne][0], fill=self.my_color)
        if len(self.selected_points) == 3:
            if self.is_valid_sausage():
                self.draw_sausage(self.selected_points, self.my_color)
                self.occupied_points.update(self.selected_points)
                self.send_move()
            else:
                for c, l in self.selected_points:
                    self.canvas.itemconfig(self.point[c][l][0], fill="blue")
            self.selected_points = []

    def is_valid_sausage(self):
        """Vérifie que les 3 points sélectionnés forment une saucisse valide."""
        col_values = [p[0] for p in self.selected_points]
        ligne_values = [p[1] for p in self.selected_points]
        return max(col_values) - min(col_values) <= 2 and max(ligne_values) - min(ligne_values) <= 2

    def draw_sausage(self, points, color):
        """Dessine la saucisse reliant les points."""
        for i in range(2):
            self.canvas.create_line(
                XMIN + points[i][0] * DIST,
                YMIN + points[i][1] * DIST,
                XMIN + points[i+1][0] * DIST,
                YMIN + points[i+1][1] * DIST,
                width=5, fill=color
            )

    def send_move(self):
        """Envoie au serveur la liste des points sélectionnés."""
        connection.Send({"action": "ovals", "ovals": self.selected_points})

    def draw_sausage_points(self, points, color):
        """
        Dessine la saucisse et colorie les points reçus (coup adverse).
        """
        for (col, ligne) in points:
            self.occupied_points.add((col, ligne))
            self.canvas.itemconfig(self.point[col][ligne][0], fill=color)
        self.draw_sausage(points, color)

class Game:
    def __init__(self, canvas, client):
        self.board = Board(canvas, client)

    def show_winner(self, winner):
        messagebox.showinfo("Fin de la partie", f"Le joueur {winner} a gagné!")
        exit()

class Client(ConnectionListener):
    def __init__(self, host, port, window):
        self.window = window
        self.Connect((host, port))
        self.state = "ACTIVE"
        print("[CLIENT] Client started")
        nickname = input("Enter your nickname: ").rstrip("\n")
        self.nickname = nickname
        connection.Send({"action": "nickname", "nickname": nickname})

    def Loop(self):
        connection.Pump()
        self.Pump()

    def quit(self):
        self.window.destroy()
        self.state = "DEAD"

    # Gestionnaires d'événements réseau
    def Network_connected(self, data):
        print("[CLIENT] Connected to server")

    def Network_set_color(self, data):
        color = data["color"]
        print(f"[CLIENT] My color is {color}")
        self.window.game.board.my_color = color

    def Network_your_turn(self, data):
        print("[CLIENT] It's your turn!")
        self.window.game.board.can_play = True

    def Network_ovals(self, data):
        who = data["who"]
        color = data["color"]
        points = data["ovals"]
        print(f"[CLIENT] Received move from {who}: {points} with color {color}")
        if who != self.nickname:
            self.window.game.board.draw_sausage_points(points, color)
        # Une fois le coup joué, on désactive le tour
        self.window.game.board.can_play = False

    def Network_game_over(self, data):
        winner = data["winner"]
        print(f"[CLIENT] Game over, winner: {winner}")
        self.window.game.show_winner(winner)

    def Network_error(self, data):
        print(f"[CLIENT] Error: {data['message']}")

    def Network_disconnected(self, data):
        print("[CLIENT] Server disconnected")
        self.quit()

class ClientWindow(Tk):
    def __init__(self, host, port):
        Tk.__init__(self)
        self.client = Client(host, int(port), self)
        self.white_board_canvas = Canvas(self, width=WIDTH, height=HEIGHT, bg='white')
        self.white_board_canvas.pack(side=TOP)
        quit_but = Button(self, text='Quitter', command=self.client.quit)
        quit_but.pack(side=BOTTOM)
        self.game = Game(self.white_board_canvas, self.client)

    def myMainLoop(self):
        while self.client.state != "DEAD":
            self.update()
            self.client.Loop()
            sleep(0.001)
        exit()

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python3", sys.argv[0], "host:port")
        host, port = "localhost", "31425"
    else:
        host, port = sys.argv[1].split(":")
    client_window = ClientWindow(host, port)
    client_window.myMainLoop()
