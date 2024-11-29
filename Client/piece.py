import hashlib
import math 
import time 
import logging
#import zmq
from Client.disk_io import DiskIO


from Client.block import Block, DEFAULT_Block_SIZE, State

class Piece:
    def __init__(self, piece_index:int, piece_offset, piece_size:int, piece_hash :str) -> None:
        
        self.piece_index = piece_index
        self.piece_offset = piece_offset
        self.piece_size = piece_size
        self.piece_hash = piece_hash
        self.is_full = False
        self.files = []
        self.raw_data:bytes = b''
        self.number_of_blocks:int = int(math.ceil(float(piece_size) / DEFAULT_Block_SIZE))
        self.is_completed = False
        self.blocks : list[Block] = self._init_blocks()


    @property
    def in_memory(self):
        return self.raw_data != b''  
    
    def put_data(self, data):
        self.raw_data = data
        self.is_full = True
    
    @property
    def have_all_blocks(self):
        '''
            If all blocks of the piece succefully downloaded
        '''
        return all(sub.state == State.FULL for sub in self.blocks) 

    def write_block(self, offset, data):
        index = offset// DEFAULT_Block_SIZE

        if not self.is_full and not self.blocks[index].state == State.FULL:
            self.blocks[index].data = data
            self.blocks[index].state = State.FULL

        if self.have_all_blocks:
            self._merge_all_blocks()  
    
    def _init_blocks(self): # see this
        result  = []
        for _ in range(self.number_of_blocks -1):
            result.append(Block(block_size=DEFAULT_Block_SIZE))

        result.append(Block(block_size= self.piece_size % DEFAULT_Block_SIZE))
        return result

    def _merge_blocks(self):
        data = b''

        for block in self.blocks:
            data += block.data

        return data   

    def _valid_blocks(self,raw_data):
        hashed_piece_raw_data = hashlib.sha1(raw_data).hexdigest() # hexdigest??
        if hashed_piece_raw_data == self.piece_hash:
            return True

        # logging.warning("Error Piece Hash")       
        # logging.debug("{} : {}".format(hashed_piece_raw_data, self.piece_hash))
        return False
    
    def _merge_all_blocks(self):
        raw_data = self._merge_blocks()
        if self._valid_blocks(raw_data):
            self.is_full = True
            self.raw_data = raw_data
            # logger. debug(....)
        else:
            self.blocks = self._init_blocks()

    def _rebuild_blocks(self):
        a = type(self.raw_data)
        for i in range(self.number_of_blocks -1):
            self.blocks[i] = Block(state=State.FREE, data=b'')  # data debe ser bytes
            self.blocks[i].data = self.raw_data[i * DEFAULT_Block_SIZE: (i+1)* DEFAULT_Block_SIZE]
        self.blocks[self.number_of_blocks - 1].data = self. raw_data[(self.number_of_blocks-1)* DEFAULT_Block_SIZE:]     
        #espacio
        a = 5
    def get_block(self, block_offset):
        block_index = block_offset // DEFAULT_Block_SIZE
        return self.blocks[block_index]
    
    def load_from_disk(self, filename : str):

        piece_data = DiskIO.read_from_disk(filename, self.piece_offset, self.piece_size)
        self.raw_data = piece_data
        self._rebuild_blocks()

    def clean_memory(self):
        self.raw_data = b''    

    def get_empty_block(self):
        if self.is_completed:
            return None
        
        for index, block in enumerate(self.blocks):
            if block.state == State.FREE:
                self.blocks[index].state = State.PENDING
                return index * DEFAULT_Block_SIZE, self.blocks[index].block_size
        
        return None     
    
    def all_blocks_full(self):
        for block in self.blocks:
            if block.state == State.FREE or block.state == State.PENDING:
                return False
        return True


    # def set_block(self, offset, data):
    #     index = int(offset/DEFAULT_block_SIZE)

    #     if not self.is_full and not self.blocks[index].state == State.FULL:
    #         self.blocks[index].data = data
    #         self.blocks[index].state = State.FULL        

    def update_block_status(self): # if block is pending for too long: set it free
        for i, block in enumerate(self.blocks):
            if block.state == State.PENDING and (time.time() - block.last_seen)>5:
                self.blocks[i] = Block()

   
   

    
