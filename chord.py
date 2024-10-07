
import socket
import threading
import sys
import time

# Operation Codes
FIND_SUCCESSOR = 1
FIND_PREDECESSOR = 2
GET_SUCCESSOR = 3
GET_PREDECESSOR = 4
NOTIFY = 5
INSERT_NODE = 6
REMOVE_NODE = 7

class ChordNodeReference:
    def __init__(self, id: int, ip: str, port: int = 8001):
        self.id = id
        self.ip = ip
        self.port = port

    def _send_data(self, op: int, data: str = None) -> bytes:
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.connect((self.ip, self.port))
                s.sendall(f'{op},{data}'.encode('utf-8'))
                return s.recv(1024)
        except Exception as e:
            print(f"Error sending data: {e}")
            return b''

    def find_succ(self, id: int) -> 'ChordNodeReference':
        response = self._send_data(FIND_SUCCESSOR, str(id)).decode().split(',')
        return ChordNodeReference(int(response[0]), response[1], self.port)

    def find_pred(self, id: int) -> 'ChordNodeReference':
        response = self._send_data(FIND_PREDECESSOR, str(id)).decode().split(',')
        return ChordNodeReference(int(response[0]), response[1], self.port)

    @property
    def successor(self) -> 'ChordNodeReference':
        response = self._send_data(GET_SUCCESSOR).decode().split(',')
        print(response)
        return ChordNodeReference(int(response[0]), response[1], self.port)

    @property
    def predecessor(self) -> 'ChordNodeReference':
        response = self._send_data(GET_PREDECESSOR).decode().split(',')
        return ChordNodeReference(int(response[0]), response[1], self.port)

    def notify(self, id: int) -> 'ChordNodeReference':
        self._send_data(NOTIFY, str(id))

    def __str__(self) -> str:
        return f'{self.id},{self.ip},{self.port}'

    def __repr__(self) -> str:
        return str(self)
    

class ChordNode:
    def __init__(self, id: int, ip: str, port: int = 8001, m: int = 8):
        self.id = id
        self.ip = ip
        self.port = port
        self.ref = ChordNodeReference(self.id, self.ip, self.port)
        self.succ = None
        self.pred = None
        self.m = m
        threading.Thread(target=self.stabilize, daemon=True).start()
        threading.Thread(target=self.start_server, daemon=True).start()

    def find_succ(self, id: int) -> 'ChordNodeReference':
        node = self.find_pred(id)
        if node.id == self.id:
            return self.ref
        return node.successor

    def find_pred(self, id: int) -> 'ChordNodeReference':
        if not self.succ or self.succ.id == self.id:
            return self.ref
        if id >= self.id and ( id < self.succ.id or self.succ.id < self.id ):
            return self.ref
        return self.succ.find_pred(id)

    def join(self, node: 'ChordNodeReference'):
        """Join a Chord network using 'node' as an entry point."""
        self.pred = None
        self.succ = node.find_succ(self.id)
        if self.succ:
            self.succ.notify(self.id)

    def stabilize(self):
        """Regular check for correct Chord structure."""
        while True:
            if self.succ:
                x = self.succ.predecessor
                if x.id != self.id:
                    self.succ = x
                self.succ.notify(self.id)
            if not self.succ and self.pred:
                self.succ = self.pred
            print(f"successor : {self.succ} predecessor {self.pred}")
            time.sleep(10)
            

    def notify(self, node: 'ChordNodeReference'):
        # """Exterior call to stabilize network."""
        # ## Hint: Missing extra condition
        # if not self.pred:
        #     self.pred = node

        """Exterior call to stabilize network."""
        # Si no hay predecesor, simplemente lo establece
        if not self.pred:
            self.pred = node
        else:
            # Verificar si el nodo que notifica debe ser el nuevo predecesor
            if (self.pred.id < node.id < self.id) or (self.pred.id > self.id and (node.id < self.id or node.id > self.pred.id)):
                self.pred = node

    def start_server(self):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            print(self.ip, self.port)
            s.bind((self.ip, self.port))
            s.listen(10)

            while True:
                conn, addr = s.accept()
                print(f'new connection from {addr}' )
                data = conn.recv(1024).decode().split(',')

                data_resp = None
                option = int(data[0])

                if option == FIND_SUCCESSOR:
                    id = int(data[1])
                    data_resp = self.find_succ(id)
                elif option == FIND_PREDECESSOR:
                    id = int(data[1])
                    data_resp = self.find_pred(id)
                elif option == GET_SUCCESSOR:
                    data_resp = self.succ if self.succ else self.ref
                elif option == GET_PREDECESSOR:
                    data_resp = self.pred if self.pred else self.ref
                elif option == NOTIFY:
                    id = int(data[1])
                    self.notify(ChordNodeReference(id, addr[0], self.port))
                elif option == INSERT_NODE:
                    id = int(data[1])
                    ip = data[2]
                    self.insert_node(ChordNodeReference(id, ip, self.port))
                elif option == REMOVE_NODE:
                    id = int(data[1])
                    self.remove_node(id)

                if data_resp:
                    response = f'{data_resp.id},{data_resp.ip}'.encode()
                    conn.sendall(response)
                conn.close()

