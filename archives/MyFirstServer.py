import sys
from time import sleep, localtime

from PodSixNet.Server import Server
from PodSixNet.Channel import Channel

class ClientChannel(Channel):
    """
    This is the server representation of a connected client.
    """
    nickname = "anonymous"
    
    def Close(self):
        self._server.DelPlayer(self)
    
    def Network_oval(self, data):
        print(data)
        self._server.SendToOthers({"oval": data["oval"], "who": self.nickname})
    
    def Network_nickname(self, data):
        self.nickname = data["nickname"]
        self._server.PrintPlayers()
        self.Send({"action":"start"})
    
    def Network_turn_update(self,data):
        self.current_player = 1 - self.current_player # change l'ID du joueur qui selectionne actuellement
        print(f"Tour suivant: {self.players[self.current_player].nickname}")
       
        for i, player in enumerate(self.players):
            player.Send({"action": "turn_update","your_turn": (i == self.current_player)})

class MyServer(Server):
    channelClass = ClientChannel
    def __init__(self, mylocaladdr):
        Server.__init__(self, localaddr=mylocaladdr)
        self.players={}
        print('Server launched')
    
    def Connected(self, channel, addr):
        self.AddPlayer(channel)
    
    def AddPlayer(self, player):
        print("New Player connected")
        self.players[player] = True
 
    def PrintPlayers(self):
        print("players' nicknames :",[p.nickname for p in self.players])
    
    
    def DelPlayer(self, player):
        print("Deleting Player " + player.nickname + " at "+str(player.addr))
        del self.players[player]
       
    def SendToOthers(self, data):
        [p.Send({"action":"oval", "oval" : data["oval"]}) for p in self.players if p.nickname != data["who"]]
    
    def Launch(self):
        while True:
            self.Pump()
            sleep(0.001)

# get command line argument of server, port
if len(sys.argv) != 2:
    print("Please use: python3", sys.argv[0], "host:port")
    print("e.g., python3", sys.argv[0], "localhost:31425")
    host, port = "localhost","31425"
else:
    host, port = sys.argv[1].split(":")
s = MyServer((host, int(port)))
s.Launch()

