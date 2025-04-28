import random
import math
import time
from collections import defaultdict

class MCTSNode:
    """Nodo dell'albero Monte Carlo ottimizzato per velocità"""
    __slots__ = ('state', 'parent', 'move', 'children', 'visits', 'wins', 'untried_moves', 'player')
    
    def __init__(self, state, parent=None, move=None):
        self.state = state
        self.parent = parent
        self.move = move
        self.children = {}
        self.visits = 0
        self.wins = 0
        self.untried_moves = None
        self.player = state.to_move
    
    def get_untried_moves(self, game):
        """Inizializzazione lazy delle mosse non provate"""
        if self.untried_moves is None:
            self.untried_moves = list(game.actions(self.state))
            # Prioritizza le mosse di cattura durante l'esplorazione
            self.untried_moves.sort(key=lambda m: len(m[2]), reverse=True)
        return self.untried_moves
    
    def has_untried_moves(self):
        """Controllo ottimizzato"""
        return self.untried_moves and len(self.untried_moves) > 0
    
    def best_child(self, c_param=1.41):
        """Versione ottimizzata della selezione UCB1"""
        player_factor = 1 if self.player == "Blue" else -1
        best_value = -float('inf')
        best_node = None
        log_visits = math.log(self.visits) if self.visits > 0 else 0
        
        for child in self.children.values():
            # Calcolo ottimizzato di UCB1
            exploit = child.wins / child.visits if child.visits > 0 else 0
            # Adatta in base al giocatore
            if player_factor == -1:  # Red vuole minimizzare
                exploit = 1 - exploit
            explore = c_param * math.sqrt(log_visits / child.visits) if child.visits > 0 else float('inf')
            value = exploit + explore
            
            if value > best_value:
                best_value = value
                best_node = child
        
        return best_node
    
    def add_child(self, move, state):
        """Versione semplificata per velocità"""
        child = MCTSNode(state, self, move)
        self.children[move] = child
        if self.untried_moves:
            try:
                self.untried_moves.remove(move)
            except ValueError:
                pass  # Ignora se non trovato (caso raro)
        return child
    
    def update(self, result):
        """Aggiornamento statistiche ottimizzato"""
        self.visits += 1
        # Per Blue vogliamo massimizzare, per Red minimizzare
        if self.player == "Blue":
            self.wins += result
        else:
            self.wins += (1 - result)

# Cache per le simulazioni - evita di simulare più volte lo stesso stato
simulation_cache = {}

def monte_carlo_tree_search(game, state, timeout=2.7):
    """MCTS ottimizzato per velocità"""
    start_time = time.time()
    root = MCTSNode(state)
    end_time = start_time + timeout
    
    # Preallochiamo una lista per le mosse del gioco per evitare allocazioni ripetute
    legal_moves = list(game.actions(state))
    if not legal_moves:
        return None
    
    # Se c'è una sola mossa legale, restituiscila immediatamente
    if len(legal_moves) == 1:
        return legal_moves[0]
    
    # Identifica mosse che catturano immediatamente
    capture_moves = [m for m in legal_moves if len(m[2]) > 0]
    if capture_moves and len(capture_moves) < 3:
        # Se ci sono poche mosse di cattura, prioritizzale
        capture_moves.sort(key=lambda m: len(m[2]), reverse=True)
        return capture_moves[0]
    
    iterations = 0
    try:
        while time.time() < end_time:
            iterations += 1
            
            # Fase 1: Selezione
            node = select(root, game)
            
            # Fase 2: Espansione
            if not game.is_terminal(node.state) and node.has_untried_moves():
                node = expand(node, game)
            
            # Fase 3: Simulazione (con cache)
            state_hash = hash_state(node.state)
            if state_hash in simulation_cache:
                result = simulation_cache[state_hash]
            else:
                result = simulate(game, node.state)
                # Limita dimensione cache per evitare problemi di memoria
                if len(simulation_cache) < 10000:
                    simulation_cache[state_hash] = result
            
            # Fase 4: Backpropagation
            backpropagate(node, result)
    except Exception as e:
        print(f"MCTS error: {e}")
        # In caso di errore, restituisci una mossa valida
        return legal_moves[0]
    
    # Seleziona la mossa con più visite (più affidabile della win ratio)
    best_move = None
    best_visits = -1
    
    if not root.children:
        # Fallback se non c'è stato tempo per esplorare
        return random.choice(legal_moves)
    
    # Selezione della mossa basata su visite per maggiore stabilità
    for move, child in root.children.items():
        if child.visits > best_visits:
            best_visits = child.visits
            best_move = move
    
    # Debug info se necessario
    # print(f"MCTS: {iterations} iterazioni in {time.time() - start_time:.3f}s")
    
    return best_move

