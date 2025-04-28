import playingStrategies_euristica
import random

def playerStrategy(game, state):
    # Usa una profondità di 3 per bilanciare efficienza e qualità delle decisioni
    cutOff = 3
    
    # Sostituiamo l'euristica nella libreria prima di eseguire la ricerca
    playingStrategies_euristica.h = cephalopod_heuristic
    
    # Esegui la ricerca alpha-beta con la nostra euristica
    value, move = playingStrategies_euristica.h_alphabeta_search(game, state, playingStrategies_euristica.cutoff_depth(cutOff))
    
    # In caso di timeout o errori, tornare a una scelta casuale
    if move is None:
        return random.choice(list(game.actions(state)))
    
    return move

def cephalopod_heuristic(state, player):
    """
    Euristica per valutare uno stato del gioco Cephalopod.
    Considera:
    1. Differenza tra il numero di pezzi
    2. Controllo del centro
    3. Potenziale di cattura
    """
    # Se il gioco è terminato, restituisci l'utilità effettiva
    # oppositePlayer è l'avversario di player
    oppositePlayer = "Red" if player == "Blue" else "Blue"
    
    # Conta i pezzi per ogni giocatore
    playerCount = state.count(player)
    oppositeCount = state.count(oppositePlayer)
    
    # Calcola la differenza di pezzi (normalizzata)
    piece_diff = (playerCount - oppositeCount) / (playerCount + oppositeCount + 1)
    
    # Valuta il controllo del centro (le celle centrali valgono di più)
    size = state.size
    center_control = 0
    center = size // 2
    
    # Maggiore peso alle celle centrali
    for r in range(size):
        for c in range(size):
            if state.board[r][c] is not None:
                # Calcola la distanza dal centro
                dist_from_center = abs(r - center) + abs(c - center)
                # Trasforma la distanza in un valore (più vicino al centro = valore più alto)
                cell_value = (size - dist_from_center) / size
                
                if state.board[r][c][0] == player:
                    center_control += cell_value
                else:
                    center_control -= cell_value
    
    # Normalizza il controllo del centro
    center_control = center_control / (size * size)
    
    # Valuta il potenziale di cattura (quante celle adiacenti si possono catturare)
    # Questo calcolo è approssimativo e potrebbe essere migliorato
    capture_potential = 0
    for r in range(size):
        for c in range(size):
            if state.board[r][c] is None:  # cella vuota
                # Conta quante celle adiacenti appartengono all'avversario
                enemy_adjacent = 0
                for dr, dc in [(-1,0), (1,0), (0,-1), (0,1)]:
                    nr, nc = r+dr, c+dc
                    if 0 <= nr < size and 0 <= nc < size:
                        if state.board[nr][nc] is not None and state.board[nr][nc][0] == oppositePlayer:
                            enemy_adjacent += 1
                
                # Più celle nemiche adiacenti = maggiore potenziale di cattura
                if enemy_adjacent >= 2:
                    capture_potential += enemy_adjacent / 4  # Normalizzato per il massimo di 4 adiacenti
    
    # Combina i fattori con pesi appropriati
    # Possiamo dare più importanza alla differenza di pezzi mentre il gioco avanza
    game_progress = (state.count(player) + state.count(oppositePlayer)) / (size * size)
    
    # All'inizio del gioco, valorizziamo controllo del centro e potenziale di cattura
    # Verso la fine, valorizziamo di più la differenza di pezzi
    score = (piece_diff * (0.4 + 0.4 * game_progress) + 
             center_control * (0.4 - 0.2 * game_progress) + 
             capture_potential * (0.2 - 0.1 * game_progress))
    
    return score