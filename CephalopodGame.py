import tkinter as tk
from tkinter import simpledialog, messagebox
from tkinter import ttk
import random, itertools, copy, concurrent.futures, threading, time

#import sys
#sys.path.append("Progetti studenti maggio 2025")
#sys.path.append(".")

# EXAMPLE VERSION
# #######################
#import playerCephalopod as playerBmodule
import playerAlpha as playerBmodule
#import playerExampleRandom as playerRmodule
import playerEuristica1 as playerRmodule
# #######################

class Game:
    """A game is similar to a problem, but it has a terminal test instead of
    a goal test, and a utility for each terminal state. To create a game,
    subclass this class and implement `actions`, `result`, `is_terminal`,
    and `utility`. You will also need to set the .initial attribute to the
    initial state; this can be done in the constructor."""

    def actions(self, state):
        """Return a collection of the allowable moves from this state."""
        raise NotImplementedError

    def result(self, state, move):
        """Return the state that results from making a move from a state."""
        raise NotImplementedError

    def is_terminal(self, state):
        """Return True if this is a final state for the game."""
        return not self.actions(state)

    def utility(self, state, player):
        """Return the value of this final state to player."""
        raise NotImplementedError

# Classe che rappresenta lo stato della board.
class Board:
    def __init__(self, size, board=None, to_move="Blue", last_move=None):
        self.size = size
        if board is None:
            self.board = [[None for _ in range(size)] for _ in range(size)]
        else:
            self.board = board
        self.to_move = to_move      # "Blue" o "Red"
        self.last_move = last_move  # (cella_inserimento, celle_catturate)

    def copy(self):
        new_board = [row[:] for row in self.board]
        return Board(self.size, new_board, self.to_move, self.last_move)

    def is_full(self):
        for row in self.board:
            if any(cell is None for cell in row):
                return False
        return True

    def count(self, player):
        cnt = 0
        for row in self.board:
            for cell in row:
                if cell is not None and cell[0] == player:
                    cnt += 1
        return cnt

# Funzione ausiliaria che genera tutti i sottoinsiemi (delle celle adiacenti) con dimensione minima min_size.
def get_subsets(adjacent, min_size=2):
    subsets = []
    n = len(adjacent)
    for r in range(min_size, n+1):
        for comb in itertools.combinations(adjacent, r):
            subsets.append(list(comb))
    return subsets

# Classe che definisce le regole del gioco Cephalopod.
class CephalopodGame(Game):
    """Il gioco Cephalopod è un gioco a turni per due giocatori, Blue e Red.
    Ogni giocatore può piazzare un numero di pip (da 1 a 6) in una cella vuota della board.
    Se la cella è adiacente a celle occupate da entrambi i giocatori, il giocatore può catturare le celle adiacenti
    e rimuoverle dalla board. Il gioco termina quando la board è piena o non ci sono più mosse legali.
    Il giocatore che occupa la maggioranza delle celle vince."""
    def __init__(self, size=5, first_player="Blue"):
        self.size = size
        self.first_player = first_player
        self.initial = Board(size, to_move=first_player)
    
    # Restituisce l’insieme delle mosse legali.
    # Una mossa è una tupla: ((r,c), pip, captured)
    def actions(self, state):
        moves = []
        for r in range(state.size):
            for c in range(state.size):
                if state.board[r][c] is None:  # cella vuota
                    adjacent = []
                    for dr, dc in [(-1,0), (1,0), (0,-1), (0,1)]:
                        nr, nc = r+dr, c+dc
                        if 0 <= nr < state.size and 0 <= nc < state.size:
                            if state.board[nr][nc] is not None:
                                adjacent.append(((nr, nc), state.board[nr][nc][1]))
                    capture_moves = []
                    if len(adjacent) >= 2:
                        subsets = get_subsets(adjacent, 2)
                        for subset in subsets:
                            s = sum(pip for pos, pip in subset)
                            if 2 <= s <= 6:
                                positions = tuple(pos for pos, pip in subset)
                                capture_moves.append( ((r,c), s, positions) )
                    if capture_moves:
                        moves.extend(capture_moves)
                    else:
                        moves.append( ((r,c), 1, ()) )
        return moves

    # Restituisce la nuova board ottenuta applicando una mossa.
    def result(self, state, move):
        new_state = state.copy()
        (r, c), pip, captured = move
        current_player = state.to_move
        new_state.board[r][c] = (current_player, pip)
        for pos in captured:
            rr, cc = pos
            new_state.board[rr][cc] = None
        new_state.last_move = ((r, c), captured)
        new_state.to_move = "Red" if current_player == "Blue" else "Blue"
        return new_state

    # Stato terminale se la board è completamente piena.
    def is_terminal(self, state):
        return state.is_full()

    # Funzione utilità: vince il giocatore che occupa la maggioranza delle celle.
    # Di default in questa implementazione è stato utilizzato il punto di vista del Blue
    def utility(self, state, player = "Blue"):
        countBlue = state.count("Blue")
        countRed = state.count("Red")
        return 1 if player == "Blue" and countBlue > countRed else -1

