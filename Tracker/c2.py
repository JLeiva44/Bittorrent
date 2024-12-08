import random
import socket
import threading
import time
import hashlib
import logging

logger = logging.getLogger("__main__")

# Operation codes
FIND_SUCCESSOR = 1
FIND_PREDECESSOR = 2
GET_SUCCESSOR = 3
GET_PREDECESSOR = 4
NOTIFY = 5

CLOSEST_PRECEDING_FINGER = 7
GET_VALUE = 8
GET_KEYS = 9
STORE_KEY = 10
UPDATE_KEY = 11
DELETE_KEY = 12
GET_REPLICATE = 13
STORE_REPLICATE = 14
UPDATE_REPLICATE = 15
DELETE_REPLICATE = 16
CHECK_CONN = 17
GET_MY_VALUES = 18
CLEAN_REPLICATES = 19

# TODO Remember the bug when a node left the ring


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
    def __init__(self, id: int, ip: str, port: int = 8001):
        self.id = getShaRepr(ip)
        self.ip = ip
        self.port = port

    def _send_data(self, op: int, data: str = None) -> bytes:
        logger.debug(
            f"Trying to send data: {data} with op: {op} to {self.ip}:{self.port}"
        )
        logger.debug(f"Send data {self.ip} with op -> {op}")
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(5)
                s.connect((self.ip, self.port))
                s.sendall(f"{op},{data}".encode("utf-8"))
                logger.debug(f"Data sent succesfuly to {self.ip}:{self.port}")
                response = s.recv(4096)
                logger.debug(f"Response -> {response} from {self.ip} with op {op}")
                if response == b"connection_refused":
                    raise ConnectionRefusedError(
                        "Connection refused in send_data -> start_server"
                    )
                return response
        # except socket.error as e:
        #     if e.errno == 104:
        #         raise ConnectionRefusedError("Socket reset conn"
        except ConnectionRefusedError as e:
            logger.debug(f"Connection refused in _send_data to {self.ip} with op: {op}")
            logger.debug(f"Connection refused in _send_data to {self.ip} with op: {op}")
            raise
        except socket.error as e:
            raise ConnectionRefusedError(
                f"Unable to reach the host {self.ip}:{self.port}"
            )
        except socket.timeout:
            logger.debug(f"Timeout while trying to send data to {self.ip}:{self.port}")
            raise ConnectionRefusedError(
                "Timeout while trying to send data to {self.ip}:{self.port}"
            )
        except Exception as e:
            logger.debug(f"Error sending data: {e}")
            logger.debug(f"Error sending data: {e}")
            return b""

    def check_conn(self):
        self._send_data(CHECK_CONN)

    def update_reference(self, node: "ChordNodeReference"):
        self.id = node.id
        self.ip = node.ip
        self.port = node.port

    def find_successor(self, id: int) -> "ChordNodeReference":
        response = self._send_data(FIND_SUCCESSOR, str(id)).decode().split(",")
        return ChordNodeReference(int(response[0]), response[1], self.port)

    def find_predecessor(self, id: int) -> "ChordNodeReference":
        response = self._send_data(FIND_PREDECESSOR, str(id)).decode().split(",")
        return ChordNodeReference(int(response[0]), response[1], self.port)

    @property
    def succ(self) -> "ChordNodeReference":
        response = self._send_data(GET_SUCCESSOR).decode().split(",")
        return ChordNodeReference(int(response[0]), response[1], self.port)

    @property
    def pred(self) -> "ChordNodeReference":
        response = self._send_data(GET_PREDECESSOR).decode().split(",")
        return ChordNodeReference(int(response[0]), response[1], self.port)

    def notify(self, node: "ChordNodeReference"):
        self._send_data(NOTIFY, f"{node.id},{node.ip}")

    def closest_preceding_finger(self, id: int) -> "ChordNodeReference":
        response = (
            self._send_data(CLOSEST_PRECEDING_FINGER, str(id)).decode().split(",")
        )
        return ChordNodeReference(int(response[0]), response[1], self.port)

    def get_value(self, key: int) -> dict:
        response = self._send_data(GET_VALUE, str(key)).decode()
        return eval(response) if response != "[]" else []

    def get_keys(self) -> list:
        response = self._send_data(GET_KEYS).decode()
        return eval(response) if response != "" else []

    def store_key(self, key: int, value: str, is_replicate=False):
        (
            self._send_data(STORE_REPLICATE, f"{key},{value}")
            if is_replicate
            else self._send_data(STORE_KEY, f"{key},{value}")
        )

    def update_key(self, key: int, value: str):
        self._send_data(UPDATE_KEY, f"{key},{value}")

    def delete_key(self, key: int):
        self._send_data(DELETE_KEY, str(key))

    def get_replicate(self, key: int):
        response = self._send_data(GET_REPLICATE, f"{key}").decode()
        return eval(response) if response != "[]" else []

    def update_replicate(self, key: int, value: str):
        self._send_data(UPDATE_REPLICATE, f"{key},{value}")

    def delete_replicate(self, key: int):
        self._send_data(DELETE_REPLICATE, f"{key}")

    def get_my_values(self, key):
        response = self._send_data(GET_MY_VALUES, f"{key}").decode()
        logger.debug(f"Get My values: {response}... and type is {type(response)}")
        return eval(response) if response != "[]" and response != "" else []

    def clean_replicates(self):
        self._send_data(CLEAN_REPLICATES)

    def __str__(self) -> str:
        return f"{self.id},{self.ip},{self.port}"

    def __repr__(self) -> str:
        return str(self)


