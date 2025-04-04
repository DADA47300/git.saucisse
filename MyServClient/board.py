from tkinter import *

RADIUS = 20
XMIN = 30
YMIN = 30
DIST = 50
COLONNES = 9 
LIGNES = 7   
WIDTH = 2 * XMIN + 8 * DIST
HEIGHT = 2 * YMIN + 6 * DIST



class Board:
    def __init__(self, canvas, saucisse_posee):                                #creation d'un board initialise avec un canvas graphique et des saucisses posees
        self.canvas = canvas                                                   # Stocke une ref au canvas tkinter donne par la classe board
        self.point = [[None for _ in range(LIGNES)] for _ in range(COLONNES)]  # Création de la matrice
        self.selected_points = []                                              # Liste des points sélectionnés
        self.sausages = []                                                     # Liste des saucisses déjà posées
        self.occupied_points = set()                                           # Points déjà utilisés dans une saucisse, creer un ensemble de points occupes, au debut vide, un set est non ordonne, + efficace q'une liste --> pas besoin de verifier les doublons et de la parcourir en un temps o(n), chaque point a deja sa propre "identite"
        self.current_player = 1                                                # Le joueur 1 commence
        self.saucisse_posee = saucisse_posee                                   # Stocke la variable saucisse_posée passée par Game
        self.draw_board()                                                      # Dessiner le plateau

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
                    self.canvas.tag_bind(idPoint, "<Button-1>", lambda event,                  #tag_bind --> methode de tkinter qui permet d'associer a un element du canvas (ici un point) un evenement. Clique gauche souris ici. lambda event obligatoire par tkinter, col = col et ligne = ligne fixe les valeurs dans l'evenement lambda, associe a methode selection de point
                                         col=col, ligne=ligne: self.select_point(col, ligne))
                else:  
                    self.point[col][ligne] = None                              # si espace vide on associe pas de methode de clique / selection

    def select_point(self, col, ligne):
        """Ajoute un point sélectionné et gère la création de saucisses."""
        if (col, ligne) in self.occupied_points:
            return                                                             # Empêcher de sélectionner un point déjà utilisé

        if (col, ligne) not in self.selected_points:
            self.selected_points.append((col, ligne))                          # si pas occupe, on l'ajoute a la liste predefinie des points selectionnes
            color = "red" if self.current_player == 1 else "green"             # variable couleur qui lui est associee en fonction du joueur
            self.canvas.itemconfig(self.point[col][ligne][0], fill=color)      # methode qui permet de modifier dynamiquement les propriétés visuelles d’un objet graphique existant, change la couleur du cercle selectionne
        
        if len(self.selected_points) == 3:                                     # verifie si 3 saucisses sont selectionnees par un joueur
            if self.is_valid_sausage():                                        # appelle la methode qui verifie si la saucisse est valide
                self.draw_sausage()                          
                self.occupied_points.update(self.selected_points)              # Ajouter ces points comme occupés dans l'ensemble de points occupes en utilisant la methode update() sur un set.
                self.current_player = (self.current_player % 2) + 1            # Alterne entre 1 et 2
                
            else:                                                                  
                for col, ligne in self.selected_points:                        # Réinitialiser la couleur des points selectionnes si la saucisse choisi est non valide.
                    self.canvas.itemconfig(self.point[col][ligne][0], fill="blue")
            self.selected_points = []                                          # remet a 0 la liste des points selectionnes

    def point_bloque(self, col, ligne):
        """Marque un point comme bloqué s'il n'a pas au moins deux voisins valides dans un rayon de 2 colonnes ou 2 lignes max."""
        directions = [(-2, 0), (2, 0), (0, -2), (0, 2), (-2, -2), (-2, 2), 
                      (2, -2), (2, 2),(1, 1), (-1, -1), (1, -1), (-1, 1)]      # les 12 voisins possibles autour d'un point, venant des 12 directions

        valid_neighbors = 0                                                    # Compte le nombre de voisins valides

        for dx, dy in directions:                                              # Vérifier si le point a des voisins valides dans les directions possibles
            new_col = col + dx
            new_ligne = ligne + dy                                             # creation des voisins "imaginaires" / "qui peuvent exister"
        
            if 0 <= new_col < COLONNES and 0 <= new_ligne < LIGNES:            # Vérifier si les nouvelles coordonnées sont valides et à l'intérieur du plateau
                if (new_col, new_ligne) not in self.occupied_points:           # Si le voisin est valide et n'est pas déjà occupé (bloqué)
                    valid_neighbors += 1
        
            if valid_neighbors >= 2:                                           # Si on a trouvé 2 voisins valides, le point n'est pas bloqué
                return

                                                                               # Si moins de 2 voisins valides sont trouvés, on marque le point comme bloqué
        self.canvas.itemconfig(self.point[col][ligne][0], fill="black")        # Change la couleur du point en noir
        self.occupied_points.add((col, ligne))                                 # Ajouter le point à l'ensemble des points bloqués

    def end_turn(self):
        """Fin de tour, vérifie et marque les points bloqués sur le plateau."""# methode utilise dans le fichier main / td3 pour verifier si il reste des points nn occupes
        
        for col in range(COLONNES):                                            # Appeler point_bloque pour chaque point après chaque tour
            for ligne in range(LIGNES):
                if (col, ligne) not in self.occupied_points:                   # Ne vérifier que les points non occupés
                    self.point_bloque(col, ligne)                              # Vérifie si un point est disponible et le bloque si non

    def is_valid_sausage(self):
        """Vérifie si les 3 points sélectionnés forment une saucisse valide."""# verifie si les 3 point sont suffisament proche pour former une saucisse
        col_values = [p[0] for p in self.selected_points]                      #recupere les coord des points selectionnes
        ligne_values = [p[1] for p in self.selected_points]
        return max(col_values) - min(col_values) <= 2 and max(ligne_values) - min(ligne_values) <= 2   # si la diff maximale (donc entre max et min) entre les col et entre les lignes est =< 2 => la saucisse est valide  

    def draw_sausage(self):
        """Dessine une saucisse entre les points sélectionnés."""
        color = "red" if self.current_player == 1 else "green"
        for i in range(2):                                                     # Besoin de deux boucles pour dessiner seulement deux segments
            self.canvas.create_line(
                XMIN + self.selected_points[i][0] * DIST,
                YMIN + self.selected_points[i][1] * DIST,
                XMIN + self.selected_points[i+1][0] * DIST,
                YMIN + self.selected_points[i+1][1] * DIST,
                width=5, fill=color)
            
        self.saucisse_posee[self.current_player] = True                        # indique que le joueur a place une saucisse, utilise dans game pour alterner les roles 
        

            
    
