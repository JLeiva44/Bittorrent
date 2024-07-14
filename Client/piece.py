import hashlib
import math 
import time 
import logging
import zmq

from subpiece import SubPiece, SUBPIECE_SIZE, State

class Piece:
    def __init__(self, piece_index:int, piece_offset, piece_size:int, piece_hash :str) -> None:
        self.piece_index:int = piece_index
        self.piece_offset = piece_offset
        self.piece_size:int = piece_size
        self.piece_hash :str = piece_hash
        self.is_full: bool = False
        self.files = []
        self.raw_data:bytes = b''
        self.number_of_subpieces:int = int(math.ceil(float(piece_size) / SUBPIECE_SIZE))
        self.subpieces : list[SubPiece] = []

        self._init_subpieces()


    def _init_subpieces(self): # see this
        
        #if self.number_of_subpieces > 1:
        for i in range(self.number_of_subpieces -1):
            self.subpieces.append(SubPiece(subpiece_size=SUBPIECE_SIZE))

            # Last subpiece of last piece, the special block
        #if self.piece_size % SUBPIECE_SIZE > 0: # la ultima tiene el tamano que alcance
        self.subpieces.append(SubPiece(subpiece_size= self.piece_size % SUBPIECE_SIZE))

        # else: # 1 solo bloque => la pieza y la subpieza son del mismo tamano
        #     self.subpieces.append(SubPiece(subpiece_size=int(self.piece_size)))            

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

    def get_subpiece(self, subpiece_offset):
        subpiece_index = subpiece_offset // SUBPIECE_SIZE
        return self.subpieces[subpiece_index]

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

        # logging.warning("Error Piece Hash")       
        # logging.debug("{} : {}".format(hashed_piece_raw_data, self.piece_hash))
        return False
    
    @property
    def have_all_blocks(self):
        '''
            If all block of the piece succefully downloaded
        '''
        return all(sub.state == State.FULL for sub in self.subpieces) 
    
    def clean_memory(self):
        self.raw_data = b''

    def put_data(self, data):
        self.raw_data = data
        self.is_full = True

    @property
    def in_memory(self):
        return self.raw_data != b''  

    def load_from_disk(self, filename : str):

        # filename, self.piece_ofsset, self.piece_size
        new_file = open(filename, 'rb')
        new_file.seek(self.piece_offset)
        raw_data = new_file.read(self.piece_size)
        new_file.close()
        piece_data = raw_data      

        self.raw_data = piece_data
        self._rebuild_subpieces()

    def _rebuild_subpieces(self):
        for i in range(self.number_of_subpieces -1):
            self.subpieces[i].data = self.raw_data[i * SUBPIECE_SIZE: (i+1)* SUBPIECE_SIZE]
        self.subpieces[self.number_of_subpieces - 1].data = self. raw_data[(self.number_of_subpieces-1)* SUBPIECE_SIZE]    


    
    def write_subpiece(self, offset, data):
        index = offset// SUBPIECE_SIZE

        if not self.is_full and not self.subpieces[index].state == State.FULL:
            self.subpieces[index].data = data
            self.subpieces[index].state = State.FULL

        if self.have_all_blocks:
            self._merge_subpieces()    

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
                        



