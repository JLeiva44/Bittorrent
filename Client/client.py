class Client:
    def __init__(self, client_id, ip, port) -> None:
        self.id = client_id
        self.ip = ip
        self.port = port

    def upload_file(self, file):
        pass

    def download_file(self,file):
        pass
    
    def create_torrent(self, **kwargs):
        pass

        

