
import zmq
import threading
#from bclient_logger import logger
import logging
import hashlib
import multiprocessing
import time
import random
import socket
from broadcast_manager import BroadcastManager
import os
from broadcast_pow_elector import BroadcastPowElector, PORT as bpowe_port
from chord import ChordNode, ChordNodeReference
HOST = '127.0.0.1'
PORT1 = '8080'
PORT2 = '8001'
CONTAINER_NAME = os.getenv("HOSTNAME")
MAX_RETRIES = 3
BROADCAST_IP = '172.17.255.255'

logger = logging.getLogger(__name__)

def sha256_hash(s):
    return int(hashlib.sha256(s.encode()).hexdigest(), 16)

def getShaRepr(data: str):
    return int(hashlib.sha1(data.encode()).hexdigest(), 16)

def bcast_call(port, msg):
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
        s.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        s.sendto(msg.encode(), ("172.17.255.255", port))

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
    def __init__(self, ip, port, chord_m = 8, broadcast_port = 5555 ):
        logger.info("------------------- LOGER DEL TRACKER-----------------")
        self.ip = ip
        self.port = port
        self.address = "tcp://" + self.ip + ":" + str(self.port)
        self.node_id = sha256_hash(self.ip + ':' + str(self.port))
        self.host_name = socket.gethostbyname(socket.gethostname())
        self.broadcast_port = broadcast_port

        # nodo Chord 
        self.chord_node  = None
        self.context = zmq.Context()
        # Inicializar BroadcastPowElector
        self.broadcast_elector = BroadcastPowElector(
            port=broadcast_port,
            base_hash=hashlib.sha256(f"Tracker:{self.ip}:{self.port}".encode()).hexdigest(),
            difficulty=5,
        )

        self.joining_list = [] # Lista de nodos que intentan unirse


        
        # Server Sockets
        self.socket = self.context.socket(zmq.REP)
        self.socket.bind(self.address)
        self.socket.RCVTIMEO = 5000  # Timeout de 5 segundos para evitar bloqueos
        
        
        self.database = {}
        self.trackers = set()
        #self.broadcast_manager = BroadcastManager(ip,broadcast_port)
        self.lock = threading.Lock()  # Para sincronizar el acceso a la base de datos
        
        # Crear hilos para servidor de broadcast y ejecucion Principal
        threading.Thread(target=self.run, daemon=True).start() # Start Tracker server thread
        threading.Thread(target=self.start_election_process, daemon=True).start()
        time.sleep(2)
        threading.Thread(target=self.join_pool, daemon=True).start()
        time.sleep(2)
        # Autodescubrimiento y unión
        threading.Thread(target=self.autodiscover_and_join, daemon=True).start()


    def start_election_process(self):
        """
        Inicia el proceso de elección de líder utilizando BroadcastPowElector.
        """
        try:
            logger.info("Iniciando proceso de elección de líder")
            self.broadcast_elector.loop()
        except Exception as e:
            logger.error(f"Error critico en el proceso de eleccion: {e}", exc_info=True)
            raise # Propaga el error si es critico    

    def autodiscover_and_join(self):
        """
        Unirse a la red utilizando el líder elegido por BroadcastPowElector.
        """
        try:
            logger.info("Esperando la elección del líder...")
            max_wait_time = 30  # Tiempo máximo en segundos para esperar a un líder
            start_time = time.time()

            while self.broadcast_elector.Leader is None:
                if time.time() - start_time > max_wait_time:
                    logger.error("Tiempo de espera agotado para la elección del líder.")
                    raise TimeoutError("No se eligió líder dentro del tiempo esperado.")
                time.sleep(1)  # Esperar un segundo antes de verificar de nuevo

            leader_ip = self.broadcast_elector.Leader
            
            #inventando
            # p = multiprocessing.Process(
            #         target=bcast_call,
            #         args=(int(self.broadcast_port), f"JOIN,{leader_ip}"),
            #     )
            # p.start()
            if leader_ip == self.ip:
                logger.info("Soy el líder de la red.")
                self.chord_node = ChordNode(self.ip)
            else: # Ya hay lider
                logger.info(f"Uniéndose al líder en {leader_ip}")
                self.join(leader_ip)
        except TimeoutError as e:
            logger.critical(f"Error crítico en autodiscover_and_join: {e}")
        # Opcionalmente, intentar una estrategia alternativa como reiniciar la elección
        except Exception as e:
            logger.error(f"Error inesperado en autodiscover_and_join: {e}", exc_info=True)
        

    def join_pool(self):
        """
        Procesa nodos en cola para unirse al anillo Chord.
        """
        logger.info("Iniciando ell procesamiento de la cla de nodos para unirse.")
        while True:
            try:
                if len(self.joining_list) > 0:
                    node_ip = self.joining_list.pop(0)
                    logger.info(f"Intentando unir el nodo {node_ip} al anillo Chord.")
                    self.join(node_ip)
                time.sleep(5)
            except Exception as e:
                logger.error(f"Error al procesar la cola de unión: {e}", exc_info=True)
            finally:
                time.sleep(5)  # Esperar antes de intentar procesar el siguiente nodo
    

    def join(self, node_ip, node_port=8001):
        """
        Realiza la unión a un nodo en el anillo Chord.
        """
        logger.debug(f"Haciendo JOIN desde {self.ip} a {node_ip}")
        try:
            logger.info(f"Intentando unirse al nodo en {node_ip}:{node_port}")
            retry_on_connection_refused(
                self.chord_node.join, ChordNodeReference(node_ip)
            )
            logger.info(f"Union exitoda al nodo en {node_ip}:{node_port}")
        except ConnectionRefusedError as e:
            logger.warning(f"Conexión rechazada por el nodo {node_ip}:{node_port}: {e}")
        except Exception as e:
            logger.error(f"Error crítico al unirse al nodo {node_ip}:{node_port}: {e}", exc_info=True)        
    
    
            
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
        


