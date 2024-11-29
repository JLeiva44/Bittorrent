import zmq
import threading
import hashlib
import time
import logging

# Configuración del logger
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger("__main__")

# Códigos de operación
FIND_SUCCESSOR = 1
FIND_PREDECESSOR = 2
GET_SUCCESSOR = 3
GET_PREDECESSOR = 4
NOTIFY = 5
CHECK_PREDECESSOR = 6
CLOSEST_PRECEDING_FINGER = 7

def getShaRepr(data: str) -> int:
    return int(hashlib.sha1(data.encode()).hexdigest(), 16)

class ChordNodeReference:
    def __init__(self, id: int, ip: str, port: int):
        self.id = getShaRepr(id)
        self.ip = ip
        self.port = port

    def _send_data(self, context: zmq.Context, op: int, data: str = None) -> bytes:
        try:
            with context.socket(zmq.REQ) as s:
                s.connect(f'tcp://{self.ip}:{self.port}')
                s.send_json({'op': op, 'data': data})
                return s.recv_json()
        except Exception as e:
            logger.error(f"Error sending data: {e}")
            return None

    def find_successor(self, id: int, context: zmq.Context) -> 'ChordNodeReference':
        response = self._send_data(context, FIND_SUCCESSOR, str(id))
        if response:
            return ChordNodeReference(int(response['id']), response['ip'], self.port)
        return None

    def find_predecessor(self, id: int, context: zmq.Context) -> 'ChordNodeReference':
        response = self._send_data(context, FIND_PREDECESSOR, str(id))
        if response:
            return ChordNodeReference(int(response['id']), response['ip'], self.port)
        return None

    @property
    def succ(self) -> 'ChordNodeReference':
        response = self._send_data(context=None, op=GET_SUCCESSOR)
        if response:
            return ChordNodeReference(int(response['id']), response['ip'], self.port)
        return None

    @property
    def pred(self) -> 'ChordNodeReference':
        response = self._send_data(context=None, op=GET_PREDECESSOR)
        if response:
            return ChordNodeReference(int(response['id']), response['ip'], self.port)
        return None

    def notify(self, node: 'ChordNodeReference', context: zmq.Context):
        self._send_data(context, NOTIFY, f'{node.id},{node.ip}')

class ChordNode:
    def __init__(self, id: int, ip: str, port: int = 8001):
        self.id = getShaRepr(id)
        self.ip = ip
        self.port = port
        self.ref = ChordNodeReference(self.id, self.ip, self.port)
        self.succ = self.ref  # Inicialmente el sucesor es sí mismo
        self.pred = None      # Inicialmente no hay predecesor

        # Iniciar el servidor en un hilo separado
        threading.Thread(target=self.start_server, daemon=True).start()

    def start_server(self):
        context = zmq.Context()
        server_socket = context.socket(zmq.REP)
        server_socket.bind(f'tcp://{self.ip}:{self.port}')
        
        logger.debug(f"Servidor de Chord escuchando en tcp://{self.ip}:{self.port}")
        
        while True:
            try:
                message = server_socket.recv_json()
                op_code = message.get('op')
                data = message.get('data')

                if op_code == FIND_SUCCESSOR:
                    id_to_find = int(data)
                    successor_node = self.find_successor(id_to_find)
                    server_socket.send_json({'id': successor_node.id, 'ip': successor_node.ip})

                elif op_code == FIND_PREDECESSOR:
                    id_to_find = int(data)
                    predecessor_node = self.find_predecessor(id_to_find)
                    server_socket.send_json({'id': predecessor_node.id, 'ip': predecessor_node.ip})

                elif op_code == GET_SUCCESSOR:
                    server_socket.send_json({'id': self.succ.id, 'ip': self.succ.ip})

                elif op_code == GET_PREDECESSOR:
                    if self.pred is not None:
                        server_socket.send_json({'id': self.pred.id, 'ip': self.pred.ip})
                    else:
                        server_socket.send_json({'id': None})

                elif op_code == NOTIFY:
                    node_info = data.split(',')
                    new_pred_id = int(node_info[0])
                    new_pred_ip = node_info[1]
                    if not self.pred or (new_pred_id > self.pred.id and new_pred_id < self.id):
                        self.pred = ChordNodeReference(new_pred_id, new_pred_ip)

            except Exception as e:
                logger.error(f"Error in server loop: {e}")

    def find_successor(self, id_to_find: int) -> 'ChordNodeReference':
        # Lógica para encontrar el sucesor (implementa según tus necesidades)
        return self.ref  # Retorna a sí mismo por ahora

    def find_predecessor(self, id_to_find: int) -> 'ChordNodeReference':
        # Lógica para encontrar el predecesor (implementa según tus necesidades)
        return self.ref  # Retorna a sí mismo por ahora

# Ejemplo de uso
if __name__ == "__main__":
    node1 = ChordNode("127.0.0.1", 8000)
    node2 = ChordNode("127.0.0.1", 8001)
    node3 = ChordNode("127.0.0.1", 8002)

    while True:
        time.sleep(1)  # Mantiene el programa en ejecución para probar los servidores
