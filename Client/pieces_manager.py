from Client.piece import Piece
from Client.disk_io import DiskIO
import os
import math
import hashlib
from Client.torrent_utils import TorrentInfo
import bitstring

class PieceManager:

    def __init__(self, info, save_at):
        '''
            Initialize the piece manager
        '''
        info = dict(info)
        print(info)
        self.file_size = info['length'] # The file size
        self.piece_size = info['piece length'] # The piece size
        self.filename = f"{save_at}/{info['name']}" # The file name
        self.number_of_pieces = math.ceil(self.file_size/self.piece_size) # The number of pieces of the file
        self.bitfield = [False for i in range(self.number_of_pieces)] # Bitfield of the pieces
        self.completed_pieces: int = 0 # Number of pieces that are completed
        self.dottorrent_pieces = info['pieces'] # SHA1 of the all pieces unioned
        self.pieces: list[Piece] = self.__build_pieces() # List of pieces
        self.save_at = save_at # The path where the file will be downloaded
        self.__run()

    def __run(self):
        self.__check_local_pieces()

    @property
    def downloaded(self):
        '''
            The total amount of bytes downloaded
        '''
        total_downloaded = 0
        for piece in self.pieces:
            if piece.is_completed:
                total_downloaded += self.piece_size
        
        return total_downloaded

    @property
    def completed(self):
        '''
            If the file is completed
        '''
        return self.number_of_pieces == self.completed_pieces
    
    @property
    def left(self):
        '''
            The number of bytes needed to download to be 100% complete and 
            get all the included files in the torrent.
        '''
        return self.file_size - self.downloaded
        
    
    

    def get_piece(self, piece_index):
        '''
            Get a piece from the piece manager
        '''
        return self.pieces[piece_index]

    def __build_pieces(self):
        '''
            Build the pieces
        '''
        pieces = []
        for i in range(self.number_of_pieces):
            piece_offset = self.piece_size*i
            starthash_index = i * 40
            piece_hash = self.dottorrent_pieces[starthash_index: starthash_index+40]
            piece_size = self.file_size % self.piece_size if i == self.number_of_pieces - 1 else self.piece_size
            piece = Piece(i, piece_offset, piece_size, piece_hash)
            pieces.append(piece)
        return pieces
        

    def __check_local_pieces(self):
        path = self.filename
        if os.path.exists(path):
            for piece_index in range(self.number_of_pieces):
                with open(path, 'rb') as f:
                    chunk = f.read(self.piece_size)
                    while(chunk):
                        sha1chunk = hashlib.sha1(chunk).hexdigest()
                        print('este es el sha1', sha1chunk)
                        piece: 'Piece' = self.pieces[piece_index]
                        print('este es el sha1 de la pieza segun la metainfo', piece.piece_hash)
                        if sha1chunk == piece.piece_hash:  # This piece is already written in the file
                            self.bitfield[piece_index] = True
                            piece.is_completed = True
                            self.completed_pieces += 1
                        chunk = f.read(self.piece_size)
        else:
            DiskIO.build_new_file(path, self.file_size)

    def receive_block_piece(self, piece_index, block_offset, raw_data):

        if not self.bitfield[piece_index]:
            piece: Piece = self.pieces[piece_index]
            piece.write_block(block_offset, raw_data)
    
            if piece.is_completed:
                self.bitfield[piece_index] = True
                self.completed_pieces += 1
                DiskIO.write_to_disk(self.filename, piece.piece_offset, piece.raw_data)

    def get_block_piece(self, piece_index, block_offset):
        piece: Piece = self.pieces[piece_index]
        if not piece.in_memory:
            piece.load_from_disk(self.filename)
        
        block = piece.get_block(block_offset)
        return block
    
    def clean_memory(self, piece_index):
        '''
            Clean the memory of a piece
        '''
        piece: Piece = self.pieces[piece_index]
        if not piece.in_memory:
            piece.clean_memory()
    
