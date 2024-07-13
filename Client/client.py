from torrent import TorrentMaker, Torrent
import zmq
HOST = '127.0.0.1'
LOCAL = 'localhost'
PORT1 = '8001'

PIECE_SIZE =  2**18 # 256 Kb (kilobibits) = 262144 bits

class Client:
    def __init__(self, client_id, ip, port) -> None:
        self.id = client_id
        self.ip = ip
        self.port = port

    def seed_file(self, file_path, tracker_url): # Ver despues si poner mas parametros como PRIVATE, COMMents, SOURCE ...
        torrent_maker = TorrentMaker(file_path,PIECE_SIZE, [tracker_url], 'pepe')
        pieces = torrent_maker.pieces
        torrent_maker.create_file()


        # 1 solo tracker 
        tracker_ip, tracker_port = tracker_url.split(':')
        print(pieces)
        print(tracker_ip, tracker_port)

        # llamar a la bd del tracker para que se actualice
        context = zmq.Context()
        p1 = "tcp://" + tracker_ip + ':' + str(tracker_port)
        socket = context.socket(zmq.REQ)
        socket.connect(p1)
        socket.send_pyobj(['WRITE', pieces, self.ip, self.port])

        message = socket.recv_pyobj()
        print(message[0])
        #socket.send_pyobj(['STOP'])

         

    def download_file(self,dottorrent_file_path):
        torrent = Torrent(dottorrent_file_path)
        print(torrent.meta_info)
        print(self.get_peers(torrent))

    def get_peers(self, torrent : Torrent):
        tracker_url = torrent.announce
        print("Esta es la url del tracker")
        print(tracker_url)
        splited = tracker_url.split(':')
        tracker_ip = splited[0]
        tracker_port = int(splited[1])

        pieces = torrent.meta_info[b'info'][b'pieces']

        context = zmq.Context()
        p1 = "tcp://" + tracker_ip + ':' + str(tracker_port)
        socket = context.socket(zmq.REQ)
        socket.connect(p1)
        socket.send_pyobj(['REQUEST PEERS', pieces])

        message = socket.recv_pyobj()
        socket.send_pyobj(['STOP'])

        status = message[0]
        print(status)
        peers = message[1]

        return peers

    # def connect(self):
    #     print("Conectando")
    #     context = zmq.Context()
    #     p1 = "tcp://"+ HOST +":"+ PORT1 # how and where to connect
    #     print("Connecting to " + p1)
    #     s = context.socket(zmq.REQ) # create request socket
    #     s.connect(p1) # block until connected
    #     s.send_pyobj(["CREATE",1])
    #     #s.send_string("Hello world 1") # send message
    #     print("Mensaje enviado")
    #     message = s.recv_pyobj() # block until response
    #     #s.send_string("STOP") # tell server to stop
    #     print(message) # print result

    

        

c = Client(1,'127.222.333.11','1880')
c.seed_file('/media/jose/A63C16883C1654211/Proyectos/Bittorrent/Bittorrent/Files/f.txt','127.0.0.1:8080')
#c.download_file('/media/jose/A63C16883C1654211/Proyectos/Bittorrent/Bittorrent/Files/f.torrent')

