
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
        threading.Thread(target=self.listen_for_broadcast, daemon=True).start()
        time.sleep(2)
        threading.Thread(target=self.broadcast_announce, daemon=True).start()
        time.sleep(2)
        threading.Thread(target=self.autodiscover_and_join, daemon=True).start()

        time.sleep(3)
        threading.Thread(target=self.print_current_leader, daemon=True).start()
    
    def print_current_leader(self):
        while True:
            logger.info(f"******************LIDER ACTUAL ES : {self.broadcast_elector.Leader}******************")
            time.sleep(10)
    
    def autodiscover_and_join(self):
        try:
            logger.info(f"Nuevo nodo en la red: {self.ip}:{self.port}")
            max_wait_time = 10  # Tiempo máximo de espera
            start_time = time.time()

            logger.info("Buscando líder...")
            while True:
                if self.broadcast_elector.Leader:
                    # Si el nodo actual detecta un líder
                    leader_ip = self.broadcast_elector.Leader
                    if self.node_id > self.broadcast_elector.id:
                        logger.info("Soy el nuevo líder de la red.")
                        self.broadcast_announce(leader=True)
                    else:
                        logger.info(f"Uniéndose al líder existente en {leader_ip}")
                        self.join(leader_ip)
                    break

                # Si el tiempo de espera expira, el nodo se convierte en líder
                if time.time() - start_time > max_wait_time:
                    logger.warning("No se detectó un líder. Convirtiéndome en líder.")
                    self.broadcast_announce(leader=True)
                    break

                time.sleep(1)
        except Exception as e:
            logger.error(f"Error inesperado en autodiscover_and_join: {e}", exc_info=True)

    # # block
    # def autodiscover_and_join(self):
    #     """
    #     Determina el líder basado en los IDs de los nodos recibidos y se une a la red.
    #     Si no hay un líder después del tiempo de espera, el nodo actual se convierte en líder y comienza un anillo Chord.
    #     """
    #     try:
    #         logger.info(f"------------------------Nuevo nodo en la red : {self.ip}:{self.port}---------------------------------------")
    #         logger.info(f"Buscando Lider---------------------------------------")
    #         max_wait_time = 10  # Tiempo máximo de espera
    #         start_time = time.time()

    #         logger.info(f"Anunciando mi llegada")
    #         #self.broadcast_announce()

    #         while True:
    #             # Si ya se ha determinado un líder
    #             if self.broadcast_elector.Leader is not None:
    #                 leader_ip = self.broadcast_elector.Leader
    #                 if self.broadcast_elector.id < self.node_id:
    #                     logger.info("Soy el nuevo líder de la red.")
    #                     self.broadcast_announce(leader=True)
    #                 else:
    #                     logger.debug("Entrando al ELSE del JOIN")
    #                     self.broadcast_announce()
    #                     self.join(leader_ip)
    #                     logger.info(f"Uniéndose al líder en {leader_ip}")
    #                 break
    #             else:
    #                 logger.debug("EN este momento el lider es NONE")

    #             # Si el tiempo máximo de espera ha pasado
    #             if time.time() - start_time > max_wait_time:
    #                 logger.warning("No se detectó un líder dentro del tiempo esperado.")
    #                 logger.info("Convirtiéndome en líder y comenzando un anillo Chord.")
    #                 #self.broadcast_elector.Leader = self.ip
    #                 # Anunciar el liderazgo
    #                 self.broadcast_announce(leader=True)
    #                 break

    #             time.sleep(1)

    #     except Exception as e:
    #         logger.error(f"Error inesperado en autodiscover_and_join: {e}", exc_info=True)
    # # endblock
            
    def listen_for_broadcast(self):
        """
        Escucha continuamente mensajes de broadcast y los maneja.
        """
        logger.info("Iniciando escucha de mensajes de broadcast...")
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            s.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
            s.bind(('', self.broadcast_port))  # Escucha en todos los interfaces para el puerto especificado

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
        logger.info(f"Mensaje de broadcast recibido: {msg} de {sender_ip}")
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
                        self.broadcast_elector.Leader = leader_ip
                        self.broadcast_elector.id = leader_id
                    else:
                        logger.debug("El mensaje de NEWLEADER tiene un ID menor. Ignorando.")
        except Exception as e:
            logger.error(f"Error al manejar mensaje de broadcast: {e}")

    # def handle_broadcast_message(self, msg, sender_ip):
    #     """
    #     Maneja los mensajes de broadcast para registrar nodos y determinar el líder.
    #     """
    #     logger.info(f"Mensaje de broadcast recibido: {msg} de {sender_ip}")
    #     lider = False
    #     try:
    #         # Mensaje de Nodo
    #         if msg.startswith("NODE"):
    #             # Parsear el mensaje del nodo
    #             _, node_id, node_ip, node_port = msg.split(",")
    #             node_id = int(node_id)  # Convertir el ID a entero

    #             # Registrar nodo
    #             self.register_node(node_id, node_ip, node_port)

    #         elif msg.startswith("NEWLEADER"):
    #             _, leader_id, leader_ip, leader_port = msg.split(",")
    #             leader_id = int(leader_id)  # Convertir el ID a entero
    #             #self.register_node(leader_id, leader_ip, leader_port, first= True)
    #             self.broadcast_elector.Leader = leader_ip
    #             self.broadcast_elector.id = leader_id
        

    #     except Exception as e:
    #         logger.error(f"Error al manejar mensaje de broadcast: {e}")

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
                old_leader_ip = self.broadcast_elector.Leader  # Guardar el líder anterior
                
                # Actualizar el líder actual
                self.broadcast_elector.Leader = node_ip
                self.broadcast_elector.id = node_id
                
                # Anunciar el nuevo liderazgo
                self.broadcast_announce(leader=True)
                logger.info(f"Nuevo líder elegido: {node_ip} con ID {node_id}")
                
                # Si este nodo era el líder anterior, debe unirse al nuevo líder
                if self.ip == old_leader_ip:
                    logger.info(f"Este nodo era el líder anterior. Ahora se unirá al nuevo líder en {node_ip}.")
                    self.join(node_ip)


    # def register_node(self, node_id, node_ip, node_port):
    #     """
    #     Registra un nodo en la red y actualiza el líder si es necesario.
    #     """
    #     logger.info(f"Registrando nodo: ID={node_id}, IP={node_ip}, Port={node_port} en la red")

    #     with self.lock:
    #         # Registrar nodo en la lista de nodos
    #         self.trackers.add((node_id, node_ip, node_port))

    #         # Elegir líder si el nodo tiene un ID mayor
    #         #if self.broadcast_elector.Leader is None or node_id > self.node_id:
    #         if node_id > self.node_id:    
    #             self.broadcast_elector.Leader = node_ip  # Elegir nuevo líder
    #             self.broadcast_announce(leader=True)
    #             logger.info(f"Nuevo líder elegido: {node_ip} con ID {node_id}")
 
                
    def broadcast_announce(self, leader = False):
        """
        Anuncia el nodo actual mediante broadcast.
        """
        if leader:
            try:
                msg = f"NEWLEADER,{self.node_id},{self.ip},{self.port}"
                logger.info(f"Intentando crear nuevo lider : {msg}")
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
        