def hash_state(state):
    """Funzione hash efficiente per gli stati di gioco"""
    # Versione semplificata per velocità
    board_str = ""
    for row in state.board:
        for cell in row:
            if cell is None:
                board_str += "N"
            else:
                player, pip = cell
                board_str += player[0] + str(pip)
    return hash(board_str + state.to_move)

def select(node, game):
    """Selezione ottimizzata"""
    current = node
    # Evita la ricorsione per maggiore velocità
    while not game.is_terminal(current.state):
        if current.has_untried_moves():
            return current
        
        if not current.children:
            return current
            
        current = current.best_child()
    return current

def expand(node, game):
    """Espansione prioritizzando mosse di cattura"""
    untried = node.get_untried_moves(game)
    move = untried[0]  # Già ordinate per potenziale di cattura
    new_state = game.result(node.state, move)
    return node.add_child(move, new_state)

def simulate(game, state):
    """Simulazione ottimizzata con euristica semi-random"""
    # Copia veloce dello stato
    current_state = state.copy()
    depth = 0
    max_simulation_depth = 25  # Limite per evitare simulazioni troppo lunghe
    
    # Simulazione rapida con preferenza per catture
    while not game.is_terminal(current_state) and depth < max_simulation_depth:
        depth += 1
        moves = list(game.actions(current_state))
        
        # Se poche mosse, non fare calcoli extra
        if len(moves) <= 2:
            move = moves[0]
        else:
            # Fast heuristic per preferire mosse di cattura
            capture_moves = []
            for m in moves:
                if len(m[2]) > 0:
                    capture_moves.append(m)
            
            if capture_moves:
                # Scelta pesata in base al numero di catture
                weights = [len(m[2])**2 for m in capture_moves]  # Quadrato per enfatizzare catture multiple
                total = sum(weights)
                if total > 0:
                    r = random.random() * total
                    upto = 0
                    for i, w in enumerate(weights):
                        upto += w
                        if upto > r:
                            move = capture_moves[i]
                            break
                    else:
                        move = capture_moves[-1]
                else:
                    move = capture_moves[0]
            else:
                # Se nessuna cattura, mossa casuale con preferenza per il centro
                center = current_state.size // 2
                # Valuta posizione rispetto al centro
                move_values = []
                for m in moves:
                    r, c = m[0]
                    # Distanza dal centro (inversamente proporzionale al valore)
                    dist = abs(r - center) + abs(c - center)
                    value = current_state.size - dist
                    move_values.append((value, m))
                
                # Scelta pesata in base alla posizione
                move_values.sort(reverse=True)
                # Prendi top 50% delle mosse
                top_moves = move_values[:max(1, len(move_values)//2)]
                move = random.choice([m for _, m in top_moves])
        
        current_state = game.result(current_state, move)
    
    # Valutazione rapida finale
    if game.is_terminal(current_state):
        return 1 if game.utility(current_state, "Blue") > 0 else 0
    else:
        # Valutazione euristica se simulazione troncata
        blue_count = current_state.count("Blue")
        red_count = current_state.count("Red")
        if blue_count > red_count:
            return 1
        elif red_count > blue_count:
            return 0
        else:
            return 0.5  # Pareggio

def backpropagate(node, result):
    """Backpropagation ottimizzata senza ricorsione"""
    current = node
    while current is not None:
        current.update(result)
        current = current.parent

def playerStrategy(game, state):
    """Strategia di gioco ottimizzata"""
    # Clear cache at start of turn to free memory
    global simulation_cache
    if len(simulation_cache) > 5000:
        simulation_cache = {}
    
    # Controllo rapido per mosse ovvie
    legal_moves = list(game.actions(state))
    
    # Se c'è una sola mossa, giocala subito
    if len(legal_moves) == 1:
        return legal_moves[0]
    
    # Se ci sono mosse di cattura multiple, valutale rapidamente
    capture_moves = [m for m in legal_moves if len(m[2]) > 0]
    if len(capture_moves) == 1:
        # Se c'è una sola mossa di cattura, giocala
        return capture_moves[0]
    elif len(capture_moves) > 1 and len(capture_moves) <= 3:
        # Se ci sono poche mosse di cattura, scegli quella che cattura di più
        best_capture = max(capture_moves, key=lambda m: len(m[2]))
        # Se è significativamente migliore, giocala subito
        if len(best_capture[2]) >= 3:
            return best_capture
    
    # Altrimenti usa MCTS
    return monte_carlo_tree_search(game, state, timeout=2.7)