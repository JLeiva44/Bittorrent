from piece import Piece
import os
import math
import hashlib
from torrent import Torrent

class PiecesManager:
    def __init__(self, torrent, path_to_download) -> None:
        info = dict(torrent.meta_info)

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
            starthash_index = i * 40
            piece_hash = self.pieces_hash[starthash_index: starthash_index + 40]
            piece_size = self.file_size % self.piece_size if i == self.number_of_pieces -1 else self.piece_size
            piece = Piece(i,piece_offset, piece_size, piece_hash)
            self.pieces.append(piece)           
