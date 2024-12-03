import hashlib
import logging
import time
import random
import socket
import os
from http.server import BaseHTTPRequestHandler, HTTPServer
import json
from urllib.parse import urlparse, parse_qs
from chord import ChordNode, ChordNodeReference
import threading
import requests
HOST = '127.0.0.1'
PORT1 = 8080
PORT2 = 8001
CONTAINER_NAME = os.getenv("HOSTNAME")
MAX_RETRIES = 3
BROADCAST_IP = '172.17.255.255'

logger = logging.getLogger(__name__)

def sha256_hash(s):
    return int(hashlib.sha256(s.encode()).hexdigest(), 16)

def getShaRepr(data: str):
    return int(hashlib.sha1(data.encode()).hexdigest(), 16)

def bcast_call(port, msg):
    # Se mantiene igual
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
        s.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        s.sendto(msg.encode(), ("172.17.255.255", port))

class TrackerHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        parsed_path = urlparse(self.path)
        query_params = parse_qs(parsed_path.query)

        action = query_params.get("action", [None])[0]
        if action:
            try:
                response = self.handle_request(action, query_params)
                self.send_response(200)
                self.send_header("Content-type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps(response).encode())
            except Exception as e:
                logger.error(f"Error al manejar la solicitud GET: {e}")
                self.send_response(500)
                self.send_header("Content-type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps({"error": f"Error interno: {e}"}).encode())
        else:
            self.send_response(400)
            self.send_header("Content-type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"error": "Acción no proporcionada"}).encode())

    def do_POST(self):
        content_length = int(self.headers["Content-Length"])
        post_data = self.rfile.read(content_length)
        message = json.loads(post_data.decode("utf-8"))

        action = message.get("action")
        if action:
            try:
                response = self.handle_request(action, message)
                self.send_response(200)
                self.send_header("Content-type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps(response).encode())
            except Exception as e:
                logger.error(f"Error al manejar la solicitud POST: {e}")
                self.send_response(500)
                self.send_header("Content-type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps({"error": f"Error interno: {e}"}).encode())
        else:
            self.send_response(400)
            self.send_header("Content-type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"error": "Acción no proporcionada"}).encode())

    def handle_request(self, action, params):
        if action == "get_peers":
            return self.get_peers(params.get("pieces_sha1", [""])[0])
        elif action == "add_to_database":
            return self.add_to_database(
                params.get("pieces_sha1", [""])[0],
                params.get("peer", [None, None])[0],
                params.get("peer", [None, None])[1]
            )
        elif action == "remove_from_database":
            return self.remove_from_database(
                params.get("pieces_sha1", [""])[0],
                params.get("ip", [""])[0],
                params.get("port", [""])[0]
            )
        elif action == "get_database":
            return self.get_database()
        elif action == "get_node_id":
            return {"node_id": self.node_id}
        else:
            return {"error": "Acción desconocida."}

    def get_peers(self, pieces_sha1):
        if not pieces_sha1:
            return {"error": "Se requiere el hash de la pieza."}
        
        peers = self.chord_node.retrieve_key(pieces_sha1)
        final_peers = []
        for peer in peers:
            peer = peer.split(":")
            final_peers.append((peer[0], peer[1]))

        return {"peers": final_peers}

    def add_to_database(self, pieces_sha1, peer_ip, peer_port):
        if not pieces_sha1 or not peer_ip or not peer_port:
            return {"error": "Datos incompletos para agregar al tracker."}
        
        peer = f'{peer_ip}:{peer_port}'
        self.chord_node.store_key(pieces_sha1, peer)
        return {"response": f"Peer {peer} añadido al tracker para {pieces_sha1}"}

    def remove_from_database(self, pieces_sha1, ip, port):
        if not pieces_sha1 or not ip or not port:
            return {"error": "Datos incompletos para eliminar del tracker."}
        
        with self.lock:
            if pieces_sha1 in self.database:
                self.database[pieces_sha1] = [
                    peer for peer in self.database[pieces_sha1] if peer != (ip, port)
                ]
                if not self.database[pieces_sha1]:
                    del self.database[pieces_sha1]

        return {"response": f"Eliminado {ip}:{port} para {pieces_sha1}"}

    def get_database(self):
        with self.lock:
            return {"database": self.database}

class Tracker:
    def __init__(self, ip, port, chord_m=8, broadcast_port=5555):
        logger.info("------------------- LOGER DEL TRACKER HTTP-----------------")
        self.ip = str(ip)
        self.port = port
        self.node_id = sha256_hash(self.ip + ':' + str(self.port))
        self.host_name = socket.gethostbyname(socket.gethostname())
        self.broadcast_port = broadcast_port
        self.chord_node = ChordNode(ip)
        self.joining_list = []  # Lista de nodos que intentan unirse
        self.database = {}
        self.trackers = set()
        self.lock = threading.Lock()  # Para sincronizar el acceso a la base de datos
        
        # Inicializar el servidor HTTP
        self.server = HTTPServer((self.ip, int(self.port)), TrackerHandler)
        logger.debug("Sali de Chord")
        threading.Thread(target=self.run_server, daemon=True).start()
        time.sleep(2)
        threading.Thread(target=self.broadcast_announce, daemon=True).start()
        time.sleep(2)
        threading.Thread(target=self.autodiscover_and_join, daemon=True).start()
        time.sleep(3)
        threading.Thread(target=self.print_current_leader, daemon=True).start()

    def run_server(self):
        logger.info(f"Servidor HTTP corriendo en {self.ip}:{self.port}")
        self.server.serve_forever()

    def broadcast_announce(self, leader=False):
        if leader:
            try:
                msg = f"NEWLEADER,{self.node_id},{self.ip},{self.port}"
                logger.info(f"Intentando crear nuevo lider: {msg}")
                bcast_call(self.broadcast_port, msg)
            except Exception as e:
                logger.error(f"Error al enviar el mensaje del primer nodo: {e}")
        else:
            try:
                msg = f"NODE,{self.node_id},{self.ip},{self.port}"
                logger.info(f"Enviando anuncio de broadcast: {msg}")
                bcast_call(self.broadcast_port, msg)
            except Exception as e:
                logger.error(f"Error al enviar el mensaje de liderazgo: {e}")  
    def autodiscover_and_join(self):
        retries = 0
        while retries < MAX_RETRIES:
            logger.info(f"Intentando descubrir nodos... intento {retries + 1}")
            for tracker in self.trackers:
                try:
                    response = self.send_http_request(tracker, "get_node_id")
                    if "node_id" in response:
                        self.trackers.add(tracker)
                        logger.info(f"Nodo encontrado: {tracker}")
                        return
                except Exception as e:
                    logger.error(f"Error al contactar con el tracker {tracker}: {e}")
            retries += 1
            time.sleep(5)  # Intentar nuevamente después de 5 segundos

        logger.warning("No se encontraron nodos para unirse después de varios intentos.")

    def send_http_request(self, tracker, action, data=None):
        url = f"http://{tracker}/{action}"
        response = None
        try:
            if data:
                response = requests.post(url, json=data)
            else:
                response = requests.get(url)
            if response.status_code == 200:
                return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"Error al hacer la solicitud HTTP: {e}")
        return {}

    def print_current_leader(self):
        while True:
            logger.info(f"El líder actual es {self.node_id} en {self.ip}:{self.port}")
            time.sleep(30)            
