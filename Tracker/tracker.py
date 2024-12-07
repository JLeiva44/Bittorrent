
import zmq
import threading
#from bclient_logger import logger
import logging
import hashlib
import multiprocessing
import time
import random
import socket
import os
from broadcast_manager import BroadcastManager
from c2 import ChordNode, ChordNodeReference
HOST = '127.0.0.1'
PORT1 = '8080'
PORT2 = '8001'
CONTAINER_NAME = os.getenv("HOSTNAME")
MAX_RETRIES = 3
BROADCAST_IP = '172.17.255.255'
DEFAULT_TIMEOUT = 5  # Timeout en segundos

logger = logging.getLogger(__name__)
def retry_on_connection_refused(func, *args, max_retries=5, delay=3, **kwargs):
    """
    Tries to execute the function 'func' with the given arguments.
    If a connection refused exception occurs, it retries the execution.

    :param func: The function to execute.
    :param args: Positional arguments for the function.
    :param max_retries: Maximum number of retries.
    :param delay: Delay time between retries (in seconds).
    :param kwargs: Keyword arguments for the function.
    :return: The result of the function if successful, None if it fails after retries.
    """
    for attempt in range(max_retries):
        try:
            return func(*args, **kwargs)
        except ConnectionRefusedError as e:
            print(
                f"Connection refused in function '{func.__name__}'. Attempt {attempt + 1} of {max_retries}."
            )
            time.sleep(delay)  # Wait before retrying
    print("Maximum number of retries reached. Function failed.")
    return None

def getShaRepr(data: str):
    return int(hashlib.sha1(data.encode()).hexdigest(), 16)


# def bcast_call(port, msg):
#     with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
#         s.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
#         s.sendto(msg.encode(), ("172.17.255.255", port))

def retry_on_connection_refused(func, *args, max_retries=5, delay=2, **kwargs):
        """
        Reintenta la ejecución de una función si ocurre un ConnectionRefusedError.

        Args:
            func (callable): La función que se desea ejecutar.
            *args: Argumentos posicionales para la función.
            max_retries (int): Número máximo de reintentos antes de rendirse.
            delay (int): Tiempo (en segundos) entre reintentos.
            **kwargs: Argumentos nombrados para la función.

        Returns:
            El resultado de la función si tiene éxito.

        Raises:
            Exception: Si se superan los intentos máximos sin éxito.
        """
        attempts = 0
        while attempts < max_retries:
            try:
                return func(*args, **kwargs)
            except ConnectionRefusedError as e:
                attempts += 1
                logger.warning(f"Intento {attempts}/{max_retries} fallido: {e}. Retentando en {delay}s...")
                time.sleep(delay)
            except Exception as e:
                logger.error(f"Error inesperado al ejecutar {func.__name__}: {e}")
                raise
        logger.critical(f"Superado el máximo de intentos ({max_retries}). Abandonando.")
        raise ConnectionRefusedError(f"No se pudo conectar tras {max_retries} intentos.")

