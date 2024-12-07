import socket
import json
from tracker_logger import logger
import time
from c2 import ChordNode, ChordNodeReference
import hashlib
BROADCAST_IP = '172.17.255.255'

def getShaRepr(data: str):
    return int(hashlib.sha1(data.encode()).hexdigest(), 16)



class BroadcastManager:
    def __init__(self, ip,chordnode, port = 5555):
        self.ip = ip  # Dirección de broadcast
        self.port = port
        self.id = getShaRepr(ip)
        self.chord_node = chordnode
        self.im_current_leader = False

        logger.info(f"Iniciando Broadcast Manager con ID:{self.id}")

        # # Configuración de sockets
        # self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        # self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        # self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        # self.sock.bind(("", port))

        # Líder actual
        self.broadcast_elector = type('', (), {})()  # Objeto vacío
        self.broadcast_elector.Leader = None
        self.broadcast_elector.id = None

    

    def listen_for_broadcast(self):
        """
        Escucha continuamente mensajes de broadcast y los maneja.
        """
        logger.info("Iniciando escucha de mensajes de broadcast...")
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            s.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
            s.bind((BROADCAST_IP, self.port))  # Escucha en todos los interfaces para el puerto especificado
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
        try:
            if msg.startswith("NODE"):
                _, node_id, node_ip, node_port = msg.split(",")
                #self.register_node(node_id, node_ip, node_port)
                # Por ahora no me interesa saber nada de los que no son lider

            elif msg.startswith("NEWLEADER"):
                _,leader_id, leader_ip, leader_port = msg.split(",")
                #self.register_node(leader_id, leader_ip, leader_port)

                # Si el anterior lider era yocy el nuevo no soy yo mismo: 
                if self.is_leader and self.broadcast_elector.Leader != leader_ip:
                    # Entonces tengo quye hacer join con el actual
                    self.chord_node.join(ChordNodeReference(1,leader_ip))

                self.broadcast_elector.Leader = leader_ip
                self.broadcast_elector.id = int(leader_id)
                logger.debug(f"handle {leader_ip}, {leader_id}")


            
                # #with self.lock:
                # # Solo actualizar si el líder actual es nulo o el nuevo líder tiene un ID más alto
                # if not self.broadcast_elector.Leader or leader_id > self.broadcast_elector.id:
                #     logger.info(f"Nuevo líder detectado: {leader_ip} con ID {leader_id}")
                #     #self.handle_leadership_change(leader_ip, leader_id)
                #     self.broadcast_elector.Leader = leader_ip
                #     self.broadcast_elector.id = leader_id
                #     self.chord_node.join(ChordNodeReference(leader_ip))
                # elif leader_id < self.node_id:
                #     # Anunciarse como líder si se recibe un líder con ID menor
                #     self.broadcast_announce(leader=True)
                # time.sleep(2)        
        except Exception as e:
            logger.error(f"Error al manejar mensaje de broadcast: {e}")

    # def register_node(self, node_ip, node_port):
    #     """
    #     Registra un nodo en la red y actualiza el líder si es necesario.
    #     Si el nodo actual era el líder y se detecta un nuevo líder, el nodo actual se une al nuevo líder.
    #     """
    #     logger.info(f"Registrando nodo: IP={node_ip}, Port={node_port}")
        
    #     #with self.lock:
    #     # Agregar el nodo a la lista de trackers
    #     self.trackers.add((node_ip, node_port))
        
    #     # Determinar si el nuevo nodo debe ser el líder
    #     if node_id > self.node_id and (not self.broadcast_elector.Leader or node_id > self.broadcast_elector.id):
    #         #self.handle_leadership_change(node_ip, node_id)
    #         old_leader_ip = self.broadcast_elector.Leader  # Guardar el líder anterior
            
    #         # Actualizar el líder actual
    #         self.broadcast_elector.Leader = node_ip
    #         self.broadcast_elector.id = node_id
            
    #         # Anunciar el nuevo liderazgo
    #         self.broadcast_announce(leader=True)
    #         logger.info(f"Nuevo líder elegido: {node_ip} con ID {node_id}")
            
    #         # Si este nodo era el líder anterior, debe unirse al nuevo líder
    #         if self.is_leader:
    #             logger.info(f"Este nodo era el líder anterior. Ahora se unirá al nuevo líder en {node_ip}.")
    #             self.chord_node.join(ChordNodeReference(node_ip))
    #     else :
    #         bcast_call(self.broadcast_port,msg = '{}')
    #     time.sleep(2)            


    @property
    def is_leader(self):
        """
        Determina si este nodo es el líder actual.
        """
        return self.broadcast_elector.Leader == self.ip 


    def print_current_leader(self):
        while True:
            logger.info(f"******************LIDER ACTUAL ES : {self.broadcast_elector.Leader}******************")
            time.sleep(20)

    def periodic_broadcast(self):
        while True:
            if self.is_leader:
                try:
                    self.broadcast_announce(leader=True)
                    logger.debug("anunciando que todavia soy lider")
                    #else:
                        #self.broadcast_announce() Creo que x ahora no me interersa saber quien esta en la red
                    time.sleep(2)  # Intervalo entre anuncios (10 segundos)
                except Exception as e:
                    logger.error(f"Error en broadcast periódico: {e}")


                
    def broadcast_announce(self, leader=False):
        """
        Anuncia el estado del nodo actual mediante broadcast.
        """
        try:
            if leader:
                msg = f"NEWLEADER,{self.id},{self.ip},{self.port}"
                logger.info(f"Anunciando líder: {self.ip}")
                #self.broadcast_elector.Leader = self.ip
                #self.broadcast_elector.id = self.node_id
            else:
                msg = f"NODE,{self.id},{self.ip},{self.port}"
                logger.info(f"Anunciando nodo: {msg}")

            # Llamada al método de broadcast
            bcast_call(self.port, msg)
        except Exception as e:
            logger.error(f"Error al enviar mensaje de broadcast: {e}")


def autodiscover_and_join(self):
        try:
            logger.info(f"Insertando uevo nodo en la red: {self.ip}:{self.port}")
            max_wait_time = 4  # Tiempo máximo de espera
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
                        self.chord_node.join(ChordNodeReference(1,leader_ip))
                    break

                # Si el tiempo de espera expira, el nodo se convierte en líder
                if time.time() - start_time > max_wait_time:
                    logger.warning("No se detectó un líder. Convirtiéndome en líder.")
                    self.broadcast_announce(leader=True)
                    break

                time.sleep(1)
        except Exception as e:
            logger.error(f"Error inesperado en autodiscover_and_join: {e}", exc_info=True)


def bcast_call(port, msg, attempts=3, delay=2):
    """
    Enviar un mensaje de broadcast con un número fijo de intentos.

    :param port: Puerto de destino.
    :param msg: Mensaje a enviar.
    :param attempts: Número de intentos máximos de reenvío.
    :param delay: Tiempo de espera entre intentos fallidos (en segundos).
    """
    for attempt in range(attempts):
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
                s.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
                s.sendto(msg.encode(), ("172.17.255.255", port))
                logger.info(f"Mensaje enviado en intento {msg}")
                return  # Salir si el envío fue exitoso
        except Exception as e:
            logger.error(f"Error al enviar el mensaje en intento {attempt + 1}: {e}")
            if attempt < attempts - 1:
                time.sleep(delay)  # Esperar antes de reintentar
    logger.error(f"No se pudo enviar el mensaje tras {attempts} intentos")