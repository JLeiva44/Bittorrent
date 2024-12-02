from torrent_utils import TorrentCreator, TorrentInfo, TorrentReader
from pieces_manager import PieceManager
from block import State, DEFAULT_Block_SIZE, Block
from bclient_logger import logger

import os
import zmq
import random
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
    def __init__(self, ip, port, peer_id ) -> None:
        self.id = peer_id
        self.ip = ip
        self.port = port
        self.peers = []
        self.context = zmq.Context()
        self.lock = threading.Lock() # Para sincronizar recursos compartidos

        logger.debug(f"Strating PeerServerThread")
        threading.Thread(target=self.run_server, daemon=True).start() # Start server thread
    
    def _send_data(self,request,ip, port, timeout = 5000) -> bytes:
        """Method for sending data to a Peer using ZMQ with timeout"""
        try:
            with self.context.socket(zmq.REQ) as s:
                s.connect(f'tcp://{ip}:{port}')
                s.send_json(request)

                poller = zmq.Poller()
                poller.register(s,zmq.POLLIN)

                if poller.poll(timeout):  # Espera hasta el timeout
                    return s.recv_json()
                else:
                    raise zmq.Again("Timeout while waiting for response")
        
        except zmq.Again as e:
            logger.warning(f"Timeout communicating with {ip}:{port} - {e}")
            return None
        except zmq.ZMQError as e:
            logger.error(f"ZMQError occurred: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error: {e}")
            return None
            

    def request_test(self, ip, port):
        request = {"action": "request_test"}
        response = self._send_data(request, ip, port)
        if response:
            logger.debug(f"Test successful. Peer ID: {response.get('id')}")

    def handshake(self, peer_ip, peer_port, info_hash):
        """Método para realizar el handshake con otro peer."""
        # El mensaje de handshake incluye el protocolo, el peer_id y el info_hash
        handshake_message = {
            "action" : "handshake",
            "protocol": "BitTorrentco",  # Identificador del protocolo
            "peer_id": self.id,  # El ID del peer
            "info_hash": info_hash  # El hash del torrent
        }
        
        try:
            response = self._send_data(handshake_message, peer_ip, peer_port)
            if response and response.get('status') == 'handshake_success':
                logger.debug(f"Handshake exitoso con {peer_ip}:{peer_port}")
            else:
                logger.warning(f"Handshake fallido con {peer_ip}:{peer_port}")
            return response    
        except Exception as e:
            logger.error(f"Error en el handshake con {peer_ip}:{peer_port} - {e}")

   
    def run_server(self):
        """Mthod that initializes the Server that listen conexions from other Peers"""
        context = zmq.Context()
        server_socket = context.socket(zmq.REP)
        server_socket.bind(f'tcp://{self.ip}:{self.port}')

        while True:
            try:
                poller = zmq.Poller()
                poller.register(server_socket, zmq.POLLIN)


                if poller.poll(1000): # 1 segundo de timeout para no bloquear:
                    message = server_socket.recv_json()
                    action_type = message.get("action")
                    logger.debug(f"Received message {message} on {self.ip}:{self.port}")

                    #if action_type == 'handshake':

                    
                    if action_type == "get_bit_field":
                        response = self.get_bit_field_of(message['info'])
                        #logger.debug(f"GetBitfieldResponse: {response}")
                        server_socket.send_json(response)
                        
                    elif action_type == "get_block":
                        response = self.get_block_of_piece(message['info'], message['piece_index'], message['block_offset'])
                        #logger.debug(f"GetBlockResponse: {response}")
                        server_socket.send_json(response)

                    elif action_type == "request_test":
                        response = {'id':self.peer_id}
                        #logger.debug("Testing Request")
                        #Probando con el id
                        server_socket.send_json(response)    
                        
                    else:
                        server_socket.send_json({"error": "Unknown action"})
                else:
                    # No hay mensaje recibido
                    continue       
                
            except zmq.Again:
                # Timeout alcanzado, no hay mensaje recibido
                logger.debug("No message received within the timeout period.")
                continue  # Continúa esperando nuevos mensajes

            except zmq.ZMQError as e:
                logger.error(f"ZMQError occurred: {e}. Restarting server socket...")
                server_socket.close()
                server_socket = context.socket(zmq.REP)
                server_socket.bind(f'tcp://{self.ip}:{self.port}')
            except Exception as e:
                logger.error(f"Unexpected error in server: {e}")

            # Ver si tengo que cerrar la conexion    

    

    def upload_file(self, path, tracker_urls, private=False, comments="unknown", source="unknown"):
        torrent_maker = TorrentCreator(path, 1 << 18, private, tracker_urls,comments, source)
        #sha1_hash = torrent_maker.get_hash_pieces()
        sha1_hash = torrent_maker.get_hash_pieces()
        assert sha1_hash != ""
        torrent_maker.create_dottorrent_file('torrent_files')
        
        trackers = [tuple(url.split(':')) for url in tracker_urls]
        self.update_trackers(trackers, sha1_hash)

    def update_trackers(self, trackers, sha1, remove: bool = False):
        for tracker_ip, tracker_port in trackers:
            self.connect_to_tracker(tracker_ip, tracker_port, sha1, remove)    

    def connect_to_tracker(self, tracker_ip, tracker_port, sha1, remove):
        logger.debug(f"Connecting peer {self.ip}:{self.port} to tracker {tracker_ip}:{tracker_port}")
        request = {
                "action": "remove_from_database" if remove else "add_to_database",
                "pieces_sha1": sha1,
                "peer": (self.ip, self.port)
            }
        response = self._send_data(request,tracker_ip, tracker_port)
        logger.debug(f"Tracker response: {response}")
        

    def get_peers_from_tracker(self, torrent_info):
        logger.debug(f"METHOD: get_peers_from_Tracker")
        peers = []
        trackers = torrent_info.get_trackers()
        
        for tracker_ip, tracker_port in trackers:
            request = {"action": "get_peers", "pieces_sha1": torrent_info.metainfo['info']['pieces']}
            response = self._send_data(request,tracker_ip,tracker_port)

            if response:
                peers.extend(response.get('peers', []))
                logger.debug(f"Connected peer {self.ip}:{self.port} to tracker {tracker_ip}:{tracker_port}")
                logger.debug(f"Tracker response: {response}")
            else:
                logger.warning(f"No response from tracker {tracker_ip}:{tracker_port}")

        return peers

    
    def get_bit_field_of(self, info):
        try:
            # Validar que la información necesaria esté presente
            if not info or 'pieces' not in info or 'piece length' not in info:
                logger.error("Invalid torrent info provided for bitfield.")
                return {"error": "Invalid torrent info"}

            piece_manager = PieceManager(info, 'client_files')
            return {"bitfield": piece_manager.bitfield}
        except Exception as e:
            logger.error(f"Error generating bitfield: {e}")
            return {"error": "Error generating bitfield"}

        # piece_manager = PieceManager(info, 'Client/client_files')
        # return {"bitfield": piece_manager.bitfield}

    def download_file(self, dottorrent_file_path, save_at):
        logger.debug(f"METHOD: download_file")
        tr = TorrentReader(dottorrent_file_path)
        info = tr.build_torrent_info()
        peers = self.get_peers_from_tracker(info)
        piece_manager_inst = PieceManager(info.metainfo['info'], save_at)

        self.update_trackers(info.get_trackers(), info.dottorrent_pieces)
        #Aqui el socket se cierra?

        while not piece_manager_inst.completed:
            rarest_piece, owners = self.find_rarest_piece(peers, info, piece_manager_inst.bitfield)
            while owners:
                peer_for_download = random.choice(owners)
                owners.remove(peer_for_download)
                piece_manager_inst.clean_memory(rarest_piece)
                try:
                    self.download_piece_from_peer(peer_for_download, info, rarest_piece, piece_manager_inst)
                except Exception as e:
                    logger.error(f"Error downloading piece {rarest_piece} from {peer_for_download}: {e}")

                break

    def find_rarest_piece(self, peers, torrent_info: TorrentInfo, owned_pieces):
        logger.debug(f"Pers en finrerestpiece {peers}")
        count_of_pieces = [0] * torrent_info.number_of_pieces
        owners = [[] for _ in range(torrent_info.number_of_pieces)]

        
        for ip, port in peers:
            request = {
                    "action": "get_bit_field",
                    "info": dict(torrent_info.metainfo['info'])
                }
            request['info'].pop('md5sum')
            response = self._send_data(request,ip,port)
            
            if response:
                peer_bit_field = response.get('bitfield', [])
                for i in range(len(peer_bit_field)):
                    if peer_bit_field[i]:
                        count_of_pieces[i] += 1
                        owners[i].append((ip, port))

            else :
                logger.warning(f"No response from peer {ip}:{port} for bit field.")

        # encuentra la pieza mas rara        
        rarest_piece = -1
        for i, count in enumerate(count_of_pieces):
            if not owned_pieces[i] and count > 0:
                if rarest_piece == -1 or count < count_of_pieces[rarest_piece]:
                    rarest_piece = i

        return rarest_piece, owners[rarest_piece] if rarest_piece != -1 else []

        # rarest_piece = count_of_pieces.index(min(count_of_pieces))
        
        # while owned_pieces[rarest_piece]:
        #     count_of_pieces[rarest_piece] = math.inf
        #     rarest_piece = count_of_pieces.index(min(count_of_pieces))

        # return rarest_piece, owners[rarest_piece]

    
        
    def get_block_of_piece(self, info: dict, piece_index: int, block_offset: int):
        try:
            piece_manager = PieceManager(info, 'client_files')
            block = piece_manager.get_block_piece(piece_index, block_offset)

            # Asegurarse de que los datos estén codificados en Base64
            return {"data": base64.b64encode(block.data).decode('utf-8')}
        except Exception as e:
            logger.error(f"Error retrieving block {block_offset} of piece {piece_index}: {e}")
            return {"error": "Failed to retrieve block"}
            # piece_manager = PieceManager(info['info'], 'Client/client_files')
            # return {"data": piece_manager.get_block_piece(piece_index, block_offset).data}   


    def download_piece_from_peer(self, peer, torrent_info: TorrentInfo, piece_index: int,
                              piece_manager: PieceManager):
        
        try:
            piece_size = (
                torrent_info.file_size % torrent_info.piece_size
                if piece_index == piece_manager.number_of_pieces - 1
                else torrent_info.piece_size
            )
            
            num_blocks = int(math.ceil(float(piece_size) / DEFAULT_Block_SIZE))

            for i in range(num_blocks):
                request = {
                    "action": "get_block",
                    "info": dict(torrent_info.metainfo['info']),
                    "piece_index": piece_index,
                    "block_offset": i * DEFAULT_Block_SIZE
                }
                request['info'].pop('md5sum', None)

                response = self._send_data(request, peer[0], peer[1])

                if response and 'data' in response:
                    try:
                        # Decodificar el bloque recibido
                        raw_data = base64.b64decode(response['data'].encode('utf-8'))
                        piece_manager.receive_block_piece(piece_index, i * DEFAULT_Block_SIZE, raw_data)
                        logger.debug(f"Successfully downloaded block {i} of piece {piece_index} from {peer}")
                    except Exception as e:
                        logger.error(f"Error decoding/storing block {i} of piece {piece_index} from {peer}: {e}")
                else:
                    logger.warning(f"Failed to receive block {i} of piece {piece_index} from {peer}")

        except Exception as e:
            logger.error(f"Error downloading piece {piece_index} from {peer}: {e}")


    def find_random_piece(self, peers, torrent_info: TorrentInfo,
                          owned_pieces):
        available_pieces = []

        for ip, port in peers:
            proxy_socket = self.context.socket(zmq.REQ)
            
            try:
                proxy_socket.connect(f"tcp://{ip}:{port}")
                
                request = {
                    "action": "get_bit_field",
                    "info": dict(torrent_info.metainfo['info'])
                }
                
                request['info'].pop('md5sum', None)

                proxy_socket.send_json(request)
                
                response = proxy_socket.recv_json()
                
                peer_bit_field = response.get('bitfield', [])
                
                for i in range(len(peer_bit_field)):
                    if peer_bit_field[i] and not owned_pieces[i]:
                        available_pieces.append((ip, port, i))  

            except Exception as e:
                logger.error(f"Error while getting bit field from {ip}:{port} - {e}")

            finally:
                proxy_socket.close()

        if available_pieces:
            selected_piece = random.choice(available_pieces)
            return selected_piece[2], selected_piece[:2]  

        return None, None 
    
    

   
