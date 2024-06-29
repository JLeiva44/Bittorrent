import hashlib
import math 
import time 
import logging
import zmq

from subpiece import SubPiece, SUBPIECE_SIZE, State

class Piece:
    def __init__(self, piece_index:int, piece_size:int, piece_hash :str) -> None:
        self.piece_index:int = piece_index
        self.piece_size:int = piece_size
        self.piece_hash :str = piece_hash
        self.is_full: bool = False
        self.files = []
        self.raw_data:bytes = b''
        self.number_of_subpieces:int = int(math.ceil(float(piece_size) / SUBPIECE_SIZE))
        self.subpieces : list[SubPiece] = []

        self._init_subpieces()


    def _init_subpieces(self): # see this
        for i in range(len(self.subpieces)-1):
            self.subpieces.append(SubPiece(subpiece_size=SUBPIECE_SIZE))

        self.subpieces.append(SubPiece(subpiece_size=self.piece_size%SUBPIECE_SIZE))        


    def get_empty_subpiece(self):
        if self.is_full:
            return None
        
        for index,subpiece in enumerate(self.subpieces):
            if subpiece.state == State.FREE:
                self.subpieces[index].state = State.PENDING
                self.subpieces[index].last_seen = time.time()
                return self.piece_index, index*SUBPIECE_SIZE, subpiece.subpiece_size
            
        return None

    def all_subpieces_full(self):
        for subpiece in self.subpieces:
            if subpiece.state == State.FREE or subpiece.state == State.PENDING:
                return False
        return True

    def get_subpiece(self, subpiece_offset, subpiece_length):
        return self.raw_data[subpiece_offset:subpiece_length]

    def set_subpiece(self, offset, data):
        index = int(offset/SUBPIECE_SIZE)

        if not self.is_full and not self.subpieces[index].state == State.FULL:
            self.subpieces[index].data = data
            self.subpieces[index].state = State.FULL        

    def update_subpiece_status(self): # if block is pending for too long: set it free
        for i, subpiece in enumerate(self.subpieces):
            if subpiece.state == State.PENDING and (time.time() - subpiece.last_seen)>5:
                self.subpieces[i] = SubPiece()

    def _merge_subpieces(self):
        data = b''

        for subpiece in self.subpieces:
            data += subpiece.data

        return data     


    def _valid_subpieces(self,raw_data):
        hashed_piece_raw_data = hashlib.shal(raw_data).digest()
        if hashed_piece_raw_data == self.piece_hash:
            return True

        logging.warning("Error Piece Hash")       
        logging.debug("{} : {}".format(hashed_piece_raw_data, self.piece_hash))
        return False

    def _wite_piece_on_disk(self):
        for file in self.files:
            file_path = file["path"]
            file_offset = file["fileOffset"]
            piece_offset = file["pieceOffset"]
            length = file["length"]

            try:
                f = open(file_path, 'r+b') # Already existing file
            except IOError:
                f = open(file_path, 'wb') # new file
            except Exception:
                logging.exception("Can't write to file")
                return 

            f.seek(file_offset)
            f.write(self.raw_data[piece_offset:piece_offset+length])
            f.close()
                        



