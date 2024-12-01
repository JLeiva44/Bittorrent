
import zmq
import threading
#from bclient_logger import logger
import logging
import hashlib
import time
from chord import ChordNode
HOST = '127.0.0.1'
PORT1 = '8080'
PORT2 = '8001'

logger = logging.getLogger(__name__)

def sha256_hash(s):
    return int(hashlib.sha256(s.encode()).hexdigest(), 16)

def getShaRepr(data: str):
    return int(hashlib.sha1(data.encode()).hexdigest(), 16)

class Tracker:
    def __init__(self, ip, port, chord_m = 8):
        self.ip = ip
        self.port = port
        self.address = "tcp://" + self.ip + ":" + str(self.port)
        self.node_id = sha256_hash(self.ip + ':' + str(self.port))

        # nodo Chord 
        self.chord_node  = ChordNode(ip,m=chord_m)
        self.context = zmq.Context()
        self.socket = self.context.socket(zmq.REP)
        self.socket.bind(self.address)
        self.socket.RCVTIMEO = 5000  # Timeout de 5 segundos para evitar bloqueos

        self.database = {}
        self.lock = threading.Lock()  # Para sincronizar el acceso a la base de datos
        
        threading.Thread(target=self.run, daemon=True).start() # Start Tracker server thread


    def run(self):
        logger.debug(f"Tracker corriendo en {self.address}")
        retry_attempts = 0
        max_retries = 5  # Límite de intentos de reinicio
        retry_delay = 2  # Segundos entre intentos de reinicio

        while True:
            try:
                # Esperar por un mensaje de un peer
                message = self.socket.recv_json()
                logger.debug(f"Mensaje recibido: {message}")
                
                # Respuesta
                response = self.handle_request(message)
                self.socket.send_json(response)

                # Reiniciar contador de intentos en caso de éxito
                retry_attempts = 0

            except zmq.Again:
                # Timeout alcanzado, continuar escuchando
                logger.debug("No se recibió mensaje dentro del período de espera.")
                continue

            except zmq.ZMQError as e:
                logger.error(f"ZMQError ccritico: {e}")
                retry_attempts +=1

                if retry_attempts > max_retries:
                    logger.critical(f"Superado el límite de reinicios ({max_retries}). Servidor detenido.")
                    break

                logger.info(f"Reiniciando servidor en {retry_delay} segundos (Intento {retry_attempts}/{max_retries})")
                time.sleep(retry_delay)
                self._restart_socket()

            except Exception as e:
                logger.error(f"Error en el tracker: {e}")
        logger.debug("El servidor se ha detenido")            

    def handle_request(self, message):
        if not isinstance(message, dict) or "action" not in message:
            return {"error": "Mensaje mal formado."}
        
        action = message.get("action")
        
        try:
            if action == "get_peers":
                return self.get_peers(message.get("pieces_sha1", ""))
            elif action == "add_to_database":
                return self.add_to_database(
                    message.get("pieces_sha1", ""),
                    message.get("peer", [None, None])[0],
                    message.get("peer", [None, None])[1],
                )
            elif action == "remove_from_database":
                return self.remove_from_database(
                    message.get("pieces_sha1", ""),
                    message.get("ip", ""),
                    message.get("port", ""),
                )
            elif action == "get_database":
                return self.get_database()
            elif action == "get_node_id":
                return {"node_id": self.node_id}
            else:
                return {"error": "Acción desconocida."}

        except KeyError as e:
            logger.error(f"Clave faltante en el mensaje: {e}")
            return {"error": f"Clave faltante: {e}"}

        except Exception as e:
            logger.error(f"Error al manejar la solicitud: {e}")
            return {"error": f"Error interno: {e}"}
        

    def get_peers(self, pieces_sha1):
        if not pieces_sha1:
            return {"error": "Se requiere el hash de la pieza."}

        # Buscar el nodo correspondiente en el anillo Chord para la pieza
        #node_ref = self.chord_node.ref.find_succ(sha256_hash(pieces_sha1))
        
        # key = getShaRepr(pieces_sha1)
        # node_ref = self.chord_node.find_succ(key) 


        peers = self.chord_node.retrieve_key(pieces_sha1)
        logger.debug(f"La lista de peers que llega al tracker es {peers}")
        final_peers = []
        for peer in peers:
            peer = peer.split(":")
            final_peers.append((peer[0],peer[1]))


        logger.debug(f"Getting Peers for piece {pieces_sha1}")
        logger.debug(f"Peers {final_peers}")
        return {"peers": final_peers}
        
        # Version Centralizada
        # with self.lock:
        #     peers = self.database.get(pieces_sha1, [])
        # return {"peers": peers}

    def add_to_database(self, pieces_sha1,peer_ip, peer_port):
        print("Entre al metodo add to databse")
        if not pieces_sha1 or not peer_ip or not peer_port:
            return {"error": "Datos incompletos para agregar al tracker."}

        # Obtener el nodo correspondiente en el anillo Chord para la pieza
        #node_ref = self.chord_node.find_succ(sha256_hash(pieces_sha1)) # Ver si es asi o solo con sha1

        # key = getShaRepr(pieces_sha1)
        # node_ref = self.chord_node.find_succ(key) # Ver si es asi o solo con sha1
        #TODOO ESTO YA LO HACE EL METODO store_key
        
        # Almacenar los datos
        peer = f'{peer_ip}:{peer_port}'
        self.chord_node.store_key(pieces_sha1,peer)
        logger.debug(f"Added {peer_ip}:{peer_port} to Node: {peer_ip}:{peer_port} for piece {pieces_sha1}")    
        

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

        logger.debug(f"Eliminado {ip}:{port} del tracker para {pieces_sha1}")
        return {"response": f"Eliminado {ip}:{port} para {pieces_sha1}"}



    def get_database(self):
        with self.lock:
            return {"database": self.database}
        


