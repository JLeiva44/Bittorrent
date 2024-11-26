from Client.torrent import TorrentMaker, Torrent
from Client.pieces_manager import PiecesManager
from Client.subpiece import State, DEFAULT_SUBPIECE_SIZE, SubPiece
from Client.bclient_logger import logger

import os
import zmq
import json
import time
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
    def __init__(self, ip, port, peer_id = None) -> None:
        self.peer_id = peer_id
        self.ip = ip
        self.port = port
        self.peers = []
        self.context = zmq.Context()
        self.socket = self.context.socket(zmq.REQ)
        self.server_socket = self.context.socket(zmq.REP)

        #threading.Thread(target=self.run_server, daemon=True).start() # Start Peer server thread

    def connect(self, ip, port):
        address = "tcp://" + ip + ":" + port

    def run_server(self):
        # El cliente actúa como servidor escuchando en un puerto aleatorio
        self.server_socket.bind("tcp://*:5556")  # Puerto fijo para simplificar
        print(f"Servidor de peer escuchando en tcp://*:5556")
        
        while True:
            message = self.server_socket.recv_json()
            print(f"Mensaje recibido de otro peer: {message}")
            # Aquí puedes manejar la lógica de intercambio de archivos o cualquier otra operación
            ## AQUI VER EL CODIGO DE LA OPERACION QUE ES PARA EJECUTAR LAS TALlALS

            action_type = message.get("action")

            if action_type == "get_bit_field":
                response = self.get_bit_field_of()
                self.server_socket.send_json(response)

            elif action_type == "get_block": 
                response = self.get_block_of_piece(message['info'], message['piece_index'], message['block_offset'])  
                self.server_socket.send_json(response)  

            # Responder al peer (puedes modificar según la lógica deseada)
            self.server_socket.send_json({"status": "received"})

    def upload_file(self, path, tracker_urls, private=False, comments="unknown", source="unknown"):
        torrent_maker = TorrentMaker(path, 1 << 18, private, tracker_urls, source)
        #sha1_hash = torrent_maker.get_hash_pieces()
        sha1_hash = torrent_maker.pieces
        torrent_maker.create_file('torrent_files')
        
        trackers = [tuple(url.split(':')) for url in tracker_urls]
        self.update_trackers(trackers, sha1_hash)

    def update_trackers(self, trackers, sha1, remove: bool = False):
        for tracker_ip, tracker_port in trackers:
            self.connect_to_tracker(tracker_ip, tracker_port, sha1, remove)    

    def connect_to_tracker(self, tracker_ip, tracker_port, sha1, remove):
        tracker_socket = self.context.socket(zmq.REQ)
        tracker_socket.connect(f"tcp://{tracker_ip}:{tracker_port}")
        
        if remove:
            request = {"action": "remove_from_database", "sha1": sha1, "peer": (self.ip, self.port)}
        else:
            request = {"action": "add_to_database", "sha1": sha1, "peer": (self.ip, self.port)}

        tracker_socket.send_json(request)
        response = tracker_socket.recv_json()
        print(f"Tracker response: {response}")

    # def register(self):
    #     message = {
    #         "action": "register",
    #         "peer_id": self.peer_id,
    #         "file_hash": self.file_hash
    #     }
    #     print("Registrando peer...")
    #     self.socket.send_json(message)
    #     response = self.socket.recv_json()
    #     print("Respuesta del tracker: {}".format(response))

    