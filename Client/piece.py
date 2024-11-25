import hashlib
import math 
import time 
import logging
#import zmq
from disk_io import DiskIO

from subpiece import SubPiece, DEFAULT_SUBPIECE_SIZE, State

class Piece:
    def __init__(self, piece_index:int, piece_offset, piece_size:int, piece_hash :str) -> None:
        
        self.piece_index = piece_index
        self.piece_offset = piece_offset
        self.piece_size = piece_size
        self.piece_hash = piece_hash
        self.is_full = False
        self.files = []
        self.raw_data:bytes = b''
        self.number_of_subpieces:int = int(math.ceil(float(piece_size) / DEFAULT_SUBPIECE_SIZE))
        self.subpieces : list[SubPiece] = self._init_subpieces()


    @property
    def in_memory(self):
        return self.raw_data != b''  
    
    def put_data(self, data):
        self.raw_data = data
        self.is_full = True
    
    @property
    def have_all_subpieces(self):
        '''
            If all subpieces of the piece succefully downloaded
        '''
        return all(sub.state == State.FULL for sub in self.subpieces) 

    def write_subpiece(self, offset, data):
        index = offset// DEFAULT_SUBPIECE_SIZE

        if not self.is_full and not self.subpieces[index].state == State.FULL:
            self.subpieces[index].data = data
            self.subpieces[index].state = State.FULL

        if self.have_all_subpieces:
            self._merge_all_subpieces()  
    
    def _init_subpieces(self): # see this
        result  = []
        for _ in range(self.number_of_subpieces -1):
            result.append(SubPiece(subpiece_size=DEFAULT_SUBPIECE_SIZE))

        result.append(SubPiece(subpiece_size= self.piece_size % DEFAULT_SUBPIECE_SIZE))
        return result

    def _merge_subpieces(self):
        data = b''

        for subpiece in self.subpieces:
            data += subpiece.data

        return data   

    def _valid_subpieces(self,raw_data):
        hashed_piece_raw_data = hashlib.sha1(raw_data).digest() # hexdigest??
        if hashed_piece_raw_data == self.piece_hash:
            return True

        # logging.warning("Error Piece Hash")       
        # logging.debug("{} : {}".format(hashed_piece_raw_data, self.piece_hash))
        return False
    
    def _merge_all_subpieces(self):
        raw_data = self._merge_subpieces()
        if self._valid_subpieces(raw_data):
            self.is_full = True
            self.raw_data = raw_data
            # logger. debug(....)
        else:
            self.subpieces = self._init_subpieces()

    def _rebuild_subpieces(self):
        for i in range(self.number_of_subpieces -1):
            self.subpieces[i].data = self.raw_data[i * DEFAULT_SUBPIECE_SIZE: (i+1)* DEFAULT_SUBPIECE_SIZE]
        self.subpieces[self.number_of_subpieces - 1].data = self. raw_data[(self.number_of_subpieces-1)* DEFAULT_SUBPIECE_SIZE]    
        
    def get_subpiece(self, subpiece_offset):
        subpiece_index = subpiece_offset // DEFAULT_SUBPIECE_SIZE
        return self.subpieces[subpiece_index]
    
    def load_from_disk(self, filename : str):

        piece_data = DiskIO.read_from_disk(filename, self.piece_offset, self.piece_size)
        self.raw_data = piece_data
        self._rebuild_subpieces()

    def clean_memory(self):
        self.raw_data = b''    

    def get_empty_subpiece(self):
        if self.is_completed:
            return None
        
        for index, block in enumerate(self.subpieces):
            if block.state == State.FREE:
                self.subpieces[index].state = State.PENDING
                return index * DEFAULT_SUBPIECE_SIZE, self.subpieces[index].subpiece_size
        
        return None     
    
    def all_subpieces_full(self):
        for subpiece in self.subpieces:
            if subpiece.state == State.FREE or subpiece.state == State.PENDING:
                return False
        return True


    # def set_subpiece(self, offset, data):
    #     index = int(offset/DEFAULT_SUBPIECE_SIZE)

    #     if not self.is_full and not self.subpieces[index].state == State.FULL:
    #         self.subpieces[index].data = data
    #         self.subpieces[index].state = State.FULL        

    def update_subpiece_status(self): # if block is pending for too long: set it free
        for i, subpiece in enumerate(self.subpieces):
            if subpiece.state == State.PENDING and (time.time() - subpiece.last_seen)>5:
                self.subpieces[i] = SubPiece()

   
   

    
    
     
   

    
        
   


print("sdkjbfdjbf")

