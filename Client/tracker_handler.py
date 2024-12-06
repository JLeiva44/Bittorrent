
from peer_communication import PeerCommunication

class TrackerHandler:
    def __init__(self, context, client_ip, client_port):
        self.context = context
        self.client_ip = client_ip
        self.client_port = client_port

    def update_tracker(self, tracker_ip, tracker_port, sha1, action="add_to_database"):
        """Actualiza un tracker para añadir o eliminar un peer."""
        request = {
            "action": action,
            "pieces_sha1": sha1,
            "peer": (self.client_ip, self.client_port)
        }
        # Reutiliza PeerCommunication para enviar datos
        response = PeerCommunication._send_data(self, request, tracker_ip, tracker_port)
        return response

    def get_peers_from_tracker(self, tracker_ip, tracker_port, sha1):
        """Obtiene la lista de peers desde un tracker."""
        request = {"action": "get_peers", "pieces_sha1": sha1}
        return PeerCommunication._send_data(self, request, tracker_ip, tracker_port)
