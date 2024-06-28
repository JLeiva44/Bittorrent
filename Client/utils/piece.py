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


    def _init_subpieces(self):
        for i in range(len(self.subpieces)-1):
            self.subpieces.append(SubPiece(subpiece_size=SUBPIECE_SIZE))

        self.subpieces.append(SubPiece(subpiece_size=self.piece_size%SUBPIECE_SIZE))        





