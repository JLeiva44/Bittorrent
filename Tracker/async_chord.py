import asyncio
import socket
from collections import defaultdict
import hashlib
from tracker_logger import logger
# Operación de códigos
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
    """Función para obtener el valor hash de una cadena usando SHA-1"""
    return int(hashlib.sha1(data.encode()).hexdigest(), 16)

class ChordNodeReference:
    """Referencia a un nodo Chord"""
    def __init__(self, ip: str, port: int = 8001):
        self.id = getShaRepr(ip)
        self.ip = ip
        self.port = port

    async def _send_data(self, op: int, data: str = None, retries: int = 3) -> bytes:
        """Envía datos a otro nodo con manejo de reintentos (versión asincrónica)"""
        for _ in range(retries):
            try:
                reader, writer = await asyncio.open_connection(self.ip, self.port)
                message = f'{op},{data}' if data else f'{op}'
                writer.write(message.encode('utf-8'))
                await writer.drain()
                data = await reader.read(1024)
                writer.close()
                await writer.wait_closed()
                return data
            except asyncio.TimeoutError as e:
                logger.warning(f"Timeout al enviar datos a {self.ip}:{self.port}: {e}")
            except Exception as e:
                logger.warning(f"Error al enviar datos a {self.ip}:{self.port}: {e}")
            await asyncio.sleep(1)  # Espera antes de reintentar
        raise Exception(f"No se pudo contactar con el nodo {self.ip}:{self.port}.")

    async def find_successor(self, id: int) -> 'ChordNodeReference':
        """Encuentra el sucesor de un id dado de manera asincrónica"""
        response = await self._send_data(FIND_SUCCESSOR, str(id))
        response = response.decode().split(',')
        return ChordNodeReference(response[1], self.port)

    async def find_predecessor(self, id: int) -> 'ChordNodeReference':
        """Encuentra el predecesor de un id dado de manera asincrónica"""
        response = await self._send_data(FIND_PREDECESSOR, str(id))
        response = response.decode().split(',')
        return ChordNodeReference(response[1], self.port)

    @property
    async def succ(self) -> 'ChordNodeReference':
        """Obtiene el sucesor de manera asincrónica"""
        response = await self._send_data(GET_SUCCESSOR)
        response = response.decode().split(',')
        return ChordNodeReference(response[1], self.port)

    @property
    async def pred(self) -> 'ChordNodeReference':
        """Obtiene el predecesor de manera asincrónica"""
        response = await self._send_data(GET_PREDECESSOR)
        response = response.decode().split(',')
        return ChordNodeReference(response[1], self.port)

    async def notify(self, node: 'ChordNodeReference'):
        """Notifica a otro nodo de manera asincrónica"""
        await self._send_data(NOTIFY, f'{node.id},{node.ip}')

    async def check_predecessor(self):
        """Verifica si el predecesor sigue activo (versión asincrónica)"""
        await self._send_data(CHECK_PREDECESSOR)

    async def closest_preceding_finger(self, id: int) -> 'ChordNodeReference':
        """Encuentra el dedo precededor más cercano de manera asincrónica"""
        response = await self._send_data(CLOSEST_PRECEDING_FINGER, str(id))
        response = response.decode().split(',')
        return ChordNodeReference(response[1], self.port)

    async def store_key(self, key: str, value: str):
        """Almacena una clave-valor en el nodo (versión asincrónica)"""
        await self._send_data(STORE_KEY, f'{key},{value}')

    async def retrieve_key(self, key: str) -> str:
        """Recupera el valor de una clave en el nodo (versión asincrónica)"""
        response = await self._send_data(RETRIEVE_KEY, key)
        return response.decode() if response != b"[]" else []

class ChordNode:
    """Clase que representa un nodo Chord"""
    def __init__(self, ip: str, port: int = 8001, m: int = 160):
        self.id = getShaRepr(ip)
        self.ip = ip
        self.port = port
        self.ref = ChordNodeReference(self.ip, self.port)
        self.succ = self.ref  # El sucesor inicial es el mismo nodo
        self.pred = None  # Inicialmente no hay predecesor
        self.m = m  # Número de bits en el espacio de claves
        self.finger = [self.ref] * self.m  # Tabla de dedos
        self.next = 0  # Índice de la siguiente posición para fijar en la tabla de dedos
        self.data = defaultdict(list)  # Diccionario para almacenar pares clave-valor
        self.lock = asyncio.Lock()  # Lock asincrónico para proteger recursos compartidos

    async def _inbetween(self, k: int, start: int, end: int) -> bool:
        '''Ayudante para verificar si un valor está en el rango (start, end]'''
        if start < end:
            return start < k <= end
        else:  # El intervalo se envuelve alrededor de 0
            return start < k or k <= end

    async def find_succ(self, id: int) -> 'ChordNodeReference':
        '''Encuentra el sucesor de un id dado (versión asincrónica)'''
        node = await self.find_pred(id)  # Encuentra el predecesor del id
        return node.succ  # Devuelve el sucesor de ese nodo

    async def find_pred(self, id: int) -> 'ChordNodeReference':
        """Encuentra el predecesor de un id dado"""
        node = self
        while not await self._inbetween(id, node.id, node.succ.id):
            node = await self.closest_preceding_finger(id)
        return node

    async def closest_preceding_finger(self, id: int) -> 'ChordNodeReference':
        """Encuentra el dedo precededor más cercano (versión asincrónica)"""
        for i in range(self.m - 1, -1, -1):
            if self.finger[i] and await self._inbetween(self.finger[i].id, self.id, id):
                return self.finger[i]
        return self.ref

    async def join(self, node: 'ChordNodeReference'):
        """Unirse a un anillo Chord existente (versión asincrónica)"""
        async with self.lock:
            if node:
                self.pred = None
                self.succ = await node.find_successor(self.id)
                await self.succ.notify(self.ref)
            else:
                self.succ = self.ref
                self.pred = None

    async def leave(self):
        """Salir del anillo Chord (versión asincrónica)"""
        async with self.lock:
            if self.succ and self.pred:
                self.pred.succ = self.succ
                self.succ.pred = self.pred

    async def stabilize(self):
        """Estabiliza el nodo y ajusta sucesores/predecesores periódicamente"""
        while True:
            try:
                async with self.lock:
                    if self.succ.id != self.id:
                        x = self.succ.pred
                        if x and await self._inbetween(x.id, self.id, self.succ.id):
                            self.succ = x
                        await self.succ.notify(self.ref)
            except Exception as e:
                logger.error(f"Error al estabilizar: {e}")
            await asyncio.sleep(10)

    async def notify(self, node: 'ChordNodeReference'):
        """Notifica al nodo sobre otro nodo (versión asincrónica)"""
        async with self.lock:
            if node.id != self.id and (not self.pred or await self._inbetween(node.id, self.pred.id, self.id)):
                self.pred = node