class ChordNode:
    def __init__(self, ip: str, port: int = 8001, m: int = 160, values={}):

        self.id = getShaRepr(ip)
        self.ip = ip
        self.port = port
        self.ref = ChordNodeReference(self.id, self.ip, self.port)
        self.succ = ChordNodeReference(
            self.id, self.ip, self.port
        )  # Initial successor is itself
        self.pred = None  # Initially no predecessor
        self.m = m  # Number of bits in the hash/key space
        self.finger = [self.ref] * self.m  # Finger table
        self.next = 0  # Finger table index to fix next
        self.succ_list = []  # List of successors
        self.values: dict = values  # Value stored in this node
        self.replicates = {}
        self.is_stabilizing = False

        logger.debug(f"Fixing fingers")
        threading.Thread(
            target=self.fix_fingers, daemon=True
        ).start()  # Start fix fingers threa

        logger.debug(f"Checking predecessor")
        threading.Thread(
            target=self.check_predecessor, daemon=True
        ).start()  # Start check predecessor thread

        logger.debug(f"Initializing server.")
        threading.Thread(
            target=self.start_server, daemon=True
        ).start()  # Start server thread

        logger.debug(f"Stabilize ring")
        threading.Thread(
            target=self.stabilize, daemon=True
        ).start()  # Start stabilize thread

        threading.Thread(
            target=self.show_my_data, daemon=True
        ).start()  # Start stabilize thread


    def show_my_data(self):
        while True:
            try:
                print("--------Mostrando mis datos-------")
                for key in self.values:
                    print(f"{key}:{self.values[key]}")
                print("-----------------------------------")
                print("--------Mostrando replicados------")
                for key in self.replicates:
                    print(f"{key}:{self.replicates[key]}")
                print("-----------------------------------")
            except Exception as e:
                print(f"Error en show_my_data: {e}")    
            time.sleep(6)    
    
    def _inbetween(self, k: int, start: int, end: int) -> bool:
        """Check if k is in the interval (start, end]."""
        if start < end:
            return start < k <= end
        else:  # The interval wraps around 0
            return start < k or k <= end

    def find_succ(self, id: int) -> "ChordNodeReference":
        node = self.find_pred(id)  # Find predecessor of id
        return node.succ  # Return successor of that node

    def find_pred(self, id: int) -> "ChordNodeReference":
        node = self
        while not self._inbetween(id, node.id, node.succ.id):
            cpf = node.closest_preceding_finger(id)
            if cpf.id == node.id:
                break
            else:
                node = cpf
        return node

    def closest_preceding_finger(self, id: int) -> "ChordNodeReference":
        for i in range(self.m - 1, -1, -1):
            if self.finger[i] and self._inbetween(self.finger[i].id, self.id, id):
                return self.finger[i]
        return self.ref

    def join(self, node: "ChordNodeReference"):
        """Join a Chord network using 'node' as an entry point."""
        if node:
            logger.debug(f"Joining to my succ -> {node}")
            succ = node.find_successor(self.id)
            if succ.ip != self.ip:
                self.change_succ(succ)

    def stabilize(self):
        """Regular check for correct Chord structure."""
        while True:
            # logger.debug('Estabilizing')
            try:
                self.is_stabilizing = True
                # self.succ.check_conn()
                x = self.succ.pred
                if x.id != self.id:
                    if x and self._inbetween(x.id, self.id, self.succ.id):
                        self.change_succ(x)
                else:
                    for key in list(self.values.keys()):
                        self.replicate(key, self.values[key])

            except ConnectionRefusedError as e:
                logger.debug(f"Connection refuse in stabilize: {e}")
                self.succ.update_reference(self.ref)

            except Exception as e:
                logger.debug(f"Error in stabilize: {e}")

            # logger.debug(self.succ_list)
            logger.debug(f"successor : {self.succ}, predecessor: {self.pred}")

            self.is_stabilizing = False
            time.sleep(10)

    def notify(self, node: "ChordNodeReference"):
        # logger.debug(
        #     f"Node: {node.id} IP: {node.ip} notify to Node: {self.id} IP: {self.ip}, as predeccesor "
        # )
        if node.id == self.id:
            pass
        if not self.pred or self._inbetween(node.id, self.pred.id, self.id):
            self.pred = node

    def fix_fingers(self):
        """Regularly refresh finger table entries."""
        while True:
            try:
                for i in range(
                    self.m - 1, -1, -1
                ):  # Iterate backwards through the finger table
                    self.next = (self.id + 2**i) % (2**self.m)
                    self.finger[i] = self.find_succ(self.next)
                    logger.debug(f"Updated finger[{i}] to {self.finger[i]}")
                    time.sleep(1)

                time.sleep(10)  # Sleep after updating all fingers

            except Exception as e:
                logger.debug(f"Error in fix fingers: {e}")
                logger.error(f"Error in fix fingers: {e}")
                time.sleep(5)  # Wait before retrying to avoid rapid failure loops

    def check_predecessor(self):
        while True:
            # logger.debug('Checking predecessor')
            try:
                logger.debug(f"Cheking predecessor -> {self.pred}")
                if self.pred:
                    self.pred.check_conn()
            except ConnectionRefusedError as e:
                try:
                    # rep = self.replicates[self.pred.id]
                    # logger.debug(f"rep: {rep}")
                    logger.debug(f"Connection refused with pred -> {self.pred}")
                    keys = []
                    for key in self.replicates.keys():
                        self.values[key] = self.replicates[key]
                        keys.append(key)
                    for key in keys:
                        self.replicates.pop(key)
                except Exception:
                    logger.debug(f"Error in check predecessor: {e}")
                self.pred = None
            except Exception as e:
                logger.debug(f"Error in check_predecessor {e}")
            time.sleep(10)

    def find(self, key: int):
        return key in self.find_succ(key).get_keys()

    def find_node(self, ip):
        sha_key = getShaRepr(ip)
        first = self.ref
        current = self.succ

        while current.ip != first.ip:
            if current.id == sha_key:
                return True
            else:
                current = current.succ

        return False if self.id != sha_key else True

    def store_key(self, key: int, value):
        key = getShaRepr(key)
        node = self.find_succ(key)
        logger.debug(f"Saving {key} in {node.ip}.")
        node.store_key(key, value)
        if node.succ.id != node.id:
            node.succ.store_key(key, value, True)
        if node.succ.succ.id != node.id:
            node.succ.succ.store_key(key, value, True)

    def get_all(self):
        hashs = {}
        first = self.ref
        while True:
            keys = first.get_keys()
            values = []
            for key in keys:
                values += first.get_value(key)
                hashs[key] = values
            succ = first.succ
            if succ.id == self.ref.id:
                break
            first = succ
        return hashs

    def save_replic(self, key, value):

        # Check if the key exists and if the value is already the same
        if key in self.replicates and self.replicates[key] == value:
            return  # Do nothing if the value is already the same

        self.replicates[key] = value

        # logger.debug(f'Replication succesfuly from {owner}')

    def replicate(self, key, value):
        # logger.debug(f'Trying to replicate ({info[1]}, {info[1]}) in destiny {dest.ip} as neighboor.')
        # logger.debug(f"Replicate 3")
        try:
            if self.id != self.succ.id:
                self.succ.store_key(key, value, True)
            if self.id != self.succ.succ.id:
                logger.debug(
                    f"In replicate self.id -> {self.id} and self.succ.succ.id -> {self.succ.succ.id}"
                )
                self.succ.succ.store_key(key, value, True)
        except Exception as e:
            logger.debug(f"Error in replicate {e}")

    def change_succ(self, succ):
        self.succ.clean_replicates()
        self.succ.succ.clean_replicates()

        self.succ.update_reference(succ)

        my_values = self.succ.get_my_values(self.id)
        for mv in my_values:
            if mv[0] not in self.values and mv[0] <= self.id:
                self.values[mv[0]] = mv[1]
            elif mv[0] > self.id:
                self.find_succ(mv[0]).store_key(mv[0], mv[1])

        for k in self.values.keys():
            self.succ.delete_key(k)

        for key in list(self.values.keys()):
            self.replicate(key, self.values[key])

        self.succ.notify(self.ref)

    def start_server(self):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            s.bind((self.ip, self.port))
            s.listen(10)

            while True:
                # logger.debug(f"Start_server: {self.ip}")

                conn, addr = s.accept()

                data = b""
                while True:
                    part = conn.recv(4096)
                    data += part
                    if len(part) < 4096:
                        break

                data = data.decode().split(",")

                # logger.debug(f"Data: {data}")

                data_resp = None
                option = int(data[0])

                try:
                    if option < 8:
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
                            ip = data[2]
                            self.notify(ChordNodeReference(id, ip, self.port))
                        elif option == CLOSEST_PRECEDING_FINGER:
                            id = int(data[1])
                            data_resp = self.closest_preceding_finger(id)

                    else:
                        if option == GET_VALUE:
                            key = int(data[1])
                            data_resp = self.values[key]
                        elif option == GET_KEYS:
                            data_resp = [key for key in self.values.keys()]
                        elif option == STORE_KEY:
                            key = int(data[1])
                            value = ",".join(data[2:])
                            value = eval(value)
                            logger.debug(f"Este es el value:{value}")

                            # logger.debug(f'Trying to save data with Key: {key} in Node: {self.id}')
                            if key not in self.values:
                                self.values[key] = [value]
                            else:
                                exist = False
                                for i, (k, v) in enumerate(self.values.items()):
                                    if v[i][1] == value[1]:
                                        exist = True
                                        break
                                if not exist:
                                    self.values[key] += [value]

                            # logger.debug(f'Data with Key: {key} saved succesfuly in Node: {self.id}')

                        elif option == UPDATE_KEY:
                            # logger.debug(f'Trying to update key: {key}')
                            key = int(data[1])
                            value = ",".join(data[2:])
                            value = eval(value)
                            self.values[key] = value
                            # logger.debug(f'Key:{key} updated succesfuly')

                        elif option == DELETE_KEY:
                            # logger.debug(f'Trying to delete key: {key}')
                            key = int(data[1])
                            if key in self.values:
                                del self.values[key]
                            # logger.debug(f'Key: {key} deleted succesfuly')

                        elif option == STORE_REPLICATE:
                            key = int(data[1])
                            value = ",".join(data[2:])
                            # logger.debug(f'Trying to save replic from Node: {owner} in Node: {self.id} using key: {key}')
                            value = eval(value)

                            self.save_replic(key, value)
                            # logger.debug(f'Replic saved succesfuly in Node: {self.id} using key: {key}')

                        elif option == GET_REPLICATE:
                            # logger.debug(f'Searching for replic with Owner: {owner} and Key: {key} in Node: {self.id}')
                            key = int(data[1])
                            data_resp = self.replicates[key]
                            # logger.debug(f'Replic with Key: {key} already founded in Node: {self.id}')

                        elif option == UPDATE_REPLICATE:
                            # logger.debug(f'Trying to update replic from Owner: {owner} and Key: {key} in Node: {self.id}')
                            key = int(data[1])
                            value = ",".join(data[2:])
                            value = eval(value)
                            self.replicates[key] = value
                            # logger.debug(f'Replic from Owner: {owner} and Key: {key} up to date succesfuly in Node: {self.id}')
                        elif option == DELETE_REPLICATE:
                            # logger.debug(f'Trying to delete replic from Owner: {owner} and Key: {key} in Node: {self.id}')
                            key = int(data[1])
                            if key in self.replicates:
                                del self.replicates[key]
                            # logger.debug(f'Replic from Owner: {owner} and Key: {key} up to date succesfuly in Node: {self.id}')
                        elif option == GET_MY_VALUES:
                            key = int(data[1])
                            data_resp = [
                                (k, self.values[k])
                                for k in self.values.keys()
                                if (key < self.id and k <= key)
                                or (key > self.id and k > self.id)
                            ]
                            # logger.debug(f"data_resp: {data_resp}")
                        elif option == CLEAN_REPLICATES:
                            self.replicates.clear()
                except ConnectionRefusedError as e:
                    logger.debug(f"Connection refused in start_server in ChordNode: {e}")
                    data_resp = "connection_refused"

                logger.debug(f"Sending {data_resp} to {addr} with option {option}")

                if data_resp and option < 8 and data_resp != "connection_refused":
                    response = f"{data_resp.id},{data_resp.ip}".encode()
                    conn.sendall(response)
                elif data_resp:
                    response = f"{data_resp}".encode()
                    conn.sendall(response)

                # logger.debug("The end")
                conn.close()