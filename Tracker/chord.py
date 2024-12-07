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


def getShaRepr(data: str, m: int = 160):
    """
    Genera el hash de una cadena utilizando SHA-1 y lo ajusta al espacio de 2^m.
    
    Args:
        data (str): Cadena a hashear.
        m (int): Tamaño del anillo Chord (en bits).
    
    Returns:
        int: Representación entera del hash dentro del espacio [0, 2^m - 1].
    """
    sha1_hash = int(hashlib.sha1(data.encode()).hexdigest(), 16)
    max_value = 2 ** m  # Tamaño del anillo
    return sha1_hash % max_value

class ChordNodeReference:
    """
    Class to reference a Chord node
    """
    def __init__(self, ip: str, port: int = 8001):
        # Validación de entrada
        if not ip or not isinstance(ip, str):
            raise ValueError("IP inválida proporcionada.")
        if not (1024 <= port <= 65535):
            raise ValueError("El puerto debe estar entre 1024 y 65535.")
        
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
    
    
           
    
    # def find_successor(self, id: int) -> 'ChordNodeReference':
    #     """Method to find the successor of a given id"""
    #     response = self._send_data(FIND_SUCCESSOR, str(id)).decode().split(',')
    #     return ChordNodeReference(response[1], self.port)
    
    def find_successor(self, id: int) -> 'ChordNodeReference':
        """
        Encuentra el sucesor de un ID.
        """
        try:
            response = self._send_data(FIND_SUCCESSOR, str(id)).decode().split(',')
            if len(response) < 2:
                raise ValueError(f"Respuesta inválida recibida al buscar sucesor: {response}")
            return ChordNodeReference(response[1], self.port)
        except Exception as e:
            logger.error(f"Error en find_successor para ID={id}: {e}")
            raise

    
    def find_predecessor(self, id: int) -> 'ChordNodeReference':
        """
        Encuentra el predecesor de un ID.
        """
        try:
            response = self._send_data(FIND_PREDECESSOR, str(id)).decode().split(',')
            if len(response) < 2:
                raise ValueError(f"Respuesta inválida recibida al buscar predecesor: {response}")
            return ChordNodeReference(response[1], self.port)
        except Exception as e:
            logger.error(f"Error en find_predecessor para ID={id}: {e}")
            raise

    def succ(self) -> 'ChordNodeReference':
        """
        Obtiene el sucesor del nodo actual.
        """
        try:
            response = self._send_data(GET_SUCCESSOR).decode().split(',')
            if len(response) < 2:
                raise ValueError(f"Respuesta inválida al obtener sucesor: {response}")
            return ChordNodeReference(response[1], self.port)
        except Exception as e:
            logger.error(f"Error al obtener sucesor: {e}")
            return None  # Retornar None si no se puede obtener
        
    @property
    def pred(self) -> 'ChordNodeReference':
        """
        Obtiene el predecesor del nodo actual.
        """
        try:
            response = self._send_data(GET_PREDECESSOR).decode().split(',')
            if len(response) < 2:
                raise ValueError(f"Respuesta inválida al obtener predecesor: {response}")
            return ChordNodeReference(response[1], self.port)
        except Exception as e:
            logger.error(f"Error al obtener predecesor: {e}")
            return None    
        
    def notify(self, node: 'ChordNodeReference'):
        """
        Notifica al nodo actual sobre otro nodo.
        """
        try:
            if not node:
                raise ValueError("Nodo para notificar no puede ser None.")
            self._send_data(NOTIFY, f"{node.id},{node.ip}")
            logger.debug(f"Nodo notificado exitosamente: {node}")
        except Exception as e:
            logger.error(f"Error notificando nodo {node}: {e}")    
        
    def check_predecessor(self):
        """
        Verifica si el predecesor está activo.
        """
        try:
            self._send_data(CHECK_PREDECESSOR)
        except Exception as e:
            logger.warning(f"Error verificando predecesor: {e}")

    def closest_preceding_finger(self, id: int) -> 'ChordNodeReference':
        """
        Encuentra el dedo más cercano precediendo al ID dado.
        """
        try:
            response = self._send_data(CLOSEST_PRECEDING_FINGER, str(id)).decode().split(',')
            if len(response) < 2:
                raise ValueError(f"Respuesta inválida para closest_preceding_finger: {response}")
            return ChordNodeReference(response[1], self.port)
        except Exception as e:
            logger.error(f"Error en closest_preceding_finger para ID={id}: {e}")
            raise        

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
        
        # Cargar datos desde disco
        self.load_data_from_disk()

        self._strat_background_tasks()


        logger.debug(f"Inicializando Nodo Chord con ID={self.id} en {self.ip}:{self.port}")

    def _strat_background_tasks(self):
        """Inicia las tareas de fondo para estabilizar el nodo u manejar datos"""
        tasks = [
            threading.Thread(target=self.stabilize, daemon=True),
            threading.Thread(target=self.fix_fingers, daemon=True),
            threading.Thread(target=self.check_predecessor, daemon=True),
            threading.Thread(target=self.start_server, daemon=True),
            threading.Thread(target=self.show_my_data, daemon=True),
            threading.Thread(target=self.auto_save_data, daemon=True)
        ]
        for task in tasks:
            task.start()

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
        try:
            node = self.find_pred(id)  # Find predecessor of id
            return node.succ if node and node.succ else self.ref  # Return successor of that node
        except Exception as e:
            logger.error(f"Error en find_sicc para ID={id}:{e}")
            return self.ref

    def find_pred(self, id: int) -> 'ChordNodeReference':
        """Encuentra el predecesor de un ID."""
        try:
            node = self
            while not self._inbetween(id, node.id, node.succ.id):
                next_node = node.closest_preceding_finger(id)
                if next_node == node:  # Evitar ciclos infinitos
                    break
                node = next_node
            return node
        except Exception as e:
            logger.error(f"Error en find_pred para ID={id}: {e}")
            return self
    
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
                #self.pred = None
                self.succ = node.find_successor(self.id)
                logger.debug(f"Antes de notify a mi nuevo succesrr")
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
                if self.id == self.succ.id:  # Soy único o el mayor
                    logger.debug("Soy el primerop y me voy a estabilizar")
                    try:
                        if self.pred:  # Hay otros nodos en el anillo
                            first = self.pred
                            logger.debug(f"Mi predecesor es {first.pred}")

                            # Limitar iteraciones para evitar ciclos infinitos
                            max_iterations = 2 ** self.m
                            iteration_count = 0
                            last_seen = first.id

                            while first.pred and last_seen != first.pred.id and iteration_count < max_iterations:
                                first = first.pred
                                logger.debug(f"el otro es {first}")
                                iteration_count += 1

                            # Verificar que el nodo menor es alcanzable antes de unirme
                            if first and self.is_node_alive(first):
                                logger.debug(f"El nodo menor encontrado es {first}. Intentando unirme...")
                                self.join(first)
                            else:
                                logger.error(f"El nodo menor no es válido o no está accesible desde {self.id}.")
                    except Exception as e:
                        logger.error(f"Error al manejar nodo mayor: {e}")
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
        """Valida disponibilidad de sucesores y redistribuye claves si caen."""
        while True:
            try:
                if not self.is_node_alive(self.succ):
                    logger.warning(f"Sucesor {self.succ.id} no responde. Redistribuyendo claves...")
                    self._redistribute_data(self.succ)
                    self.succ = self.succ.succ if self.succ.succ else self.ref
                    logger.info(f"Nuevo sucesor asignado: {self.succ.id}.")
            except Exception as e:
                logger.error(f"Error en check_successors: {e}")
            time.sleep(15)

    def _redistribute_data(self, failed_node: 'ChordNodeReference'):
        """Redistribuye los datos de un nodo caído."""
        try:
            if failed_node and failed_node.data:
                for key, values in failed_node.data.items():
                    for value in values:
                        self.store_key(key, value)
                logger.info(f"Datos redistribuidos del nodo caído {failed_node.id}.")
        except Exception as e:
            logger.error(f"Error al redistribuir datos de nodo {failed_node.id}: {e}")

    def check_predecessor(self):
        """Comprueba si el predecesor sigue activo."""
        while True:
            try:
                #with self.lock:
                if self.pred and not self.is_node_alive(self.pred):
                    logger.warning(f"Predecesor {self.pred.id} no responde. Eliminando referencia.")
                    self.pred = None
            except Exception as e:
                logger.error(f"Error en check_predecessor: {e}")
            time.sleep(10)        

    def is_node_alive(self, node: 'ChordNodeReference') -> bool:
        """Verificar si un nodo está activo enviando una solicitud."""
        try:
            node.check_predecessor()  # Cualquier operación simple para comprobar vida
            return True
        except Exception:
            return False


    
    def store_key(self, key: str, value):
        """Almacena una clave en el nodo adecuado y realiza replicación."""
        #with self.lock:  # Proteger acceso concurrente
        try:
            key_hash = getShaRepr(key)
            node = self.find_succ(key_hash)

            if node.id == self.id:
                # Almacenar localmente
                if value not in self.data[key]:
                    self.data[key].append(value)
                logger.info(f"Clave '{key}' almacenada localmente en nodo {self.id}.")
            else:
                # Solicitar al nodo sucesor almacenar la clave
                logger.debug(f"Redirigiendo clave '{key}' a nodo {node.id}.")
                node.store_key(key, value)

            # Replicación a sucesores inmediatos
            self._replicate_key_to_successors(key, value, node)
        except Exception as e:
            logger.error(f"Error al almacenar la clave '{key}': {e}")       

    def _replicate_key_to_successors(self, key: str, value, origin_node: 'ChordNodeReference'):
        """Replica la clave a los sucesores inmediatos del nodo."""
        try:
            successors = [origin_node.succ, origin_node.succ.succ]
            for succ in successors:
                if succ and succ.id != origin_node.id:
                    try:
                        succ.store_key(key, value)
                        logger.debug(f"Clave '{key}' replicada en nodo sucesor {succ.id}.")
                    except Exception:
                        logger.warning(f"No se pudo replicar la clave '{key}' en nodo {succ.id}.")
        except Exception as e:             
            logger.error(f"Error durante la replicación de la clave '{key}': {e}")
    
    
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

                elif option == CLOSEST_PRECEDING_FINGER:
                    id = int(data[1])
                    response = str(self.closest_preceding_finger(id))
                    logger.info(f"Closest preceding finger para ID={id}: {response}.")
                
                elif option == CHECK_PREDECESSOR:
                    response = "ALIVE"
                if response:
                    conn.sendall(str(response).encode())
            except Exception as e:
                logger.error(f"Error handling connection from {addr}: {e}")
            finally:
                conn.close()