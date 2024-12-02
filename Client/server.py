import zmq
import threading
from bclient_logger import logger

class Server:
    def __init__(self, ip, port, peer_id):
        self.ip = ip
        self.port = port
        self.peer_id = peer_id
        self.context = zmq.Context()

    def start(self):
        threading.Thread(target=self.run_server, daemon=True).start()

    def run_server(self):
        server_socket = self.context.socket(zmq.REP)
        server_socket.bind(f"tcp://{self.ip}:{self.port}")
        logger.debug(f"Server running at {self.ip}:{self.port}")

        while True:
            try:
                message = server_socket.recv_json()
                action = message.get("action")
                logger.debug(f"Received message: {message}")

                if action == "handshake":
                    server_socket.send_json({"status": "handshake_success"})
                elif action == "choke":
                    logger.info(f"Received choke request from {message['peer_id']}")
                    server_socket.send_json({"status": "choked"})
                elif action == "unchoke":
                    logger.info(f"Received unchoke request from {message['peer_id']}")
                    server_socket.send_json({"status": "unchoked"})
                elif action == "interested":
                    logger.info(f"Peer {message['peer_id']} is interested")
                    server_socket.send_json({"status": "interested_received"})
                elif action == "peer_exchange":
                    logger.info(f"Peer exchange with {message['peer_id']}")
                    server_socket.send_json({"status": "peer_exchange_success"})
                else:
                    server_socket.send_json({"error": "Unknown action"})
            except Exception as e:
                logger.error(f"Server error: {e}")
