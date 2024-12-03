import socket
import json

PORT = 8002

class BroadcastManager:
    def __init__(self, ip, port):
        self.broadcast_ip = '172.17.255.255'  # Dirección de broadcast
        self.port = port

        # Configuración de sockets
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.sock.bind(("", port))

    def send_broadcast(self, message):
        self.sock.sendto(json.dumps(message).encode(), (self.broadcast_ip, self.port))

    def receive_broadcast(self):
        try:
            data, _ = self.sock.recvfrom(1024)
            return json.loads(data.decode())
        except socket.timeout:
            return None

    def send_response(self, message, ip):
        self.sock.sendto(json.dumps(message).encode(), (ip, self.port))

    def receive_response(self, expected_action = "discovery_response"):
        #self.receive_broadcast()
        try:
            data, sender = self.sock.recvfrom(1024)
            message = json.loads(data.decode())

            # # Validar que el mensaje tenga la acción esperada
            # if message.get("action") == expected_action:
            #     return message, sender
            # else:
            #     return message.get("action"), sender
            return message, sender
        except socket.timeout:
            return None, None