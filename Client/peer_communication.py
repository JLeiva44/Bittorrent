import zmq
from bclient_logger import logger

class PeerCommunication:
    def __init__(self, ip, port, peer_id):
        self.ip = ip
        self.port = port
        self.peer_id = peer_id
        self.context = zmq.Context()

    def send_request(self, request, ip, port, timeout=5000):
        """Envía una solicitud a un peer o tracker."""
        try:
            with self.context.socket(zmq.REQ) as socket:
                socket.connect(f"tcp://{ip}:{port}")
                socket.send_json(request)
                
                poller = zmq.Poller()
                poller.register(socket, zmq.POLLIN)
                
                if poller.poll(timeout):
                    return socket.recv_json()
                else:
                    logger.warning(f"Timeout waiting for response from {ip}:{port}")
                    return None
        except Exception as e:
            logger.error(f"Error communicating with {ip}:{port} - {e}")
            return None

    def connect_to_tracker(self, tracker_ip, tracker_port, torrent_hash, remove=False):
        """Conecta al tracker para registrar o eliminar este peer."""
        action = "remove_from_database" if remove else "add_to_database"
        request = {"action": action, "pieces_sha1": torrent_hash, "peer": (self.ip, self.port)}
        response = self.send_request(request, tracker_ip, tracker_port)
        logger.debug(f"Tracker response: {response}")
