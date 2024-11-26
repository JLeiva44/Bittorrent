import zmq
import time
import threading
from ..Client.client import Client
from Client.client import Client  # Asegúrate de que este archivo esté en el mismo directorio
from Tracker.tracker import Tracker  # Asegúrate de que este archivo esté en el mismo directorio

def start_tracker(ip="127.0.0.1", port=6200):
    tracker = Tracker(ip, port)
    tracker.run()

def start_client(ip="127.0.0.1", port=6201):
    client = Client(ip, port)
    
    # Iniciar el servidor del cliente en un hilo separado
    server_thread = threading.Thread(target=client.run_server)
    server_thread.start()
    
    return client

def test_tracker_and_client():
    # Iniciar el tracker
    tracker_thread = threading.Thread(target=start_tracker)
    tracker_thread.start()
    
    time.sleep(1)  # Esperar a que el tracker esté listo

    # Iniciar un cliente
    client = start_client()

    time.sleep(1)  # Esperar a que el cliente esté listo

    # Simular la subida de un archivo al tracker
    tracker_urls = ["127.0.0.1:6200"]
    client.upload_file("/home/jose/Documents/proyectos/Bittorrent/Client/client_files/archivo1.txt", tracker_urls)  # Cambia esto a un archivo real

    # Obtener peers del tracker para verificar la funcionalidad
    torrent_info = client.get_peers_from_tracker(client.get_torrent_info("/home/jose/Documents/proyectos/Bittorrent/Client/client_files/archivo1.txt"))  # Cambia esto a un archivo real
    print("Peers obtenidos del tracker:", torrent_info)

    # Simular otro cliente que se registre en el tracker
    another_client = start_client("127.0.0.1", 6202)
    
    time.sleep(1)  # Esperar a que el segundo cliente esté listo
    
    another_client.upload_file("/home/jose/Documents/proyectos/Bittorrent/Client/client_files/archivo2.txt", tracker_urls)  # Cambia esto a otro archivo real

    time.sleep(1)  # Esperar a que se registre
    
    # Obtener peers nuevamente para verificar que ambos clientes están registrados
    peers_after_registration = client.get_peers_from_tracker(client.get_torrent_info("/home/jose/Documents/proyectos/Bittorrent/Client/client_files/archivo2.txt"))  # Cambia esto a un archivo real
    print("Peers después del registro:", peers_after_registration)

if __name__ == "__main__":
    test_tracker_and_client()
