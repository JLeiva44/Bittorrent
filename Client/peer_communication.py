import threading
import socket
import zmq
from bclient_logger import logger
from pieces_manager import PieceManager
import base64
# TODO arreglar
class PeerCommunication:
    def __init__(self, ip, port, context):
        self.ip = ip
        self.port = port
        self.context = context
        self.lock = threading.Lock()

    def run_server(self):
        """Servidor que escucha conexiones de otros peers."""
        server_socket = self.context.socket(zmq.REP)
        server_socket.bind(f'tcp://{self.ip}:{self.port}')

        while True:
            try:
                poller = zmq.Poller()
                poller.register(server_socket, zmq.POLLIN)

                if poller.poll(1000):  # Timeout de 1 segundo
                    message = server_socket.recv_json()
                    action_type = message.get("action")
                    # Aquí puedes delegar la lógica específica
                    response = self.handle_request(action_type, message)
                    server_socket.send_json(response)
            except Exception as e:
                logger.error(f"Error en servidor Peer: {e}")

    def _send_data(self, request, ip, port, timeout=10000):
        """Envía datos a otro peer usando ZeroMQ."""
        try:
            with self.context.socket(zmq.REQ) as s:
                s.connect(f'tcp://{ip}:{port}')
                s.send_json(request)
                poller = zmq.Poller()
                poller.register(s, zmq.POLLIN)

                if poller.poll(timeout):
                    return s.recv_json()
                else:
                    raise zmq.Again("Timeout esperando respuesta")
        except Exception as e:
            logger.error(f"Error en la comunicación con {ip}:{port}: {e}")
            return None

    def handle_request(self, action_type, message):
        """Lógica para manejar solicitudes entrantes."""
        # Implementa lógica específica para diferentes tipos de acciones.
        # if action_type == "get_bit_field":
        #     return {"bitfield": []}  # Solo un ejemplo, delega a `PieceManager`
        

        if action_type == "get_bit_field":
            response = self.get_bit_field_of(message['info'])
            #logger.debug(f"GetBitfieldResponse: {response}")
            return response
            
        elif action_type == "get_block":
            response = self.get_block_of_piece(message['info'], message['piece_index'], message['block_offset'])
            #logger.debug(f"GetBlockResponse: {response}")
            return response

        elif action_type == "request_test":
            response = {'id':self.peer_id}
            return response
        
        return {"error": "Unknown action"}

    def get_bit_field_of(self, info):
        try:
            # Validar que la información necesaria esté presente
            if not info or 'pieces' not in info or 'piece length' not in info:
                logger.error("Invalid torrent info provided for bitfield.")
                return {"error": "Invalid torrent info"}

            piece_manager = PieceManager(info, 'client_files')
            return {"bitfield": piece_manager.bitfield}
        except Exception as e:
            logger.error(f"Error generating bitfield: {e}")
            return {"error": "Error generating bitfield"}
    def get_block_of_piece(self, info: dict, piece_index: int, block_offset: int):
        try:
            piece_manager = PieceManager(info, 'client_files')
            block = piece_manager.get_block_piece(piece_index, block_offset)

            # Asegurarse de que los datos estén codificados en Base64
            return {"data": base64.b64encode(block.data).decode('utf-8')}
        except Exception as e:
            logger.error(f"Error retrieving block {block_offset} of piece {piece_index}: {e}")
            return {"error": "Failed to retrieve block"}
            # piece_manager = PieceManager(info['info'], 'Client/client_files')
            # return {"data": piece_manager.get_block_piece(piece_index, block_offset).data}   
