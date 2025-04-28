
#import playingStrategies
import random

# import game
#from board import Board,draw_board

def playerStrategy (game,state):
    return random.choice(list(game.actions(state)))


