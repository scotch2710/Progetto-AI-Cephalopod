import playingStrategies
#import random
#import game

# The moves of player have the form (x,y), where y is the column number and x the row number (starting with 0)

def playerStrategy (game,state):
    cutOff = 3 # The depth of the search tree. It can be changed to test the performance of the player.
    # The player uses the alphabeta search algorithm to find the best move.
    value,move = playingStrategies.h_alphabeta_search(game,state,playingStrategies.cutoff_depth(cutOff))
  
    return move

