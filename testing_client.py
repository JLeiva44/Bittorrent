import zmq
import random
import time
import threading

class Client:
    def __init__(self, ip, port):
        self.ip = ip
        self.port = port
        self.context = zmq.Context()
        self.server_socket = self.context.socket(zmq.REP)
        self.server_socket.bind(f"tcp://{self.ip}:{self.port}")
        threading.Thread(target=self.run_server, daemon=True).start()

    def run_server(self):
        print(f"Cliente escuchando en tcp://{self.ip}:{self.port}")
        while True:
            try:
                message = self.server_socket.recv_json()
                action_type = message.get("action")

                if action_type == "get_file":
                    file_data = self.simulate_file_download(message['file_name'])
                    self.server_socket.send_json({"status": "success", "data": file_data})
                else:
                    self.server_socket.send_json({"error": "Unknown action"})
            except zmq.ZMQError as e:
                print(f"ZMQError occurred: {e}")
            except Exception as e:
                print(f"An error occurred in the server: {e}")

    def simulate_file_download(self, file_name):
        # Simula la descarga de un archivo
        print(f"Descargando {file_name}...")
        time.sleep(random.uniform(0.5, 2))  # Simula tiempo de descarga
        return f"Contenido de {file_name}"

    def request_file(self, peer_ip, peer_port, file_name):
        client_socket = self.context.socket(zmq.REQ)
        client_socket.connect(f"tcp://{peer_ip}:{peer_port}")

        try:
            request = {"action": "get_file", "file_name": file_name}
            client_socket.send_json(request)
            response = client_socket.recv_json()
            print(f"Respuesta del peer {peer_ip}:{peer_port}: {response}")
        except Exception as e:
            print(f"Error al solicitar archivo: {e}")
        finally:
            client_socket.close()

def main():
    # Iniciar varios clientes
    clients = []
    for i in range(3):
        client_ip = "127.0.0.1"
        client_port = 8000 + i  # Diferentes puertos para cada cliente
        clients.append(Client(client_ip, client_port))

    time.sleep(1)  # Esperar a que todos los clientes estén listos

    # Simular solicitudes entre clientes
    for i in range(len(clients)):
        target_client_index = (i + 1) % len(clients)  # Conectar con el siguiente cliente
        clients[i].request_file(clients[target_client_index].ip, clients[target_client_index].port, f"archivo{i}.txt")

if __name__ == "__main__":
    main()
