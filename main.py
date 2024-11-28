import zmq
import time
import threading
from Client.client import Client  # Asegúrate de que este archivo esté en el mismo directorio
from Tracker.tracker import Tracker  # Asegúrate de que este archivo esté en el mismo directorio
from Client.torrent_utils import TorrentReader 
from Client.bclient_logger import logger

def start_tracker(ip="127.0.0.1", port=6200):
    tracker = Tracker(ip, port)
    #tracker.run()
    return tracker

def start_client(ip="127.0.0.1", port=6201):
    client = Client(ip, port)
    
    # # Iniciar el servidor del cliente en un hilo separado
    # server_thread = threading.Thread(target=client.run_server)
    # server_thread.start()
    
    return client

def test_tracker_and_client():
    # Iniciar el tracker
    # tracker_thread = threading.Thread(target=start_tracker)
    # tracker_thread.start()
    
    tracker1 = start_tracker()

    time.sleep(1)  # Esperar a que el tracker esté listo

    # Iniciar un cliente
    client = start_client()

    time.sleep(1)  # Esperar a que el cliente esté listo

    # Simular la subida de un archivo al tracker
    tracker_urls = ["127.0.0.1:6200"]
    file_1_path = "/home/jose/Documents/proyectos/Bittorrent/Client/client_files/archivo1.txt"
    client.upload_file(file_1_path, tracker_urls)  # Cambia esto a un archivo real

    # Obtener peers del tracker para verificar la funcionalidad
    dottorrent_file1_path = "Client/torrent_files/archivo1.torrent"
    tr = TorrentReader(dottorrent_file1_path)
    torrent_info = tr.build_torrent_info()
    peers = client.get_peers_from_tracker(torrent_info)
    print("Peers obtenidos del tracker:", peers)

    # Simular otro cliente que se registre en el tracker
    another_client = start_client("127.0.0.1", 6202)
    
    time.sleep(1)  # Esperar a que el segundo cliente esté listoget_torrent_in
    
    another_client.upload_file("/home/jose/Documents/proyectos/Bittorrent/Client/client_files/archivo2.txt", tracker_urls)  # Cambia esto a otro archivo real

    time.sleep(1)  # Esperar a que se registre
    
    # Obtener peers nuevamente para verificar que ambos clientes están registrados
    dottorrent_file2_path = "Client/torrent_files/archivo2.torrent"
    tr = TorrentReader(dottorrent_file2_path)
    torrent_info = tr.build_torrent_info()
    peers = client.get_peers_from_tracker(torrent_info)
    peers_after_registration = client.get_peers_from_tracker(torrent_info)  # Cambia esto a un archivo real
    print("Peers después del registro:", peers_after_registration)



def test_download():
    # Iniciar el tracker
    # tracker_thread = threading.Thread(target=start_tracker)
    # tracker_thread.start()

    tracker = Tracker(ip="127.0.0.1", port=6200)
    
    time.sleep(1)  # Esperar a que el tracker esté listo

    # Iniciar un cliente para subir un archivo
    upload_client = Client(ip="127.0.0.1", port=6201)

    time.sleep(1)  # Esperar a que el cliente esté listo

    # Simular la subida de un archivo al tracker
    file_to_upload = "Client/client_files/archivo1.txt"  # Cambia esto a un archivo real
    tracker_urls = ["127.0.0.1:6200"]
    
    upload_client.upload_file(file_to_upload, tracker_urls)

    time.sleep(1)  # Esperar a que se registre

    # Iniciar otro cliente para descargar el archivo
    download_client = Client("127.0.0.1", 6202)

    time.sleep(1)  # Esperar a que el segundo cliente esté listo

    # Simular la descarga del archivo
    download_client.download_file("Client/torrent_files/archivo1.torrent", save_at='Client/downloaded_files')  # Cambia esto a un archivo torrent real

if __name__ == "__main__":
    test_download()