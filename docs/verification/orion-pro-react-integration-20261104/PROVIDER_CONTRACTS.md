# Contrats fournisseur consultés le 4 novembre 2026

La [documentation officielle PitchAPI](https://pitchapi.dev/) décrit les heatmaps comme des triplets clairsemés `[cell_x,cell_y,actions]`, dans une grille de 16 × 12 cellules. `grid.length`, `grid.width`, `grid.frame` et les dimensions de cellule décrivent le repère. L'ordre des triplets observés doit être conservé ; aucun zéro supplémentaire ne sera matérialisé dans les tables. Les doublons, bornes et types restent à vérifier sur chaque observation avant acceptation.

La même documentation donne les coordonnées des tirs en mètres sur 105 × 68, avec direction `acting_ltr`. Le contrat `home_ltr` des heatmaps est déjà orienté par le serveur. Les futurs lecteurs doivent conserver le repère observé et éviter une rotation supplémentaire.

Ce document qualifie le format annoncé ; il ne prouve pas la conformité de chaque ancien corps. Le lot content a identifié 1 344 triplets dans 32 collections. Leur import exige encore une matrice complète, un oracle indépendant et les tests préparés avant correction du normaliseur. Aucun schéma ni source stockée n'est modifié ici.

Commit proposé : `docs: qualify provider coordinate and sparse heatmap contracts`.
