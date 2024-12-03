
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
        self.ip = str(ip)
        self.port = port
        self.address = "tcp://" + self.ip + ":" + str(self.port)
        self.node_id = sha256_hash(self.ip + ':' + str(self.port))
        self.host_name = socket.gethostbyname(socket.gethostname())
        self.broadcast_port = broadcast_port

        # nodo Chord 
        self.chord_node  = ChordNode(ip)
        


        self.joining_list = [] # Lista de nodos que intentan unirse


        
        # Server Sockets
        self.context = zmq.Context()
        self.socket = self.context.socket(zmq.REP)
        self.socket.bind(self.address)
        self.socket.RCVTIMEO = 5000  # Timeout de 5 segundos para evitar bloqueos
        
        # Líder actual
        self.broadcast_elector = type('', (), {})()  # Objeto vacío
        self.broadcast_elector.Leader = None
        self.broadcast_elector.id = None

        
        self.database = {}
        self.trackers = set()
        self.lock = threading.Lock()  # Para sincronizar el acceso a la base de datos
        
        # Crear hilos para servidor de broadcast y ejecucion Principal
        threading.Thread(target=self.run, daemon=True).start() # Start Tracker server thread
        # threading.Thread(target=self.listen_for_broadcast, daemon=True).start()
        # time.sleep(2)
        # #threading.Thread(target=self.broadcast_announce, daemon=True).start()
        # self.start_periodic_broadcast()
        # time.sleep(2)
        # threading.Thread(target=self.autodiscover_and_join, daemon=True).start()

        # time.sleep(3)
        # threading.Thread(target=self.print_current_leader, daemon=True).start()
    
    def print_current_leader(self):
        while True:
            logger.info(f"******************LIDER ACTUAL ES : {self.broadcast_elector.Leader}******************")
            time.sleep(10)
    
    def autodiscover_and_join(self):
        try:
            logger.info(f"Nuevo nodo en la red: {self.ip}:{self.port}")
            max_wait_time = 10  # Tiempo máximo de espera
            start_time = time.time()

            while True:
                if self.broadcast_elector.Leader:
                    # Si el nodo actual detecta un líder
                    leader_ip = self.broadcast_elector.Leader
                    if self.node_id > self.broadcast_elector.id:
                        logger.info("Soy el nuevo líder de la red.")
                        self.broadcast_announce(leader=True)
                    else:
                        logger.info(f"Uniéndose al líder existente en {leader_ip}")
                        self.chord_node.join(ChordNodeReference(leader_ip))
                    break

                # Si el tiempo de espera expira, el nodo se convierte en líder
                if time.time() - start_time > max_wait_time:
                    logger.warning("No se detectó un líder. Convirtiéndome en líder.")
                    self.broadcast_announce(leader=True)
                    break

                time.sleep(1)
        except Exception as e:
            logger.error(f"Error inesperado en autodiscover_and_join: {e}", exc_info=True)

    
    def listen_for_broadcast(self):
        """
        Escucha continuamente mensajes de broadcast y los maneja.
        """
        logger.info("Iniciando escucha de mensajes de broadcast...")
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            s.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
            s.bind((BROADCAST_IP, self.broadcast_port))  # Escucha en todos los interfaces para el puerto especificado

            while True:
                try:
                    data, addr = s.recvfrom(1024)  # Tamaño del búfer: 1024 bytes
                    message = data.decode()
                    sender_ip = addr[0]
                    logger.info(f"Mensaje recibido de {sender_ip}: {message}")
                    self.handle_broadcast_message(message, sender_ip)
                except Exception as e:
                    logger.error(f"Error al escuchar mensajes de broadcast: {e}", exc_info=True)

    def handle_broadcast_message(self, msg, sender_ip):
        #logger.info(f"Mensaje de broadcast recibido: {msg} de {sender_ip}")
        try:
            if msg.startswith("NODE"):
                _, node_id, node_ip, node_port = msg.split(",")
                node_id = int(node_id)
                self.register_node(node_id, node_ip, node_port)

            elif msg.startswith("NEWLEADER"):
                _, leader_id, leader_ip, leader_port = msg.split(",")
                leader_id = int(leader_id)
                
                with self.lock:
                    # Solo actualizar si el líder actual es nulo o el nuevo líder tiene un ID más alto
                    if not self.broadcast_elector.Leader or leader_id > self.broadcast_elector.id:
                        logger.info(f"Nuevo líder detectado: {leader_ip} con ID {leader_id}")
                        #self.handle_leadership_change(leader_ip, leader_id)
                        self.broadcast_elector.Leader = leader_ip
                        self.broadcast_elector.id = leader_id
                        self.chord_node.join(ChordNodeReference(leader_ip))
                    elif leader_id < self.node_id:
                        # Anunciarse como líder si se recibe un líder con ID menor
                        self.broadcast_announce(leader=True)
                time.sleep(2)        
        except Exception as e:
            logger.error(f"Error al manejar mensaje de broadcast: {e}")

    
    def handle_leadership_change(self, new_leader_ip, new_leader_id):
        """
        Maneja la transición de liderazgo.
        """
        with self.lock:
            was_leader = self.is_leader  # Estado anterior
            self.broadcast_elector.Leader = new_leader_ip
            self.broadcast_elector.id = new_leader_id

            if was_leader and not self.is_leader:
                logger.info(f"Este nodo ya no es el líder. Nuevo líder: {new_leader_ip} con ID {new_leader_id}")
                self.join(new_leader_ip)  # Unirse al nuevo líder
            elif not was_leader and self.is_leader:
                logger.info(f"Este nodo ahora es el líder.")

    def register_node(self, node_id, node_ip, node_port):
        """
        Registra un nodo en la red y actualiza el líder si es necesario.
        Si el nodo actual era el líder y se detecta un nuevo líder, el nodo actual se une al nuevo líder.
        """
        logger.info(f"Registrando nodo: ID={node_id}, IP={node_ip}, Port={node_port}")
        
        with self.lock:
            # Agregar el nodo a la lista de trackers
            self.trackers.add((node_id, node_ip, node_port))
            
            # Determinar si el nuevo nodo debe ser el líder
            if node_id > self.node_id and (not self.broadcast_elector.Leader or node_id > self.broadcast_elector.id):
                #self.handle_leadership_change(node_ip, node_id)
                old_leader_ip = self.broadcast_elector.Leader  # Guardar el líder anterior
                
                # Actualizar el líder actual
                self.broadcast_elector.Leader = node_ip
                self.broadcast_elector.id = node_id
                
                # Anunciar el nuevo liderazgo
                self.broadcast_announce(leader=True)
                logger.info(f"Nuevo líder elegido: {node_ip} con ID {node_id}")
                
                # Si este nodo era el líder anterior, debe unirse al nuevo líder
                if self.is_leader:
                    logger.info(f"Este nodo era el líder anterior. Ahora se unirá al nuevo líder en {node_ip}.")
                    self.chord_node.join(ChordNodeReference(node_ip))
            else :
                bcast_call(self.broadcast_port,msg = '{}')
        time.sleep(2)            


    @property
    def is_leader(self):
        """
        Determina si este nodo es el líder actual.
        """
        return self.broadcast_elector.Leader == self.ip and self.broadcast_elector.id == self.node_id


    def start_periodic_broadcast(self):
        """
        Inicia un hilo para enviar anuncios periódicos.
        """
        def periodic_broadcast():
            while True:
                try:
                    if self.is_leader:
                        self.broadcast_announce(leader=True)
                    else:
                        self.broadcast_announce()
                    time.sleep(10)  # Intervalo entre anuncios (10 segundos)
                except Exception as e:
                    logger.error(f"Error en broadcast periódico: {e}")

        # Crear un hilo para el broadcast periódico
        threading.Thread(target=periodic_broadcast, daemon=True).start()

                
    def broadcast_announce(self, leader=False):
        """
        Anuncia el estado del nodo actual mediante broadcast.
        """
        try:
            if leader:
                msg = f"NEWLEADER,{self.node_id},{self.ip},{self.port}"
                logger.info(f"Anunciando nuevo líder: {msg}")
            else:
                msg = f"NODE,{self.node_id},{self.ip},{self.port}"
                logger.info(f"Anunciando nodo: {msg}")

            # Llamada al método de broadcast
            bcast_call(self.broadcast_port, msg)
        except Exception as e:
            logger.error(f"Error al enviar mensaje de broadcast: {e}")

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
        


