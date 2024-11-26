from enum import Enum

DEFAULT_Block_SIZE = 1<<14 # 16kb = 16383 bits = 2^14 bits)

class State(Enum):
    FREE = 0
    PENDING = 1
    FULL = 2

class Block:
    def __init__(self, state : State = State.FREE, block_size: int = DEFAULT_Block_SIZE, data:bytes = b'', last_seen:float = 0 ) -> None:
        self.state = state
        self.block_size = block_size
        self.data= data

    def update_block_status(self, new_state: State)   :
        self.state = new_state 

    def __getState__(self):
        return {
            'data': self.data,
            'block_size' : self.block_size,
            'self.state': self.state 
        }

    def __setstate__(self, state):
        self.data = state['data']
        self.block_size = state['block_size']
        self.state = state['state']    

    def __str__(self):

        return "%s - %d - %d - %d" % (self.state, self.block_size, len(self.data), self.last_seen)    