class Tracker:
    def __init__(self, ip, port = 8080, chord_m = 160, broadcast_port = 5555 ):
        logger.info("------------------- LOGER DEL TRACKER-----------------")
        self.ip = str(ip)
        self.port = port
        self.address = "tcp://" + self.ip + ":" + str(self.port)
        logger.info(f"MY adress: {self.address}")
        self.node_id = getShaRepr(self.ip + ':' + str(self.port))
        self.host_name = socket.gethostbyname(socket.gethostname())
        
        # nodo Chord 
        self.chord_node  = ChordNode(ip)
        
        self.broadcast_manager = BroadcastManager(ip,self.chord_node,broadcast_port)


        self.joining_list = [] # Lista de nodos que intentan unirse

        # Server Sockets
        self.context = zmq.Context()
        self.socket = self.context.socket(zmq.REP)
        self.socket.bind(self.address)
        #self.socket.listen(1000)
        self.socket.RCVTIMEO = DEFAULT_TIMEOUT * 5  # Timeout en milisegundos
        
        # # Líder actual
        # self.broadcast_elector = type('', (), {})()  # Objeto vacío
        # self.broadcast_elector.Leader = None
        # self.broadcast_elector.id = None
        # self.database = {}
        # self.trackers = set()
        #self.lock = threading.Lock()  # Para sincronizar el acceso a la base de datos
        
        self._start_communication_threads()
        time.sleep(2)
        self.autodiscover_and_join()
        time.sleep(2)
        threading.Thread(target=self.broadcast_manager.periodic_broadcast, daemon=True).start()



        logger.debug(f"Soy lider??: {self.broadcast_manager.is_leader}")

        
        
            
    
    def _start_communication_threads(self):
        """Inicia los hilos de com del Tracker"""
        # Crear hilos para servidor de broadcast y ejecucion Principal
        threading.Thread(target=self.run, daemon=True).start() # Start Tracker server 
        # Excucho primero pa ver si hay un lider
        threading.Thread(target=self.broadcast_manager.listen_for_broadcast, daemon=True).start()
        time.sleep(3)

        threading.Thread(target=self.broadcast_manager.print_current_leader, daemon=True).start()

        

    
    
    def autodiscover_and_join(self):
        try:
            logger.info(f"Insertando uevo nodo en la red: {self.ip}:{self.port}")
            max_wait_time = 5  # Tiempo máximo de espera
            start_time = time.time()

            while True:
                if self.broadcast_manager.broadcast_elector.Leader:
                    # Si el nodo actual detecta un líder
                    leader_ip = self.broadcast_manager.broadcast_elector.Leader
                    if self.broadcast_manager.id > self.broadcast_manager.broadcast_elector.id:
                        logger.info("Soy el nuevo líder de la red.")
                        
                        self.broadcast_manager.broadcast_announce(leader=True)
                    else: # Si no es lider no aviso xq a nadie le importa
                        logger.info(f"Uniéndose al líder existente en {leader_ip}")
                        self.chord_node.join(ChordNodeReference(leader_ip, leader_ip))
                    break

                # Si el tiempo de espera expira, el nodo se convierte en líder
                if time.time() - start_time > max_wait_time:
                    logger.warning("No se detectaron nodos en la red. Convirtiéndome en líder.")
                    # No anuncio xq si no hay nadie en la red nadie se va a enterar
                    #self.broadcast_announce(leader=True)
                    self.broadcast_manager.broadcast_elector.Leader = self.ip
                    self.broadcast_manager.id = self.node_id
                    break

                time.sleep(1)
        except Exception as e:
            logger.error(f"Error inesperado en autodiscover_and_join: {e}", exc_info=True)

    
    
    
    def handle_leadership_change(self, new_leader_ip, new_leader_id):
        """
        Maneja la transición de liderazgo.
        """
        #with self.lock:
        was_leader = self.is_leader  # Estado anterior
        self.broadcast_elector.Leader = new_leader_ip
        self.broadcast_elector.id = new_leader_id

        if was_leader and not self.is_leader:
            logger.info(f"Este nodo ya no es el líder. Nuevo líder: {new_leader_ip} con ID {new_leader_id}")
            self.join(new_leader_ip)  # Unirse al nuevo líder
        elif not was_leader and self.is_leader:
            logger.info(f"Este nodo ahora es el líder.")

    
                
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
                #logger.debug("No se recibió mensaje dentro del período de espera.")
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
        
        # node_ref = self.chord_node.find_succ(key) 


        key = getShaRepr(pieces_sha1)
        peers = self.chord_node.find_succ(key).get_value(key) # Esto es una lista de listas [[perr_id, perr_ip, port]]
        logger.debug(f"La lista de peers que llega al tracker es {peers}")
        final_peers = []
        for peer_id, peer_ip, peer_port in peers:
            final_peers.append((peer_ip,peer_port))


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
        self.chord_node.store_key(pieces_sha1,[peer_ip,peer_ip, peer_port])
        logger.debug(f"Added {peer_ip}:{peer_port} to Node: {peer_ip}:{peer_port} for piece {pieces_sha1}")    
        

    def remove_from_database(self, pieces_sha1, ip, port):
        if not pieces_sha1 or not ip or not port:
            return {"error": "Datos incompletos para eliminar del tracker."}

        #with self.lock:
        if pieces_sha1 in self.database:
            self.database[pieces_sha1] = [
                peer for peer in self.database[pieces_sha1] if peer != (ip, port)
            ]
            if not self.database[pieces_sha1]:
                del self.database[pieces_sha1]

        logger.debug(f"Eliminado {ip}:{port} del tracker para {pieces_sha1}")
        return {"response": f"Eliminado {ip}:{port} para {pieces_sha1}"}



    def get_database(self):
        #with self.lock:
        return {"database": self.database}
        


