import socket
import threading
import sys
import time
import hashlib
import json 
import os
from tracker_logger import logger
from collections import defaultdict
# Operation codes
FIND_SUCCESSOR = 1
FIND_PREDECESSOR = 2
GET_SUCCESSOR = 3
GET_PREDECESSOR = 4
NOTIFY = 5
CHECK_PREDECESSOR = 6
CLOSEST_PRECEDING_FINGER = 7
STORE_KEY = 8
RETRIEVE_KEY = 9


def getShaRepr(data: str):
    """Function to hash a string using SHA-1 and return its integer representation"""
    return int(hashlib.sha1(data.encode()).hexdigest(), 16)

class ChordNodeReference:
    """
    Class to reference a Chord node
    """
    def __init__(self, ip: str, port: int = 8001):
        self.id = getShaRepr(ip)
        self.ip = ip
        self.port = port
        logger.debug(f"CHordReference {self,ip, self.port}")


    def _send_data(self, op: int, data: str = None, retries : int = 3) -> bytes:
        """Envia datos a otro nodo con manejo de reintentos."""
        for _ in range(retries):
            try:
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                    s.connect((self.ip, self.port))
                    s.sendall(f'{op},{data}'.encode('utf-8'))
                    return s.recv(1024)
            except socket.timeout as e:
                logger.warning(f"Timeout error while sending data to {self.ip}:{self.port}: {e}")
            except socket.error as e:
                logger.warning(f"Socket error while sending data to {self.ip}:{self.port}: {e}")    
            except Exception as e:
                logger.warning(f"Retrying to send data to {self.ip}:{self.port} due to error: {e}")
                time.sleep(1)
        logger.error(f"Failed to send data to {self.ip}:{self.port} after {retries} retries") 
        raise Exception(f"No se pudo contactar nodo {self.ip}:{self.port}.")
           
    
    def find_successor(self, id: int) -> 'ChordNodeReference':
        """Method to find the successor of a given id"""
        response = self._send_data(FIND_SUCCESSOR, str(id)).decode().split(',')
        return ChordNodeReference(response[1], self.port)

    # Method to find the predecessor of a given id
    def find_predecessor(self, id: int) -> 'ChordNodeReference':
        response = self._send_data(FIND_PREDECESSOR, str(id)).decode().split(',')
        return ChordNodeReference(response[1], self.port)

    # Property to get the successor of the current node
    @property
    def succ(self) -> 'ChordNodeReference':
        response = self._send_data(GET_SUCCESSOR).decode().split(',')
        logger.debug(f"Pidiendo el succ de {self.ip}")
        return ChordNodeReference(response[1], self.port)

    # Property to get the predecessor of the current node
    @property
    def pred(self) -> 'ChordNodeReference':
        response = self._send_data(GET_PREDECESSOR).decode().split(',')
        return ChordNodeReference(response[1], self.port)

    # Method to notify the current node about another node
    def notify(self, node: 'ChordNodeReference'):
        self._send_data(NOTIFY, f'{node.id},{node.ip}')

    # Method to check if the predecessor is alive
    def check_predecessor(self):
        self._send_data(CHECK_PREDECESSOR)

    # Method to find the closest preceding finger of a given id
    def closest_preceding_finger(self, id: int) -> 'ChordNodeReference':
        response = self._send_data(CLOSEST_PRECEDING_FINGER, str(id)).decode().split(',')
        return ChordNodeReference(response[1], self.port)

    # Method to store a key-value pair in the current node
    def store_key(self, key: str, value: str):
        self._send_data(STORE_KEY, f'{key},{value}')

    # Method to retrieve a value for a given key from the current node
    def retrieve_key(self, key: str) -> str:
        response = self._send_data(RETRIEVE_KEY, key).decode()
        return eval(response) if response != "[]" else []

    def __str__(self) -> str:
        return f'{self.id},{self.ip},{self.port}'

    def __repr__(self) -> str:
        return str(self)


