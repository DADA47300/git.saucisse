import sys
from time import sleep
from sys import stdin, exit

from PodSixNet.Connection import connection, ConnectionListener
import random
from tkinter import *
CELL_SIZE = 70
WIDTH_PLATEAU = 9 * CELL_SIZE
HEIGHT_PLATEAU = 7 * CELL_SIZE
SAUCISSE_WIDTH = 6
R=5

INITIAL=0
ACTIVE=1
DEAD=-1

class Client(ConnectionListener):
    def __init__(self, host, port, window):
        self.window = window
        self.Connect((host, port))
        self.current_player=random.randint(0,1)

        self.state=INITIAL
        print("Client started")
        print("Ctrl-C to exit")
        print("Enter your nickname: ")
        nickname=stdin.readline().rstrip("\n")
        self.nickname=nickname
        connection.Send({"action": "nickname", "nickname": nickname})

        
        self.window.destroy()
        self.state=DEAD
   
    def Network_start(self,data):
        self.state=ACTIVE
        print("started")
   
    def Network_oval(self, data):
        print(data)
        (x,y)=data["oval"]
        self.window.white_board_canvas.itemconfig(f"btn_{x}_{y}", fill="yellow")
        self.window.white_board_canvas.update()

        
    def Network_error(self, data):
        print('error:', data['error'][1])
        connection.Close()
    
    def Network_disconnected(self, data):
        print('Server disconnected')
        exit()
    
    def Network_turn_update(self, data):
        print(f"Reçu tour_update: {data}")
        # Mise à jour du tour
        if data["your_turn"]:
            self.window.your_turn()
        else:
            self.window.opponent_turn()

#########################################################

class ClientWindow(Tk):
    def __init__(self, host, port):
        Tk.__init__(self)
        self.client = Client(host, int(port), self)
        self.white_board_canvas = Canvas(self, width=WIDTH_PLATEAU, height=HEIGHT_PLATEAU, bg='white')
        self.white_board_canvas.pack(side=TOP)
        self.white_board_canvas.bind("<Button-1>", self.drawNewPoint)
        self.current_turn = None 
        quit_but = Button(self, text='Quitter', command=self.client.quit)
        quit_but.pack(side=BOTTOM)
        
        for i in range(9):
            for j in range(7):
                if (i + j) % 2 == 0:  # Seulement les cases jouables
                    x = i * CELL_SIZE + CELL_SIZE//2
                    y = j * CELL_SIZE + CELL_SIZE//2
                    
                    # Création du point avec un tag spécifique
                    btn_tag = f"btn_{i}_{j}"
                    self.white_board_canvas.create_oval(
                        x-15, y-15, x+15, y+15,
                        fill="#2196F3", outline="#0D47A1", width=2,
                        tags=btn_tag
                    )
                    
                    # Lier l'événement de clic à ce tag
                    self.white_board_canvas.tag_bind(btn_tag, "<Button-1>", 
                                                   lambda event, i=i, j=j: self.onOvalClick(i, j))
    def your_turn(self):
        """Active le tour du joueur"""
        self.current_turn = 1
        self.client.Send({"action":"your_turn","your_turn":1})
        print("C'est votre tour!")
    def opponent_turn(self):
        """Désactive pour le tour adverse"""
        self.current_turn = 0
        self.client.Send({"action":"opponent_turn","opponent_turn":0})
        print(f"C'est le tour de {self.opponent_name}")
    
    
    def onOvalClick(self, i, j):
        print(f"Position sélectionnée: ({i}, {j})")
    # Change la couleur pour indiquer la sélection
        self.white_board_canvas.itemconfig(f"btn_{i}_{j}", fill="red")
    # Envoie la position au serveur
        self.client.Send({"action":"oval","oval": (i,j)})
    
    def first_player(self):
        self.current_turns
                  


    def drawNewPoint(self,evt):
        pass
    
    def myMainLoop(self):
        while self.client.state!=DEAD:   
            self.update()
            self.client.Loop()
            sleep(0.001)
        exit()    


# get command line argument of client, port
if len(sys.argv) != 2:
    print("Please use: python3", sys.argv[0], "host:port")
    print("e.g., python3", sys.argv[0], "localhost:31425")
    host, port = "localhost", "31425"
else:
    host, port = sys.argv[1].split(":")
client_window = ClientWindow(host, port)
client_window.myMainLoop()



