from server import Server
from peer_communication import PeerCommunication
from torrent_manager import TorrentManager
from bclient_logger import logger

class Client:
    def __init__(self, ip, port, peer_id):
        self.id = peer_id
        self.ip = ip
        self.port = port
        self.server = Server(ip, port, self.id)
        self.peer_comm = PeerCommunication(ip, port, peer_id)
        self.torrent_manager = TorrentManager()

        logger.debug(f"Starting Client at {ip}:{port}")
        self.server.start()  # Inicia el servidor en un hilo separado

    def upload_file(self, path, tracker_urls, private=False, comments="unknown", source="unknown"):
        """Crea y sube un archivo torrent al tracker."""
        self.torrent_manager.upload_torrent(path, tracker_urls, private, comments, source)

    def download_file(self, dottorrent_file_path, save_at):
        """Descarga un archivo usando un torrent."""
        self.torrent_manager.download_torrent(dottorrent_file_path, save_at, self.peer_comm)

    def connect_to_tracker(self, tracker_ip, tracker_port, torrent_hash, remove=False):
        """Conecta este peer al tracker para registrar o eliminarse."""
        self.peer_comm.connect_to_tracker(tracker_ip, tracker_port, torrent_hash, remove)
