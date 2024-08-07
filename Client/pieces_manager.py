from piece import Piece
import os
import math
import hashlib
from torrent import Torrent

class PiecesManager:
    def __init__(self, torrent, path_to_download) -> None:
        info = dict(torrent.meta_info[b'info'])

        self.file_size = info[b'length']
        self.piece_size = info['piece length']
        self.filename = f"{path_to_download}/{info['name']}"
        self.number_of_pieces = math.ceil(self.file_size/self.piece_size)
        self.bitfield = [False for i in range(self.number_of_pieces)]
        self.completed_pieces = 0 
        self.pieces_hash = info['pieces'] # SHA1 of all pieces unioned
        self.pieces = []
        self.path = path_to_download

        self._build_pieces()
        self._check_local_pieces()


    @property
    def download_completed(self):
        return self.completed_pieces == self.number_of_pieces
    
    @property
    def amount_of_bytes_already_downloaded(self):
        total_downloaded = 0
        for piece in self.pieces:
            if piece.is_full:
                total_downloaded += self.piece_size

        return total_downloaded

    @property
    def is_file_completed(self):
        return self.number_of_pieces == self.completed_pieces

    @property
    def bytes_left(self):
        return self.file_size - self.amount_of_bytes_already_downloaded

    def get_piece(self, index):
        return self.pieces[index]

    def _build_pieces(self):
        for i in range(self.number_of_pieces):
            piece_offset = self.piece_size * i
            starthash_index = i * 40 # ver esto
            piece_hash = self.pieces_hash[starthash_index: starthash_index + 40]
            piece_size = self.file_size % self.piece_size if i == self.number_of_pieces -1 else self.piece_size
            piece = Piece(i,piece_offset, piece_size, piece_hash)
            self.pieces.append(piece)           


    def _check_local_pieces(self):
        path = self.filename
        if os.path.exists(path):
            for index in range(self.number_of_pieces):
                with open(path, 'rb') as f:
                    chunk = f.read(self.piece_size)
                    while chunk:
                        sha1_chunk = hashlib.sha1(chunk).digest()
                        piece : Piece = self.pieces[index]
                        if sha1_chunk == piece.piece_hash :
                            self.bitfield[index] = True
                            piece.is_full = True
                            self.completed_pieces+=1
                        chunk = f.read(self.piece_size)
        else: # build new file
            f = open(path,"wb")
            f.seek(self.file_size-1)
            f.write(b"\0")
            f.close()


    def receive_subP_of_piece(self, piece_index, subpiece_offset, raw_data):

        if not self.bitfield[piece_index]:
            piece = self.pieces[piece_index]
            piece.write_subpiece(subpiece_offset, raw_data)

            if piece.is_full:
                self.bitfield[piece_index] = True
                self.completed_pieces+=1

                # Write in disk
                new_file = open(self.filename, 'r+b')
                new_file.seek(piece.piece_offset)
                new_file.write(piece.raw_data)
                new_file.close()            

    def get_subP_of_piece(self, piece_index, supiece_offset):
        piece : Piece = self.pieces[piece_index]

        if not piece.in_memory:
            piece.load_from_disk(self.filename)

        subpiece = piece.get_subpiece(supiece_offset)    
        return subpiece


    def clean_memory(self, piece_index):
        piece: Piece = self.pieces[piece_index]

        if not piece.in_memory:
            piece.clean_memory()    