# Class representing a Chord node
class ChordNode:
    def __init__(self, ip: str, port: int = 8001, m: int = 160):
        self.id = getShaRepr(ip)
        self.ip = ip
        self.port = port
        self.ref = ChordNodeReference(self.ip, self.port)
        self.succ = self.ref  # Initial successor is itself
        self.pred = None  # Initially no predecessor
        self.m = m  # Number of bits in the hash/key space
        self.finger = [self.ref] * self.m  # Finger table
        self.next = 0  # Finger table index to fix next
        self.data = defaultdict(list)  # Dictionary to store key-value pairs with load balancing
        #self.lock = threading.Lock() # lock to protect shared resources
        self.load_data_from_disk()

        # Start background threads for stabilization, fixing fingers, and checking predecessor
        threading.Thread(target=self.stabilize, daemon=True).start()  # Start stabilize thread
        threading.Thread(target=self.fix_fingers, daemon=True).start()  # Start fix fingers thread
        threading.Thread(target=self.check_predecessor, daemon=True).start()  # Start check predecessor thread
        threading.Thread(target=self.start_server, daemon=True).start()  # Start server thread
        threading.Thread(target=self.show_my_data, daemon=True).start()
        threading.Thread(target=self.auto_save_data, daemon=True).start() # Guardar datos periodicamente

        logger.debug(f"Inicializando Nodo Chord con ID={self.id} en {self.ip}:{self.port}")

    def show_my_data(self):
        while True:
            try:
                logger.info("--------Mostrando mis datos-------")
                for key in self.data:
                    logger.info(f"{key}:{self.data[key]}")
                logger.info("-----------------------------------")
            except Exception as e:
                logger.error(f"Error en show_my_data: {e}")    
            time.sleep(30)    

    def auto_save_data(self):
        """Guardar datos periódicamente en disco."""
        while True:
            self.save_data_to_disk()
            time.sleep(60)  # Guardar cada 60 segundos

    def _inbetween(self, k: int, start: int, end: int) -> bool:
        '''Helper method to check if a value is in the range (start, end]'''
        if start < end:
            return start < k <= end
        else:  # Interval wraps around 0
            return start < k or k <= end

    def find_succ(self, id: int) -> 'ChordNodeReference':
        '''Method to find the successor of a given id'''
        node = self.find_pred(id)  # Find predecessor of id
        return node.succ  # Return successor of that node

    # Method to find the predecessor of a given id
    def find_pred(self, id: int) -> 'ChordNodeReference':
        node = self
        while not self._inbetween(id, node.id, node.succ.id):
            node = node.closest_preceding_finger(id)
        return node

    def save_data_to_disk(self):
        """Guardar datos del nodo en disco para persistencia."""
        try:
            file_name = f"chord_node_{self.id}.json"
            with open(file_name, 'w') as f:
                json.dump(self.data, f)
            logger.info(f"Datos guardados en disco: {file_name}")
        except Exception as e:
            logger.error(f"Error al guardar datos en disco: {e}")

    def load_data_from_disk(self):
        """Cargar datos del nodo desde disco."""
        try:
            file_name = f"chord_node_{self.id}.json"
            if os.path.exists(file_name):
                with open(file_name, 'r') as f:
                    self.data = defaultdict(list, json.load(f))
                logger.info(f"Datos cargados desde disco: {file_name}")
            else:
                logger.info(f"No se encontró archivo local para nodo {self.id}. Iniciando vacío.")
        except Exception as e:
            logger.error(f"Error al cargar datos desde disco: {e}")

    # Method to find the closest preceding finger of a given id
    def closest_preceding_finger(self, id: int) -> 'ChordNodeReference':
        try:

            for i in range(self.m - 1, -1, -1):
                if self.finger[i] and self._inbetween(self.finger[i].id, self.id, id):
                    return self.finger[i]
            return self.ref
        except Exception as e:
            logger.error(f"{e}")        
        

    # Method to join a Chord network using 'node' as an entry point
    def join(self, node: 'ChordNodeReference'):
        """Join a Chord Network using 'node' as an entry point."""
        logger.debug("Estoy en el join")
        #with self.lock:
        try:
            if node:
                self.pred = None
                self.succ = node.find_successor(self.id)
                self.succ.notify(self.ref)
            else:
                self.succ = self.ref
                self.pred = None
            #logger.debug(f"Adyacentes de {self.ip}:{self.port} :: succ: {self.succ.ip} y pred: {self.pred.ip}" )    
        except Exception as e:
            logger.error(f"Error en el join: {e}")        


    def stabilize(self):
        """Verifica y ajusta sicesores/predecesores periodicamente."""
        while True:
            try:
                #with self.lock:
                if self.succ.id != self.id:
                    x = self.succ.pred
                    logger.debug(f"X es {x}")
                    if x and self._inbetween(x.id, self.id, self.succ.id):
                        self.succ = x
                    self.succ.notify(self.ref)
            except Exception as e:
                logger.error(f"Error in stabilize: {e}")
            logger.info(f"Stabilized: successor={self.succ}, predecessor={self.pred}")    

            time.sleep(10)

    # Notify method to inform the node about another node
    def notify(self, node: 'ChordNodeReference'):
        #with self.lock:
        if node.id!= self.id and (not self.pred or self._inbetween(node.id, self.pred.id, self.id)):
            self.pred = node

    def fix_fingers(self):
        """Actualiza periódicamente la tabla de dedos."""
        while True:
            try:
                #with self.lock:
                self.next = (self.next + 1) % self.m
                self.finger[self.next] = self.find_succ((self.id + 2 ** self.next) % 2 ** self.m)
            except Exception as e:
                logger.error(f"Error in fix_fingers: {e}")
            time.sleep(10)

    def check_successors(self):
        """Validar disponibilidad de sucesores y redistribuir datos si caen."""
        while True:
            try:
                if not self.is_node_alive(self.succ):
                    logger.warning(f"Sucesor {self.succ.id} no responde. Redistribuyendo datos...")
                    # Redistribuir claves del sucesor caído
                    if self.succ and self.succ.data:
                        for key, values in self.succ.data.items():
                            for value in values:
                                self.store_key(key, value)
                    # Asignar nuevo sucesor
                    self.succ = self.succ.succ if self.succ.succ else self.ref
                    logger.info(f"Nuevo sucesor asignado: {self.succ}.")
            except Exception as e:
                logger.error(f"Error en check_successors: {e}")
            time.sleep(15)

    
    

    def is_node_alive(self, node: 'ChordNodeReference') -> bool:
        """Verificar si un nodo está activo enviando una solicitud."""
        try:
            node.check_predecessor()  # Cualquier operación simple para comprobar vida
            return True
        except Exception:
            return False


    def check_predecessor(self):
        """Comprueba si el predecesor sigue activo."""
        while True:
            try:
                #with self.lock:
                if self.pred:
                    self.pred.check_predecessor()
            except Exception:
                self.pred = None
            time.sleep(10)

    # Store key method to store a key-value pair and replicate to the successor
    def store_key(self, key: str, value):
        #with self.lock: 
        try:
            logger.debug(f"Almacenando clave '{key}' con valor '{value}'...")   
            key_hash = getShaRepr(key)
            node = self.find_succ(key_hash)
            logger.debug(f"El sucesor de la llave es : {node}, la vou a mandar paya")
            node.store_key(key, value)
            logger.debug(f"Clave '{key}' almacenada en nodo {node.id}.")

            # Replicacion de la clave en el succesor y el sucesor del sucesor
            succesors = [node.succ, node.succ.succ]
            for succ in succesors:
                if succ and succ.id != node.id: # Validar que el succesor no sea el mismo
                    succ.store_key(key, value)
                    logger.debug(f"Clave {key} replicada en nodo sucesor {succ.id}")
            # if node.succ.id != node.id:
            #     node.succ.store_key(key,value)
            #     logger.debug(f"Clave '{key}' replicada en nodo sucesor {node.succ.id}.")
            # if node.succ.succ.id != node.id:
            #     node.succ.succ.store_key(key,value)    
            #     logger.debug(f"Clave '{key}' replicada en nodo sucesor del sucesor {node.succ.succ.id}.")
            
        except Exception as e:
            logger.error(f"Error al almacenar la clave '{key}': {e}")

    # Retrieve key method to get a value for a given key
    def retrieve_key(self, key: str) -> str:
        #with self.lock:
        try:
            logger.info(f"Recuperando clave *********************************************************8'{key}'...")    
            key_hash = getShaRepr(key)
            node = self.find_succ(key_hash)
            value = node.retrieve_key(key)
            if value:
                logger.info(f"Clave {key} encontrada con valor {value} en nodo {node.id}.")
            else:
                logger.warning(f"Clave {key} no encontrada.")
            return value
        except Exception as e:
            logger.error(f"Error al recuperar la clave '{key}': {e}")
            return None
        
    # Start server method to handle incoming requests
    def start_server(self):
        logger.info(f"Iniciando servidor CHORD en {self.ip}:{self.port}...")
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            s.bind((self.ip, self.port))
            s.listen(100)
            logger.info("Servidor iniciado y esperando conexiones...")

            while True:
                try:
                    conn, addr = s.accept()
                    logger.debug(f"Nueva conexión aceptada desde {addr}")
                    threading.Thread(target=self.handle_connection, args=(conn, addr), daemon=True).start()
                except Exception as e:
                    logger.error(f"Error acepting new connextion: {e}")    
           
    def handle_connection(self, conn, addr):
            try:
                data = conn.recv(1024).decode().split(',')
                logger.debug(f"Datos recibidos de {addr}: {data}")
                option = int(data[0])
                response = None

                if option == FIND_SUCCESSOR:
                    id = int(data[1])
                    response = self.find_succ(id)
                    logger.info(f"Successor de ID={id} encontrado: {response}.")
                elif option == FIND_PREDECESSOR:
                    id = int(data[1])
                    response = self.find_pred(id)
                    logger.info(f"Predecessor de ID={id} encontrado: {response}.")
                elif option == GET_SUCCESSOR:
                    response = self.succ if self.succ else self.ref
                elif option == GET_PREDECESSOR:
                    response = self.pred if self.pred else self.ref
                elif option == NOTIFY:
                    id = int(data[1])
                    ip = data[2]
                    self.notify(ChordNodeReference(ip, self.port))
                    logger.info(f"Nodo notificado: ID={id}, IP={ip}.")
                elif option == STORE_KEY:
                    key, value = data[1], data[2]
                    self.data.setdefault(key, [])
                    if not value in self.data[key]:
                        self.data[key].append(value) 
                    logger.info(f"Clave '{key}' con valor '{value}' almacenada localmente.")
                elif option == RETRIEVE_KEY:
                    key = data[1]
                    response = self.data.get(key, '')
                    logger.info(f"Clave '{key}' recuperada con valor '{response}'.")

                if response:
                    conn.sendall(str(response).encode())
            except Exception as e:
                logger.error(f"Error handling connection from {addr}: {e}")
            finally:
                conn.close()