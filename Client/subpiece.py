from enum import Enum

SUBPIECE_SIZE = 16383 # 16kb = 16383 bits = 2^14 bits)

class State(Enum):
    FREE = 0
    PENDING = 1
    FULL = 2

class SubPiece:
    def __init__(self, state : State = State.FREE, subpiece_size: int = SUBPIECE_SIZE, data:bytes = b'', last_seen:float = 0 ) -> None:
        self.state:State = state
        self.subpiece_size:int = subpiece_size
        self.data: bytes = data
        self.last_seen:float = last_seen

    def update_status(self, new_state)   :
        pass 

    def __str__(self):

        return "%s - %d - %d - %d" % (self.state, self.subpiece_size, len(self.data), self.last_seen)    

