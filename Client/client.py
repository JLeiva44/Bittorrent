from torrent.torrent import TorrentMaker


PIECE_SIZE =  2**18 # 256 Kb (kilobibits) = 262144 bits

class Client:
    def __init__(self, client_id, ip, port) -> None:
        self.id = client_id
        self.ip = ip
        self.port = port

    def seed_file(self, file_path, tracker_url): # Ver despues si poner mas parametros como PRIVATE, COMMents, SOURCE ...
        torrent_maker = TorrentMaker(file_path,PIECE_SIZE, tracker_url, 'pepe')
        pieces = torrent_maker.pieces

        tracker_ip, tracker_port = tracker_url.split(':')
        print(pieces)
        print(tracker_ip, tracker_port)
         

    def download_file(self,file):
        pass
    

        

c = Client(1,'127.222.333.11','1880')
c.seed_file('Files/music1.txt','127.222.11.11:1080')
