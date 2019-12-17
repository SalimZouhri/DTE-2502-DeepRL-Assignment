'''
This script stores the game environment. Note that the snake is a part of the
environment itself in this implementation.
The environment state is a set of frames, we want the agent to be able to discern
the movement of the snake as well, for which multiple frames are needed.
We will keep track of a history of 2 frames.
Important to manually reset the environment by user after initialization.
The board borders are different from board color
The player cannot play infinitely, and hence max time limit is imposed
'''

import numpy as np
from collections import deque
import matplotlib.pyplot as plt

class Snake:
    '''
    Class for the snake game.
    Attributes:
        size (int) : size of the game board, assumed to be square
        board : numpy array containing information about various objects in the
                board, including snake, food and obstacles
        snake_length (int) : current length of the snake
        snake_head (int, int) : Position containing the row and column no of board
                                for snake head
        food (int, int) : Position containing the coordinates for the food
        snake_direction (int) : direction (left:2, right:0, up:1, down:3) where
                                   snake is moving
        snake (queue) : a queue to store the positions of the snake body
    '''
    def __init__(self, board_size=10, frames=2, games=10, start_length=5, seed=42,
                 max_time_limit=298):
        '''
        Initialization function for the environment.
        '''
        # self._value = {'snake':255, 'board':0, 'food':128, 'head':180, 'border':80}
        self._value = {'snake':1, 'board':0, 'food':3, 'head':2, 'border':4}
        # self._actions = [-1, 0, 1] # -1 left, 0 nothing, 1 right
        self._actions = {-1:-1, 0:0, 1:1, 2:2, 3:3, 4:-1}
        self._n_actions = 4 # 0, 1, 2, 3
        self._board_size = board_size
        self._n_frames = frames
        self._n_games = games
        self._rewards = {'out':-1, 'food':1, 'time':0, 'no_food':0}
        # start length is constrained to be less than half of board size
        self._start_length = min(start_length, (board_size-2)//2)
        # set numpy seed for reproducible results
        # np.random.seed(seed)
        # time limit to contain length of game, -1 means run till end
        self._max_time_limit = max_time_limit
        # other variables that can be quickly reused across multiple games
        self._border = self._value['board'] * np.ones((self._board_size-2,self._board_size-2))
        # make board borders
        self._border = np.pad(self._border, 1, mode='constant',
                              constant_values=self._value['border'])\
                          .reshape(1,self._board_size,self._board_size)
        self._border = np.zeros((self._n_games, self._board_size, self._board_size)) \
                        + self._border
        # queue for board
        self._board = deque(maxlen = self._n_frames)
        # define the convolutions for movement operations
        self._action_conv = np.zeros((3,3,self._n_actions), dtype=np.uint8)
        self._action_conv[1,0,0] = 1
        self._action_conv[2,1,1] = 1
        self._action_conv[1,2,2] = 1
        self._action_conv[0,1,3] = 1

    def _queue_to_board(self):
        '''
        Convert the current queue of frames to a tensor
        Returns:
            board : np array of 4 dimensions
        '''
        board = np.stack([x for x in self._board], axis=3)
        return board.copy()

    def _calculate_board(self):
        ''' combine all elements together to get the board '''
        board = self._border + (self._body > 0)*self._value['snake'] + \
                self._head*self._value['head'] + self._food*self._value['food']
        return board.copy()

    def _set_first_frame(self):
        self._board[0] = self._calculate_board()

    def print_game(self):
        ''' prints the current state (board) '''
        board = self._queue_to_board()
        fig, axs = plt.subplots(self._n_games, self._n_frames)
        if(self._n_games == 1 and self._n_frames == 1):
            axs.imshow(board[0], cmap='gray')
        elif(self._n_games == 1):
            for i in range(self._n_frames):
                axs[i].imshow(board[0,:,:,i], cmap='gray')
        elif(self._n_frames == 1):
            for i in range(self._n_games):
                axs[i].imshow(board[i,:,:,0], cmap='gray')
        else:
            for i in range(self._n_games):
                for j in range(self._n_frames):
                    axs[i][j].imshow(board[i,:,:,j], cmap = 'gray')
        plt.show()

    def get_board_size(self):
        ''' get board_size '''
        return self._board_size

    def get_n_frames(self):
        ''' get frame count '''
        return self._n_frames

    def get_head_value(self):
        ''' get color of head '''
        return self._value['head']

    def get_values(self):
        return self._value

    def reset(self):
        '''
        reset the environment
        Returns:
            board : the current board state
        '''
        # initialize snake, head takes the value 1 always
        self._body = np.zeros((self._n_games, self._board_size, self._board_size))
        self._food, self._head = self._body.copy().astype(np.uint8), self._body.copy().astype(np.uint8)
        self._snake_length = self._start_length
        self._count_food = 0
        # assume snake is just head + 1 body initially, place randomly across games
        self._body[:,self._board_size//2, 1:self._snake_length] = \
            np.arange(self._snake_length-1,0,-1).reshape(1,1,-1)
        self._head[:, self._board_size//2, self._snake_length] = 1
        self._snake_direction = np.zeros((self._n_games,), dtype=np.uint8)
        # first view of the board
        board = self._calculate_board()
        # initialize the queue
        for _ in range(self._n_frames):
            self._board.append(board.copy())
        # modify the food position on the board, after board queue initialized
        self._get_food()
        # set time elapsed to 0
        self._time = np.zeros((self._n_games,1))
        return self._queue_to_board()

    def get_num_actions(self):
        ''' get total count of actions '''
        return self._n_actions

    def _action_map(self, action):
        ''' converts integer to internal action mapping '''
        return self._actions[action]

    def _get_snake_tail(self):
        '''
        get the head of the snake, right most element in the queue
        Returns:
        head : Position of the head
        '''
        return self._snake[0]

    def _get_food(self):
        '''
        find the coordinates of the point to put the food at
        places which are occupied by the board
        '''
        board = self._board[0]
        seq = np.arange(0,(self._n_games * (self._board_size**2)))
        np.random.shuffle(seq)
        food_pos = (board == self._value['board']) * seq.reshape(self._n_games,self._board_size,self._board_size)
        m = food_pos.max((1,2)).reshape(self._n_games,1,1)
        food_pos = ((food_pos == m) & (food_pos > self._value['board']))
        m = self._food.max((1,2)).reshape(self._n_games,1,1)
        self._food = (food_pos * (1-m) + self._food * m).astype(np.uint8)
        self._set_first_frame()

    def _get_new_direction(self, action, current_direction):
        '''
        get the new direction after taking the specified action
        Returns:
            direction (int) : the new direction of motion
        '''
        new_dir = current_direction.copy()
        f = (np.abs(action - current_direction) != 2) & (action != -1)
        new_dir[f] = action[f]
        return new_dir.copy()

    def _get_new_head(self, action, current_direction):
        '''
        get the position for the new head through the action
        first do convolution operations for all actions, then use
        one hot encoded actions for each game to get the final position of the new head
        Returns:
            new_head (Position) : position class for the new head
        '''
        action = self._get_new_direction(action, current_direction)
        one_hot_action = np.zeros((self._n_games,1,1,self._n_actions), dtype=np.uint8)
        one_hot_action[np.arange(self._n_games), :, :, action] = 1
        hstr = self._head.strides
        new_head = np.lib.stride_tricks.as_strided(self._head, 
                       shape=(self._n_games,self._board_size-3+1,self._board_size-3+1,3,3),
                       strides=(hstr[0],hstr[1],hstr[2],hstr[1],hstr[2]))
                       # strides determine how much steps are needed to reach the next element
                       # in that direction, to decide strides for the function, visualize
                       # with the expected output
        new_head = np.tensordot(new_head, self._action_conv) # where conv is (3,3,4)
        new_head = np.pad((new_head * one_hot_action).sum(3),
                        1,mode='constant', constant_values=0)[1:-1] # sum along last axis
        return new_head.copy()

    def step(self, action):
        '''
        takes an action and performs one time step of the game, returns updated
        board
        Arguments:
            action (int) : should be among the possible actions
        Returns:
            board : updated after taking the step
            reward : agent's reward for performing the current action
            done : whether the game is over or not (1 or 0)
            info : any auxillary game information
        '''
        # assert action in list(range(self._n_actions)), "Action must be in " + list(range(self._n_actions))
        # assert action in self._actions, "Action must be in " + [k for k in self._actions]
        reward, done = np.zeros((self._n_games,1)), np.zeros((self._n_games,1))

        # check if the current action is feasible
        reward, done, can_eat_food, termination_reason = self._check_if_done(action)
        if(done == 0):
            # if not done, move the snake
            self._move_snake(action, can_eat_food)
            # update the direction of motion
            self._snake_direction = self._get_new_direction(action, self._snake_direction)
            # get the next food location
            if(can_eat_food):
                self._get_food()

        # update time
        self._time += 1
        # info contains time elapsed etc
        info = {'time':self._time, 'food':self._count_food,
                'termination_reason':termination_reason}


        return self._queue_to_board(), reward, done, info

    def _get_food_reward(self):
        ''' try different rewards schemes for when food is eaten '''
        # return((self._snake_length - self._start_length + 1) * self._rewards['food'])
        return self._rewards['food']

    def _get_death_reward(self):
        ''' try different rewards schemes for death '''
        # return((self._snake_length - self._start_length + 1) * self._rewards['out'])
        return self._rewards['out']

    def _check_if_done(self, action):
        '''
        checks if the game has ended or if food has been taken
        Returns:
            reward : reward for the current action
            done : 1 if ended else 0
            can_eat_food : whether the current action leads to eating food
        '''
        reward, done, can_eat_food, termination_reason = \
                            self._rewards['time'] * np.ones((self._n_games,1)),\
                            np.zeros((self._n_games,1)), np.zeros((self._n_games,1)), ['']*self._n_games
        # check if the current action forces snake out of board
        new_head = self._get_new_head(action, self._snake_direction)
        while(1):
            # check if no position available for food
            if((self._board[0] == self._value['board']).sum() == 0 and \
               (self._board[0] == self._value['food']).sum() == 0):
                done = 1
                reward += self._get_food_reward()
                termination_reason = 'game_end'
                break
            # snake is colliding with border/obstacles
            if(self._board[0][new_head.row, new_head.col] == self._value['border']):
                done = 1
                reward = self._get_death_reward()
                termination_reason = 'collision_wall'
                break
            # collision with self, collision with tail is allowed
            if(self._board[0][new_head.row, new_head.col] == self._value['snake']):
                snake_tail = self._get_snake_tail()
                if(not(new_head.row == snake_tail.row and new_head.col == snake_tail.col)):
                    done = 1
                    reward = self._get_death_reward()
                    termination_reason = 'collision_self'
                    break
            # check if food
            if(self._board[0][new_head.row, new_head.col] == self._value['food']):
                done = 0
                reward += self._get_food_reward()
                self._count_food += 1
                can_eat_food = 1
            # check if time up
            if(self._time >= self._max_time_limit and self._max_time_limit != -1):
                done = 1
                # check if no food eaten
                if(self._snake_length == self._start_length and self._rewards['no_food'] != 0):
                    termination_reason = 'time_up_no_food'
                    reward += self._rewards['no_food']
                else:
                    termination_reason = 'time_up'
                break
            # if normal movement, no other updates needed
            break
        return reward, done, can_eat_food, termination_reason

    def _move_snake(self, action, can_eat_food):
        '''
        moves the snake using the given action
        and updates the board accordingly
        '''
        # get the coordinates for the new head
        new_head = self._get_new_head(action, self._snake_direction)
        # prepare new board as the last frame
        new_board = self._board[0].copy()
        # modify the next block of the snake body to be same color as snake
        new_board[self._snake_head.row, self._snake_head.col] = self._value['snake']
        # insert the new head into the snake queue
        # different treatment for addition of food
        # update the new board view as well
        # if new head overlaps with the tail, special handling is needed
        self._snake.append(new_head)
        self._snake_head = new_head

        if(can_eat_food):
            self._snake_length += 1
        else:
            delete_pos = self._snake.popleft()
            new_board[delete_pos.row, delete_pos.col] = self._value['board']
        # update head position in last so that if head is same as tail
        # the update is still correct
        new_board[new_head.row, new_head.col] = self._value['head']
        self._board.appendleft(new_board.copy())