# Giocatore artificiale: sceglie una mossa a caso.
def random_player(game, state, timeout=3):
    moves = game.actions(state)
    return random.choice(moves)

############################################################
# Interfaccia grafica del gioco.
class CephalopodGUI:
    def __init__(self, game, player_types, time_out=3):
        # player_types: dizionario con chiavi "Blue" e "Red" e valori "human" o "ai"
        self.game = game
        self.player_types = player_types
        self.state_history = [game.initial]
        self.current_index = 0
        self.executor = concurrent.futures.ThreadPoolExecutor(max_workers=4)
        self.waiting_for_human = False
        self.human_move = None
        self.time_out = time_out  # Salviamo il timeout
        
        # Variabili per la modalità di selezione della cattura
        self.capture_selection_mode = False
        self.pending_placement = None
        self.pending_candidate_moves = []
        self.selected_capture_cells = set()
        
        # Modalità di auto-play (solo per AI vs AI)
        self.auto_mode = False
        self.show_auto = (self.player_types.get("Blue") == "ai" and self.player_types.get("Red") == "ai")
        
        self.root = tk.Tk()
        self.root.title("Cephalopod")
        self.root.geometry("400x400")
        self.root.configure(bg="white")
        
        self.board_frame = tk.Frame(self.root, bg="white")
        self.board_frame.pack(pady=10)
        self.controls_frame = tk.Frame(self.root, bg="white")
        self.controls_frame.pack(pady=10)
        
        # Creazione della griglia con padding fisso
        self.cells = [[None for _ in range(self.game.size)] for _ in range(self.game.size)]
        for r in range(self.game.size):
            for c in range(self.game.size):
                lbl = tk.Label(self.board_frame, text="", width=4, height=2,
                               borderwidth=2, relief="ridge", font=("Helvetica", 16), bg="white", anchor="center")
                lbl.grid(row=r, column=c, padx=3, pady=3)
                lbl.bind("<Button-1>", lambda e, row=r, col=c: self.cell_clicked(row, col))
                self.cells[r][c] = lbl
        
        self.prev_button = tk.Button(self.controls_frame, text="Precedente", command=self.prev_move,
                                     font=("Helvetica", 12), padx=10, pady=5)
        self.prev_button.grid(row=0, column=0, padx=5)
        # Usa lambda per ritardare la chiamata e non eseguirla subito:
        self.next_button = tk.Button(self.controls_frame, text="Successivo", command=lambda: self.next_move(),
                                     font=("Helvetica", 12), padx=10, pady=5)
        self.next_button.grid(row=0, column=1, padx=5)

        if self.show_auto:
            self.auto_button = tk.Button(self.controls_frame, text="Auto", highlightbackground="red", command=self.toggle_auto,
                                         font=("Helvetica", 12), padx=10, pady=5)
            self.auto_button.grid(row=0, column=2, padx=5)
        
        self.confirm_button = tk.Button(self.controls_frame, text="Conferma", highlightbackground="green", command=self.confirm_capture,
                                        font=("Helvetica", 12), padx=10, pady=5)
        self.confirm_button.grid_forget()
        
        self.status_label = tk.Label(self.controls_frame, text="Turno: " + self.current_state().to_move,
                                     bg="white", font=("Helvetica", 12))
        self.status_label.grid(row=1, column=0, columnspan=4)
        
        self.update_board()

    def current_state(self):
        return self.state_history[self.current_index]

    def update_board(self):
        state = self.current_state()
        # Aggiorna le celle in base allo stato della board
        for r in range(state.size):
            for c in range(state.size):
                cell = state.board[r][c]
                lbl = self.cells[r][c]
                if cell is None:
                    lbl.config(text="", bg="white")
                else:
                    player, pip = cell
                    color = "lightblue" if player == "Blue" else "lightcoral"
                    lbl.config(text=str(pip), bg=color)
                lbl.config(relief="ridge", borderwidth=4)
        # Evidenzia la mossa precedente
        if state.last_move:
            (r, c), captured = state.last_move
            self.cells[r][c].config(relief="solid", borderwidth=4)
            for (rr, cc) in captured:
                self.cells[rr][cc].config(relief="solid", borderwidth=4)
        if self.game.is_terminal(state):
            util = self.game.utility(state)
            winner = "Blue" if util == 1 else "Red"
            self.status_label.config(text="Vincitore: " + winner)
        else:
            self.status_label.config(text="Turno: " + state.to_move)
        
        # Se siamo in modalità di selezione cattura, evidenzia:
        if self.capture_selection_mode:
            allowed = set()
            for move in self.pending_candidate_moves:
                allowed.update(move[2])
            # Evidenzia la cella selezionata per l'inserimento con un "?" (colore diverso, es. lightblue)
            pr, pc = self.pending_placement
            self.cells[pr][pc].config(bg="lightblue", text="?")
            # Evidenzia le celle candidate:
            for (ar, ac) in allowed:
                if (ar, ac) in self.selected_capture_cells:
                    self.cells[ar][ac].config(bg="orange")
                else:
                    self.cells[ar][ac].config(bg="lightgreen")

    def cell_clicked(self, r, c):
        if self.waiting_for_human:
            if self.capture_selection_mode:
                allowed = set()
                for move in self.pending_candidate_moves:
                    allowed.update(move[2])
                if (r, c) in allowed:
                    if (r, c) in self.selected_capture_cells:
                        self.selected_capture_cells.remove((r, c))
                    else:
                        self.selected_capture_cells.add((r, c))
                    self.update_board()
            else:
                state = self.current_state()
                legal_moves = self.game.actions(state)
                candidate_moves = [move for move in legal_moves if move[0] == (r, c)]
                if not candidate_moves:
                    return
                if len(candidate_moves) == 1:
                    self.human_move = candidate_moves[0]
                    self.waiting_for_human = False
                else:
                    # Avvia modalità di selezione della cattura
                    self.capture_selection_mode = True
                    self.pending_placement = (r, c)
                    self.pending_candidate_moves = candidate_moves
                    self.selected_capture_cells = set()
                    self.update_board()
                    self.confirm_button.grid(row=0, column=3, padx=5)

    def confirm_capture(self):
        # Verifica se la selezione corrisponde a una mossa valida
        for move in self.pending_candidate_moves:
            if set(move[2]) == self.selected_capture_cells:
                self.human_move = move
                self.waiting_for_human = False
                break
        if self.human_move is None:
            messagebox.showerror("Errore", "Selezione non valida. Riprova.")
            return
        # Esci dalla modalità di selezione e ripristina lo stato
        self.capture_selection_mode = False
        self.pending_placement = None
        self.pending_candidate_moves = []
        self.selected_capture_cells = set()
        self.confirm_button.grid_forget()
        self.update_board()

    def prev_move(self):
        if self.current_index > 0:
            self.current_index -= 1
            self.update_board()

    def next_move(self):
        # Se esistono mosse già calcolate, naviga in avanti
        if self.current_index < len(self.state_history) - 1:
            self.current_index += 1
            self.update_board()
        else:
            # In modalità AI vs AI senza auto, calcola la prossima mossa al click del pulsante "Successivo"
            if (self.player_types.get("Blue") == "ai" and self.player_types.get("Red") == "ai") and not self.auto_mode:
                if not self.game.is_terminal(self.current_state()):
                    self.play_turn()
                    self.update_board()

    def toggle_auto(self):
        self.auto_mode = not self.auto_mode
        if self.auto_mode:
            self.auto_button.config(text="Auto ON",highlightbackground="green")
            threading.Thread(target=self.auto_play, daemon=True).start()
        else:
            self.auto_button.config(text="Auto",highlightbackground="red")

    def auto_play(self):
        while self.auto_mode and not self.game.is_terminal(self.state_history[-1]):
            self.play_turn()
            time.sleep(0.5)
        if self.game.is_terminal(self.state_history[-1]):
            self.show_game_over("La partita è terminata.")
            #messagebox.showinfo("Fine partita", "La partita è terminata.")

    # Funzione per eseguire il turno del giocatore.
    def play_turn(self):
        state = self.state_history[-1]
        if self.game.is_terminal(state):
            return
        current_player = state.to_move
        legal_moves = self.game.actions(state)
        move = None
        if self.player_types[current_player] == "ai":
            if current_player == "Blue":
                future = self.executor.submit(playerBmodule.playerStrategy, self.game, state)
            else:
                future = self.executor.submit(playerRmodule.playerStrategy, self.game, state)
            # Attendi il risultato della funzione di strategia dell'AI
            # Se il risultato non arriva entro il timeout, scegli una mossa casuale
            # e mostra un messaggio di timeout
            try:
                move = future.result(timeout=self.time_out)
                #debug
                print(f"AI {current_player} ha scelto la mossa {move}\n")
            except concurrent.futures.TimeoutError:
                future.cancel()
                move = None
            if move is None:
                move = random.choice(legal_moves)
                print(f"Time-out per {current_player}, effettuata mossa casuale {move}\n")
        else:
            self.waiting_for_human = True
            self.human_move = None
            # Evidenzia le celle su cui è possibile muovere
            for m in legal_moves:
                (r, c) = m[0]
                self.cells[r][c].config(bg="white")
            while self.waiting_for_human:
                self.root.update()
                time.sleep(0.1)
            move = self.human_move
            self.update_board()
        new_state = self.game.result(state, move)
        self.state_history.append(new_state)
        self.current_index = len(self.state_history) - 1
        self.update_board()
        if self.game.is_terminal(new_state):
            util = self.game.utility(new_state)
            winner = "Blue" if util == 1 else "Red"

    # Loop di gioco: se non siamo in modalità AI vs AI senza auto, avvia il loop.
    def run_game_loop(self):
        if not (self.player_types.get("Blue") == "ai" and self.player_types.get("Red") == "ai" and not self.auto_mode):
            def loop():
                while not self.game.is_terminal(self.state_history[-1]):
                    self.play_turn()
                    time.sleep(0.1)
            threading.Thread(target=loop, daemon=True).start()
        self.root.mainloop()


    def show_game_over(self, message):
        dialog = tk.Toplevel(self.root)
        dialog.title("Fine partita")
        dialog.geometry("300x150")
        
        tk.Label(dialog, text=message, font=("Helvetica", 12), pady=20).pack()
        
        ok_button = tk.Button(dialog, text="OK", command=dialog.destroy, 
                            font=("Helvetica", 12), height=1)
        ok_button.pack(pady=10)
        
        dialog.transient(self.root)
        dialog.grab_set()
        self.root.wait_window(dialog)

