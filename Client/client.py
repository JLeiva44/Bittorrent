from torrent import TorrentMaker, Torrent
from pieces_manager import PiecesManager
from subpiece import SUBPIECE_SIZE, SubPiece
import zmq
import random
import threading
import math
import base64
HOST = '127.0.0.1'
LOCAL = 'localhost'
PORT1 = '8001'

PIECE_SIZE =  2**18 # 256 Kb (kilobibits) = 262144 bits

class Client:
    def __init__(self, client_id, ip, port) -> None:
        self.id = client_id
        self.ip = ip
        self.port = port
        threading.Thread(target=self.start_server, daemon=True).start()

    def start_server(self):
        context = zmq.Context()
        p1 = "tcp://"+ self.ip +":"+ self.port # how and where to connect
        socket = context.socket(zmq.REP) # reply socket
        socket.bind(p1)    
        message = socket.recv_pyobj()
        while not message[0] == 'STOP':
            if message[0] == 'REQUEST SUBPIECE': # (info, piece_index, subpiece_offset)
                torrent = message[1]
                piece_index = message[2]
                subpiece_offset = message[3]
                pieces_mgr = PiecesManager(torrent, 'Downloaded_Files')

                reply = pieces_mgr.get_subP_of_piece(piece_index, subpiece_offset)
                socket.send_pyobj(['REPLY SUBPIECE OK', reply])

            elif message[0] == 'GET BITFIELD': # getBF(info)
                torrent = message[1]
                pieces_mgr = PiecesManager(torrent, 'Downloaded_Files')
                reply = pieces_mgr.bitfield
                socket.send_pyobj(['REPLY BITFIELD OK',reply])

            message = socket.recv_pyobj() 

    def _send_message(self,message, ip, port):
        context = zmq.Context()
        url = "tcp://" + ip + ":" + port    
        socket = context.socket(zmq.REQ)
        socket.connect(url)
        socket.send_pyobj(message)

        answer = socket.recv_pyobj()
        return answer

    def seed_file(self, file_path, tracker_url): # Ver despues si poner mas parametros como PRIVATE, COMMents, SOURCE ...
        torrent_maker = TorrentMaker(file_path,PIECE_SIZE, [tracker_url], 'pepe')
        pieces = torrent_maker.pieces
        torrent_maker.create_file()


        # 1 solo tracker 
        tracker_ip, tracker_port = tracker_url.split(':')
        print(pieces)
        print(tracker_ip, tracker_port)

        # llamar a la bd del tracker para que se actualice
        # context = zmq.Context()
        # p1 = "tcp://" + tracker_ip + ':' + str(tracker_port)
        # socket = context.socket(zmq.REQ)
        # socket.connect(p1)
        # socket.send_pyobj(['WRITE', pieces, self.ip, self.port])

        message = ['WRITE', pieces, self.ip, self.port]

        answer = self._send_message(message, tracker_ip, tracker_port)
        print(answer)
        #socket.send_pyobj(['STOP'])


    def find_random_piece(self, peers, torrent : Torrent, owned_pieces):
        owners = [[] for i in range(torrent.number_of_pieces)]

        for ip, port in peers :
            response_to_bf_request = self._send_message(['GET BITFIELD', torrent])
            answer_status = response_to_bf_request[0]

            peer_bitfield = response_to_bf_request[1]
            for i in range(len(peer_bitfield)):
                if peer_bitfield[i]:
                    owners[i].append((ip, port))

            p_index = random.randint(0, len(owners)-1)
            while owned_pieces[p_index] or len(owners[i] == 0):
                p_index = random.randint(0, len(owners)-1) 

            return p_index, owners                           


        print("Este es el bitfield")
        print(peer_bitfield)

    



         

    def download_file(self,dottorrent_file_path, path_to_download = 'Downloaded_Files'):
        torrent = Torrent(dottorrent_file_path) 
        peers = self.get_peers(torrent)

        pieces_manager = PiecesManager(torrent,path_to_download)

        while not pieces_manager.download_completed:
            random_piece, owners = self.find_random_piece(peers, torrent, pieces_manager.bitfields)

            while owners:
                peer_for_download = owners[random.randint(0, len(owners)-1)]
                owners.remove(peer_for_download)

                pieces_manager.clean_memory(random_piece)
                self.download_piece_from_peer(peer_for_download, torrent, rarest_piece, pieces_manager)
                break
            if not len(owners):
                break

    def download_piece_from_peer(self,peer, torrent : Torrent, piece_index, piece_manager : PiecesManager):
        peer_ip = peer[0]
        peer_port = peer[1]

        piece_size = torrent.file_length % torrent.piece_length if piece_index == piece_manager.number_of_pieces -1 else torrent.piece_length
        for i in range(int(math.ceil(float(piece_size) / SUBPIECE_SIZE))):
            received_subpiece_response = self._send_message(['REQUEST SUBPIECE',torrent,piece_index, i * SUBPIECE_SIZE ]) 
            answer_status = received_subpiece_response[0]
            print(answer_status)
            received_subpiece = received_subpiece_response[1]

            raw_data = base64.b64decode(received_subpiece.data)
            piece_manager.receive_subP_of_piece(piece_index, i * SUBPIECE_SIZE, raw_data)





    def get_peers(self, torrent : Torrent):
        tracker_url = torrent.announce
        print("Esta es la url del tracker")
        print(tracker_url)
        splited = tracker_url.split(':')
        tracker_ip = splited[0]
        tracker_port = int(splited[1])

        pieces = torrent.meta_info[b'info'][b'pieces']

        # context = zmq.Context()
        # p1 = "tcp://" + tracker_ip + ':' + str(tracker_port)
        # socket = context.socket(zmq.REQ)
        # socket.connect(p1)
        # socket.send_pyobj(['REQUEST PEERS', pieces])

        m1 = ['REQUEST PEERS', pieces]
        answer1 = self._send_message(m1, tracker_ip, tracker_port)

        #message = socket.recv_pyobj()

        #answer2 = socket.send_pyobj(['STOP'])

        answer2 = self._send_message(['STOP'],tracker_ip,tracker_port)

        status = answer2[0]
        print(status)
        peers = answer1[1]

        return peers

    

        

c = Client(1,'127.222.333.11','1880')
c.seed_file('/media/jose/A63C16883C1654211/Proyectos/Bittorrent/Bittorrent/Files/f.txt','127.0.0.1:8080')
#c.download_file('/media/jose/A63C16883C1654211/Proyectos/Bittorrent/Bittorrent/Files/f.torrent')

