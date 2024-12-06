import threading
import zmq
from peer_communication import PeerCommunication
from tracker_handler import TrackerHandler
from torrent_manager import TorrentManager
class Client:
    def __init__(self, ip, port, peer_id):
        self.id = peer_id
        self.ip = ip
        self.port = port
        self.context = zmq.Context()

        # Inicializa componentes
        self.peer_communication = PeerCommunication(ip, port, self.context)
        self.tracker_handler = TrackerHandler(self.context, ip, port)
        self.torrent_manager = TorrentManager(self.peer_communication, self.tracker_handler)

        # Inicia el servidor para escuchar conexiones
        threading.Thread(target=self.peer_communication.run_server, daemon=True).start()

    def upload_file(self, path, tracker_urls, private=False, comments="unknown", source="unknown"):
        """Sube un archivo y actualiza los trackers correspondientes."""
        self.torrent_manager.upload_file(path, tracker_urls, private, comments, source)

    def download_file(self, dottorrent_file_path, save_at):
        """Descarga un archivo de un torrent."""
        self.torrent_manager.download_file(dottorrent_file_path, save_at)
