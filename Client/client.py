from torrent import TorrentMaker, Torrent
from pieces_manager import PiecesManager
from subpiece import State, DEFAULT_SUBPIECE_SIZE, SubPiece
from bclient_logger import logger
import Pyro4
import os
#import zmq
import random
import threading
import math
import base64
HOST = '127.0.0.1'
LOCAL = 'localhost'
PORT1 = '8001'

PIECE_SIZE =  2**18 # 256 Kb (kilobibits) = 262144 bits

ACTUAL_PATH = os.getcwd()

class Client:
    def __init__(self, ip, port, client_id = None) -> None:
        self.id = client_id
        self.ip = ip
        self.port = port
        self.peers = []

    
    