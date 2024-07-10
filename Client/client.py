from torrent import TorrentMaker
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

    # def seed_file(self, file_path, tracker_url): # Ver despues si poner mas parametros como PRIVATE, COMMents, SOURCE ...
    #     torrent_maker = TorrentMaker(file_path,PIECE_SIZE, tracker_url, 'pepe')
    #     pieces = torrent_maker.pieces

    #     tracker_ip, tracker_port = tracker_url.split(':')
    #     print(pieces)
    #     print(tracker_ip, tracker_port)
         

    def download_file(self,file):
        pass

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
c.connect()
