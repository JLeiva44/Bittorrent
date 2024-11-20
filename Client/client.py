from utils.torrent import TorrentMaker, Torrent
from utils.pieces_manager import PiecesManager
from utils.subpiece import State, DEFAULT_SUBPIECE_SIZE, SubPiece
from utils.bclient_logger import logger
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
    def __init__(self, client_id, ip, port) -> None:
        self.id = client_id
        self.ip = ip
        self.port = port
        self.peers = []

    
    @Pyro4.expose
    def get_bitfield_of(self, torrent):
        piece_manager = PiecesManager(torrent, 'files')
        return piece_manager.bitfield
    
    @Pyro4.expose
    def get_subpiece_of_piece(self, torrent, piece_index, subpiece_offset):
        piece_manager = PiecesManager(torrent, 'files')
        return piece_manager.get_subP_of_piece(piece_index, subpiece_offset)
    

    def connect_to(self, ip, port, type_of_peer):
        ns = Pyro4.locateNS()
        #by default all peers, including tracker are registered in the name server as type_of_peerIP:Port
        uri = ns.lookup(f"{type_of_peer}{ip}:{port}")
        proxy = Pyro4.Proxy(uri=uri)
        return proxy


    def update_trackers(self, trackers, sha1, remove: bool = False):
        if remove :
            for tracker_ip, tracker_port in trackers:
                tracker_proxy = self.connect_to(tracker_ip, tracker_port,'tracker')
                tracker_proxy.remove_from_database(sha1, self.ip, self.port)

        else:
            print("Updating Trackers")
            for tracker_ip, tracker_port in trackers:
                tracker_proxy = self.connect_to(tracker_ip,tracker_port, 'tracker')
                tracker_proxy.add_to_trackers(sha1, self.ip, self.port)


    def upload_file(self, path, tracker_urls, source = "unknow"):
        '''
        Upload a local File
        '''
        torrent_maker = TorrentMaker(path,1<<18,tracker_urls,source) 
        pieces = torrent_maker.pieces
        torrent_maker.create_file()  

        trackers = []

        for url in tracker_urls:
            ip,port = url.split(':')
            trackers.append((ip,int(port)))
        print(type(trackers))
        print(trackers)
        print("LLamando a update trackers")
        self.update_trackers(trackers, pieces) 

    def get_peers_from_tracker(self, torrent):
        info = torrent # Torrent is a Python class that represents a torrent file
        peers = []
        trackers = info.announce

        for tracker_ip, tracker_port in trackers:
            tracker_proxy = self.connect_to(tracker_ip, tracker_port, 'tracker')
            for peer in tracker_proxy.get_peers(info.pieces):
                peers.append(peer)
        return peers    

    def find_rarest_piece(self, peers, torrent, owned_pieces):
        count_of_pieces = [0 for i in range(torrent.number_of_pieces)]      
        owners = [[] for i in range(torrent.number_of_pieces)]
        print(peers)

        for ip, port in peers:
            proxy = self.connect_to(ip,port, 'client')
            peer_bit_field = proxy.get_bitfield_of(torrent.meta_info[b'info']) 

            for i in range(len(peer_bit_field)):
                if peer_bit_field[i]:
                    count_of_pieces[i] = count_of_pieces[i] + 1
                    owners[i].append((ip,port))
            rarest_piece = count_of_pieces.index(min(count_of_pieces))
            while(owned_pieces[rarest_piece]):
                count_of_pieces[rarest_piece] = math.inf
                rarest_piece = count_of_pieces.index(min(count_of_pieces, lambda x:x))

        return rarest_piece, owners[rarest_piece]       
    

    def download_file(self, torrent_file_path, save_at = "files"):
        """
        Start download of a file from a local dottorrent file
        """

        torrent = Torrent(torrent_file_path)
        info = torrent.info
        peers = self.get_peers_from_tracker(torrent)
        piece_manager_inst = PiecesManager(info, save_at)

        self.update_trackers(torrent.announce, torrent.pieces)


        while not piece_manager_inst.download_completed:
            rarest_piece, owners = self.find_rarest_piece(peers, torrent, piece_manager_inst.bitfield)
            while len(owners)>0:
                print("tengo un owner")
                peer_for_download = owners[random.randint(0,len(owners)-1)]
                owners.remove(peer_for_download)

                piece_manager_inst.clean_memory(rarest_piece)

                print("Voy a tratar de descargar la pieza")
                self.download_piece_from_peer(peer_for_download, torrent, rarest_piece, piece_manager_inst)
                break
            if not len(owners):
                break


    def download_piece_from_peer(self, peer, torrent, piece_index, piece_manager):
        try:
            proxy_peer = self.connect_to(peer[0],peer[1], 'client')
        except:
            logger.error("Connection failure")
            return

        piece_size = torrent.file_length % torrent.piece_length if piece_index == piece_manager.number_of_pieces -1 else torrent.piece_length
        for i in range(int(math.ceil(float(piece_size) / DEFAULT_SUBPIECE_SIZE))):
            received_subpiece = proxy_peer.get_subpiece_of_piece(torrent.info, piece_index, i*DEFAULT_SUBPIECE_SIZE)
            print('este es el bloque que me mandaron')
            print(received_subpiece)
            raw_data = base64.b64decode(received_subpiece['data']['data'])
            piece_manager.receive_subP_of_piece(piece_index, i*DEFAULT_SUBPIECE_SIZE, raw_data)
          




