from enum import Enum

DEFAULT_SUBPIECE_SIZE = 16383 # 16kb = 16383 bits = 2^14 bits)

class State(Enum):
    FREE = 0
    PENDING = 1
    FULL = 2

class SubPiece:
    def __init__(self, state : State = State.FREE, subpiece_size: int = DEFAULT_SUBPIECE_SIZE, data:bytes = b'', last_seen:float = 0 ) -> None:
        self.state = state
        self.subpiece_size = subpiece_size
        self.data= data

    def update_subpiece_status(self, new_state: State)   :
        self.state = new_state 

    def __getState__(self):
        return {
            'data': self.data,
            'subpiece_size' : self.subpiece_size,
            'self.state': self.state 
        }

    def __setstate__(self, state):
        self.data = state['data']
        self.subpiece_size = state['subpiece_size']
        self.state = state['state']    

    def __str__(self):

        return "%s - %d - %d - %d" % (self.state, self.subpiece_size, len(self.data), self.last_seen)    

