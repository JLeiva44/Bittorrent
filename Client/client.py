from Client.torrent_utils import TorrentCreator, TorrentInfo, TorrentReader
from Client.pieces_manager import PieceManager
from Client.block import State, DEFAULT_Block_SIZE, Block
from Client.bclient_logger import logger

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
    def __init__(self, ip, port, peer_id = None) -> None:
        self.peer_id = peer_id
        self.ip = ip
        self.port = port
        self.peers = []
        self.context = zmq.Context()
        self.server_socket = self.context.socket(zmq.REP)
        self.tracker_sockets = {}
        threading.Thread(target=self.run_server, daemon=True).start() # Start Peer server thread



    def run_server(self):
        self.server_socket.bind(f"tcp://{self.ip}:{self.port}")
        logger.debug(f"Servidor de Peer escuvhando en tcp://{self.ip}:{self.port}")

        while True:
            try:
                message = self.server_socket.recv_json()
                action_type = message.get("action")
                
                if action_type == "get_bit_field":
                    response = self.get_bit_field_of(message['info'])
                    logger.debug(f"GetBitfieldResponse: {response}")
                    self.server_socket.send_json(response)
                    
                elif action_type == "get_block":
                    response = self.get_block_of_piece(message['info'], message['piece_index'], message['block_offset'])
                    logger.debug(f"GetBlockResponse: {response}")
                    self.server_socket.send_json(response)
                    
                else:
                    self.server_socket.send_json({"error": "Unknown action"})
            
            except zmq.ZMQError as e:
                logger.error(f"ZMQError occurred: {e}")
            except Exception as e:
                logger.error(f"An error occurred in the server: {e}")


    def upload_file(self, path, tracker_urls, private=False, comments="unknown", source="unknown"):
        torrent_maker = TorrentCreator(path, 1 << 18, private, tracker_urls,comments, source)
        #sha1_hash = torrent_maker.get_hash_pieces()
        sha1_hash = torrent_maker.get_hash_pieces()
        assert sha1_hash != ""
        torrent_maker.create_dottorrent_file('Client/torrent_files')
        
        trackers = [tuple(url.split(':')) for url in tracker_urls]
        self.update_trackers(trackers, sha1_hash)

    def update_trackers(self, trackers, sha1, remove: bool = False):
        for tracker_ip, tracker_port in trackers:
            self.connect_to_tracker(tracker_ip, tracker_port, sha1, remove)    

    def connect_to_tracker(self, tracker_ip, tracker_port, sha1, remove):
        tracker_socket = self.context.socket(zmq.REQ)
        tracker_socket.setsockopt(zmq.RCVTIMEO, 1000)  # Timeout de 1 segundo para recibir
        tracker_socket.setsockopt(zmq.SNDTIMEO, 1000)  # Timeout de 1 segundo para enviar

        try:
            tracker_socket.connect(f"tcp://{tracker_ip}:{tracker_port}")
            request = {
                "action": "remove_from_database" if remove else "add_to_database",
                "pieces_sha1": sha1,
                "peer": (self.ip, self.port)
            }
            tracker_socket.send_json(request)
            response = tracker_socket.recv_json()
            print(f"Tracker response: {response}")

        except zmq.ZMQError as e:
            logger.error(f"ZMQError connecting to tracker {tracker_ip}:{tracker_port} - {e}")
        
        finally:
            tracker_socket.close()

        # tracker_socket.connect(f"tcp://{tracker_ip}:{tracker_port}")
        
        # if remove:
        #     request = {"action": "remove_from_database", "pieces_sha1": sha1, "peer": (self.ip, self.port)}
        # else:
        #     request = {"action": "add_to_database", "pieces_sha1": sha1, "peer": (self.ip, self.port)}

        # tracker_socket.send_json(request)
        # response = tracker_socket.recv_json()
        # print(f"Tracker response: {response}")

    def get_peers_from_tracker(self, torrent_info):
        peers = []
        trackers = torrent_info.get_trackers()
        
        for tracker_ip, tracker_port in trackers:
            tracker_socket = self.context.socket(zmq.REQ)
            tracker_socket.setsockopt(zmq.RCVTIMEO, 1000)  # Timeout de 1 segundo para recibir
            tracker_socket.setsockopt(zmq.SNDTIMEO, 1000)  # Timeout de 1 segundo para enviar

            try:
                tracker_socket.connect(f"tcp://{tracker_ip}:{tracker_port}")
                request = {"action": "get_peers", "pieces_sha1": torrent_info.metainfo['info']['pieces']}
                tracker_socket.send_json(request)
                response = tracker_socket.recv_json()
                peers.extend(response.get('peers', []))

            except zmq.ZMQError as e:
                logger.error(f"ZMQError connecting to {tracker_ip}:{tracker_port} - {e}")

            finally:
                tracker_socket.close()

        return peers

        #     tracker_socket.connect(f"tcp://{tracker_ip}:{tracker_port}")
        #     request = {"action": "get_peers", "pieces_sha1": torrent_info.metainfo['info']['pieces']}
        #     tracker_socket.send_json(request)
        #     response = tracker_socket.recv_json()
        #     peers.extend(response.get('peers', []))
        
        # return peers
    
    def get_bit_field_of(self, info):
        piece_manager = PieceManager(info, 'Client/client_files')
        return {"bitfield": piece_manager.bitfield}
    # def register(self):
    #     message = {
    #         "action": "register",
    #         "peer_id": self.peer_id,
    #         "file_hash": self.file_hash
    #     }
    #     print("Registrando peer...")
    #     self.socket.send_json(message)
    #     response = self.sock_fileset.recv_json()
    #     print("Respuesta del tracker: {}".format(response))

    def download_file(self, dottorrent_file_path, save_at):
        tr = TorrentReader(dottorrent_file_path)
        info = tr.build_torrent_info()
        peers = self.get_peers_from_tracker(info)
        piece_manager_inst = PieceManager(info.metainfo['info'], save_at)

        self.update_trackers(info.get_trackers(), info.dottorrent_pieces)

        while not piece_manager_inst.completed:
            rarest_piece, owners = self.find_rarest_piece(peers, info, piece_manager_inst.bitfield)
            while owners:
                peer_for_download = random.choice(owners)
                owners.remove(peer_for_download)
                piece_manager_inst.clean_memory(rarest_piece)
                self.download_piece_from_peer(peer_for_download, info, rarest_piece, piece_manager_inst)
                break

    def find_rarest_piece(self, peers, torrent_info: TorrentInfo, owned_pieces):
        count_of_pieces = [0] * torrent_info.number_of_pieces
        owners = [[] for _ in range(torrent_info.number_of_pieces)]
        
        for ip, port in peers:
            proxy_socket = self.context.socket(zmq.REQ)
            proxy_socket.setsockopt(zmq.RCVTIMEO, 1000)  # Timeout de 1 segundo para recibir
            proxy_socket.setsockopt(zmq.SNDTIMEO, 1000)  # Timeout de 1 segundo para enviar
            
            max_retries = 3

            try:
                proxy_socket.connect(f"tcp://{ip}:{port}")
                
                for attempt in range(max_retries):
                    if self.is_socket_connected(proxy_socket):
                        logger.warning(f"Server at {ip}:{port} is not alive")
                        break
                    else : 
                        logger.warning(f"Server at {ip}:{port} is not alive")
                    time.sleep(0.1)  # Esperar antes del siguiente intento
                
                else:
                    logger.error(f"Failed to connect to {ip}:{port} after {max_retries} attempts.")
                    continue
                
                request = {
                    "action": "get_bit_field",
                    "info": dict(torrent_info.metainfo['info'])
                }
                request['info'].pop('md5sum')
                
                proxy_socket.send_json(request)
                response = proxy_socket.recv_json()
                
                peer_bit_field = response.get('bitfield', [])
                
                for i in range(len(peer_bit_field)):
                    if peer_bit_field[i]:
                        count_of_pieces[i] += 1
                        owners[i].append((ip, port))

            except zmq.ZMQError as e:
                logger.error(f"ZMQError connecting to {ip}:{port} - {e}")
            except Exception as e:
                logger.error(f"An error occurred while getting bit field from {ip}:{port} - {e}")
            
            finally:
                proxy_socket.close()

        rarest_piece = count_of_pieces.index(min(count_of_pieces))
        
        while owned_pieces[rarest_piece]:
            count_of_pieces[rarest_piece] = math.inf
            rarest_piece = count_of_pieces.index(min(count_of_pieces))

        return rarest_piece, owners[rarest_piece]
        #     try:
        #         # Conectar al socket solo una vez por peer
        #         proxy_socket = self.context.socket(zmq.REQ)
        #         #proxy_socket = self.socket
        #         proxy_socket.connect(f"tcp://{ip}:{port}")
        #         time.sleep(0.1)  # Esperar 100 ms antes de enviar el ping

        #         conected = self.is_socket_connected(proxy_socket)

        #         max_retries = 3
        #         for attempt in range(max_retries):
        #             if self.is_socket_connected(proxy_socket):
        #                 break
        #             time.sleep(0.1)  # Esperar antes del siguiente intento
        #         else:
        #             logger.error(f"Failed to connect to {ip}:{port} after {max_retries} attempts.")

                
        #         request = {
        #             "action": "get_bit_field",
        #             "info": dict(torrent_info.metainfo['info'])
        #         }
        #         request['info'].pop('md5sum')
                
        #         # Enviar la solicitud
        #         proxy_socket.send_json(request)
        #         response = proxy_socket.recv_json()
        #         peer_bit_field = response.get('bitfield', [])
                
        #         for i in range(len(peer_bit_field)):
        #             if peer_bit_field[i]:
        #                 count_of_pieces[i] += 1
        #                 owners[i].append((ip, port))
            
        #     except zmq.ZMQError as e:
        #         logger.error(f"ZMQError connecting to {ip}:{port} - {e}")
        #     except Exception as e:
        #         logger.error(f"An error occurred while getting bit field from {ip}:{port} - {e}")

        #     finally:
        #         proxy_socket.close()    
            
        # rarest_piece = count_of_pieces.index(min(count_of_pieces))
        
        # while owned_pieces[rarest_piece]:
        #     count_of_pieces[rarest_piece] = math.inf
        #     rarest_piece = count_of_pieces.index(min(count_of_pieces))
        
        # return rarest_piece, owners[rarest_piece]


    
        
    def get_block_of_piece(self, info: dict, piece_index: int, block_offset: int):
        piece_manager = PieceManager(info['info'], 'Client/client_files')
        return {"data": piece_manager.get_block_piece(piece_index, block_offset).data}   


    def download_piece_from_peer(self, peer, torrent_info: TorrentInfo, piece_index: int,
                              piece_manager: PieceManager):
        try:
            proxy_socket = self.context.socket(zmq.REQ)
            proxy_socket.setsockopt(zmq.RCVTIMEO, 1000)  # Timeout de 1 segundo para recibir
            proxy_socket.setsockopt(zmq.SNDTIMEO, 1000)  # Timeout de 1 segundo para enviar
            
            proxy_socket.connect(f"tcp://{peer[0]}:{str(peer[1])}")

            #conected = self.is_socket_connected(proxy_socket)

            piece_size = torrent_info.file_size % torrent_info.piece_size if piece_index == piece_manager.number_of_pieces - 1 else torrent_info.piece_size
         
            for i in range(int(math.ceil(float(piece_size) / DEFAULT_Block_SIZE))):
                request = {
                    "action": "get_block",
                    "info": dict(torrent_info.metainfo['info']),
                    "piece_index": piece_index,
                    "block_offset": i * DEFAULT_Block_SIZE
                }
                request['info'].pop('md5sum')

                proxy_socket.send_json(request)
                
                #El problema es aqui
                received_block = proxy_socket.recv_json()

                # Asegurar de que 'data' sea una cadena antes de decodificar
                raw_data = base64.b64decode(received_block['data']['data'].encode('utf-8'))  # Decodifica a bytes
                piece_manager.receive_block_piece(piece_index, i * DEFAULT_Block_SIZE, raw_data)
        except Exception as e:
            logger.error(f"Error downloading piece {piece_index} from {peer}: {e}")

        finally:
            proxy_socket.close()    
    

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
    
    def is_server_alive(self,socket):
      try:
          socket.send_json({"action": "ping"})
          response=socket.recv_json(flags=zmq.NOBLOCK)  
          return True
      except zmq.Again:
          logger.warning(f"Socket not ready for {socket} - retrying...")
          return False
      except zmq.ZMQError as e:
          logger.error(f"ZMQError occurred: {e}")
          return False
    
    def is_socket_connected(self, socket):
        try:
            socket.send_json({"action": "ping"})
            response = socket.recv_json(flags=zmq.NOBLOCK)  # Non-blocking receive
            return True
        except zmq.Again:
            logger.warning(f"Socket not ready for {socket} - retrying...")
            return False
        except zmq.ZMQError as e:
            logger.error(f"ZMQError occurred: {e}")
            return False
