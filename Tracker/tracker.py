
import zmq
import threading
from Client.bclient_logger import logger
import hashlib

HOST = '127.0.0.1'
PORT1 = '8080'
PORT2 = '8001'

def sha256_hash(s):
    return int(hashlib.sha256(s.encode()).hexdigest(), 16)


class Tracker:
    def __init__(self, ip, port):
        self.ip = ip
        self.port = port
        self.address = "tcp://" + self.ip + ":" + str(self.port)
        self.node_id = sha256_hash(self.ip + ':' + str(self.port))

        self.context = zmq.Context()
        self.socket = self.context.socket(zmq.REP)
        self.socket.bind(self.address)

        self.database = {}

        threading.Thread(target=self.run, daemon=True).start() # Start Tracker server thread


    def run(self):
        logger.debug(f"Tracker corriendo en {self.address}")
        while True:
            try:
                # Esperar por un mensaje de un peer
                message = self.socket.recv_json()
                print(f"Mensaje recibido: {message}")
                
                # Respuesta
                response = self.handle_request(message)
                self.socket.send_json(response)

            except zmq.ZMQError as e:
                print(f"ZMQError occurred: {e}")
            except Exception as e:
                print(f"An error occurred in the tracker: {e}") 

    def handle_request(self, message):
        action = message.get("action")
        
        if action == "get_peers":
            return self.get_peers(message["pieces_sha1"])
        elif action == "add_to_database":
            return self.add_to_database(message["pieces_sha1"], message["peer"][0], message["peer"][1]) # peer[o] = ip, peer[1] puerto
        elif action == "remove_from_database":
            return self.remove_from_database(message["pieces_sha1"], message["ip"], message["port"])
        elif action == "get_database":
            return self.get_database()
        elif action == "get_node_id":
            return {"node_id": self.node_id}
        elif action == "set_successor":
            return self.set_successor(message["node"])
        elif action == "set_predecessor":
            return self.set_predecessor(message["node"])
        else:
            return {"error": "Unknown action"}
        

    def get_peers(self, pieces_sha1):
        #pieces_sha256 = sha256_hash(pieces_sha1)
        
        if pieces_sha1 in self.database:
            return {"peers": self.database[pieces_sha1]}
        
        return {"peers": []} 

    def add_to_database(self, pieces_sha256, ip, port):
        if pieces_sha256 not in self.database:
            self.database[pieces_sha256] = []
        
        if (ip, port) not in self.database[pieces_sha256]:
            self.database[pieces_sha256].append((ip, port))
        
        logger.debug(f"Added {ip}:{port} to database for piece {pieces_sha256}")   
        return {"reponse":f"Added {ip}:{port} to database for piece {pieces_sha256}"}


    def remove_from_database(self, pieces_sha1, ip, port):
        pieces_sha256 = sha256_hash(pieces_sha1)
        
        if pieces_sha256 in self.database and (ip, port) in self.database[pieces_sha256]:
            self.database[pieces_sha256].remove((ip, port))
            logger.debug(f"Removed {ip}:{port} from database for piece {pieces_sha256}")   



    def get_database(self):
        return {"database": self.database}