# Funzione principale: chiede la modalità e il primo giocatore, quindi avvia l'interfaccia.
def main():
    root = tk.Tk()
    root.withdraw()
    mode = simpledialog.askinteger("Seleziona modalità", 
        "Seleziona modalità:\n1: Umano vs Umano\n2: Umano vs AI\n3: AI vs AI", minvalue=1, maxvalue=3)
    first = simpledialog.askstring("Primo giocatore", "Inserisci il primo giocatore (Blue o Red):", parent=root)
    first = first.capitalize()
    if first in "Red":
        first = "Red"
    else:
        first = "Blue"
    
    if mode == 1:
        player_types = {"Blue": "human", "Red": "human"}
    elif mode == 2:
        human_player = simpledialog.askstring("Giocatore umano", "Quale giocatore è umano? (Blue o Red):", parent=root)
        human_player = human_player.capitalize()
        if human_player in "Red":
            human_player = "Red"
        else:
            human_player = "Blue"
        
        player_types = {"Blue": "human" if human_player == "Blue" else "ai",
                        "Red": "human" if human_player == "Red" else "ai"}
    else:
        player_types = {"Blue": "ai", "Red": "ai"}
    root.destroy()
    
    game = CephalopodGame(size=5, first_player=first)
    gui = CephalopodGUI(game, player_types, time_out=3)
    gui.run_game_loop()

if __name__ == '__main__':
    main()
