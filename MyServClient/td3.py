from tkinter import *
from tkinter import messagebox
from board import Board
import time

RADIUS = 20                                                                    # rayon d'un point
XMIN = 30                                                                      # distance minimale entre le bord d'un cercle et l'extremite du plateau
YMIN = 30              
DIST = 50                                                                      # distance entre deux centres de cercles
COLONNES = 9                                                                   # le cercle en haut a gauche est de centre xmin,ymin
LIGNES = 7   
WIDTH = 2 * XMIN + 8 * DIST
HEIGHT = 2 * YMIN + 6 * DIST


class Game:
    def __init__(self, canvas):
        self.saucisse_posee = {1: False, 2: False}
        self.board = Board(canvas, self.saucisse_posee)                        # Créer une instance de la classe Board
        self.current_player = 1                                                # Le joueur Rouge commence (1 = Rouge, 2 = Vert)
        self.game_over = False                                                 # Variable pour savoir si la partie est terminée
        self.turn_completed = [False, False]                                   # Liste pour suivre si chaque joueur a terminé son tour
        #self.game_active = True                                               
                                                                               
        self.turn_time = 15                                                    # Temps de départ pour chaque joueur (en secondes) par coup
        self.start_time = {1: None, 2: None}                                   # Heure de début du tour de chaque joueur
        self.remaining_time = {1: self.turn_time, 2: self.turn_time}           # Temps restant pour chaque joueur

        self.time_label = Label(MyWindow,
                                text=f"Temps Rouge: {self.format_time(self.remaining_time[1])}   Temps Vert: {self.format_time(self.remaining_time[2])}", 
                                font=("Helvetica", 14))                        # Crée un label pour afficher le temps 
        self.time_label.pack()

        self.start_timer()

    def format_time(self, seconds):
        """Formate le temps en minutes:secondes et arrondi à la seconde."""    # methode qui formate le temps pour l'affichage
        seconds = int(seconds)                                                 # Arrondi à la seconde
        minutes = seconds // 60
        seconds = seconds % 60
        return f"{minutes:02}:{seconds:02}"                                    #02 pour afficher au moins deux nombre si 3 sec --> 03

    def start_timer(self):
        """Démarre le timer pour le joueur Rouge et Vert."""
        self.start_time[self.current_player] = time.time()                     # Lorsqu'un tour est lance, enregistre le nbr de secondes ecoules depuis le 1er Janvier 1970 a cet instant
        self.update_time()                                                     

    def update_time(self):
        """Met à jour le temps restant pour chaque joueur."""
        if not self.game_over:
            if self.start_time[self.current_player] is not None:               # si le temps restant / ecoule pour un joueur n'est pas nul
                elapsed_time = time.time() - self.start_time[self.current_player]  # calcul le temps ecoule depuis le debut du tour
                self.remaining_time[self.current_player] = max(0,
                                                               self.turn_time - 
                                                               elapsed_time)   #s'assure que le temps n'est pas negatif, si c'est le cas il devient nul et on passe a condition suivante

                                                                               
            if self.remaining_time[self.current_player] <= 0:                  # Si le temps est écoulé pour un joueur / negatif, il a perdu
                self.game_over = True
                messagebox.showinfo("Fin de la partie", f"Le joueur {'Rouge' if self.current_player == 1 else 'Vert'} a perdu !")
                return

            self.time_label.config(text=f"Temps Rouge: {self.format_time(self.remaining_time[1])}   Temps Vert: {self.format_time(self.remaining_time[2])}") # Apres verification qu'il reste du temps pour le joueur, reformate le temps restant pour l'affichage

            MyWindow.after(100, self.update_time)                              # Utilise une methode de tkinter qui permet d'appeler tt les 100 millisecondes un update_timer pour mettre a jour le decompte --> methode tourne en boucle en arriere plan jusqu'a la fin d'un timer d'un tour ou que le tour est joue, tourne en arriere plan du jeu

    def play_turn(self):
        """Gère un tour de jeu, change de joueur et vérifie l'état des points."""    # methode qui sera utilise pour verifier les conditions de changement de joueur quand le bouton jouer un tour sera appuyer. 
        if self.game_over:
            return                                                             # Si la partie est terminée, on ne joue plus
        
        if not self.saucisse_posee[self.current_player]:
            messagebox.showinfo("Tour incomplet", f"Le joueur {'Rouge' if self.current_player == 1 else 'Vert'} doit poser une saucisse avant de passer son tour.")
            return                                                             # Empêche de passer le tour tant que la saucisse n'a pas été posée
                         
        self.board.end_turn()                                                  # Si le joueur a pose une saucisse , appelle end_turn de board pour bloquer les points qui ne sont plus jouables

        self.turn_completed[self.current_player - 1] = True                    # Marquer le tour comme complété pour ce joueur

        self.current_player = 1 if self.current_player == 2 else 2             # Change de joueur automatiquement après avoir créé une saucisse

                                                                               # Permet au nouvel autre joueur de jouer
        self.turn_completed[self.current_player - 1] = False                   # Le joueur qui vient de passer son tour peut maintenant jouer
        
        self.saucisse_posee[self.current_player] = False                       # Réinitialisation pour le nouveau joueur

                                                                               # Redémarre le timer pour l'autre joueur (reset du temps de 10 secondes)
        self.start_time[self.current_player] = time.time()                     # Définir l'heure de début pour le joueur suivant

                                                                                 
        print(f"Joueur {'Rouge' if self.current_player == 1 else 'Vert'} a joué.") # Afficher un message indiquant que le tour est terminé
        self.update_time_display()

    def update_time_display(self):
        """Met à jour l'affichage du temps restant pour les deux joueurs."""
        self.time_label.config(text=f"Temps Rouge: {self.format_time(self.remaining_time[1])}   Temps Vert: {self.format_time(self.remaining_time[2])}")
        if self.remaining_time[1] <= 0 or self.remaining_time[2] <= 0:
            self.game_over = True
            winner = 2 if self.remaining_time[1] <= 0 else 1
            messagebox.showinfo("Fin de la partie", f"Le joueur {'Rouge' if winner == 1 else 'Vert'} a gagné !")

    def quit_game(self):
        """Ferme la fenêtre du jeu."""
        print("Le jeu est fermé.")
        MyWindow.destroy()

    def surrender(self):
        """Abandonne la partie et affiche qui a gagné."""
        if self.current_player == 1:
            winner = 2
        else:
            winner = 1
        
        messagebox.showinfo("Fin de la partie", f"Le joueur {'Rouge' if winner == 1 else 'Vert'} a gagné !")
        self.game_over = True                                                  # Marquer la fin de la partie pour empêcher d'autres tours


MyWindow = Tk()                                                                # Configuration de l'interface utilisateur
MyWindow.title("Jeu de Plateau")

canvas = Canvas(MyWindow, width=WIDTH, height=HEIGHT)                          # Création du canvas
canvas.pack()

game = Game(canvas)                                                            # Créer une instance du jeu

quit_button = Button(MyWindow, text="Quitter", command=game.quit_game)         # Bouton pour quitter le jeu
quit_button.pack(pady=5)

surrender_button = Button(MyWindow, text="Abandonner", command=game.surrender) # Bouton pour abandonner et afficher le gagnant
surrender_button.pack(pady=5)

play_button = Button(MyWindow, text="Jouer un tour", command=game.play_turn)   # Bouton pour jouer un tour (juste pour tester)
play_button.pack(pady=5)

MyWindow.mainloop()








