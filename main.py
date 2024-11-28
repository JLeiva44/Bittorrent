import zmq
import time
import threading
from Client.client import Client  # Asegúrate de que este archivo esté en el mismo directorio
from Tracker.tracker import Tracker  # Asegúrate de que este archivo esté en el mismo directorio
from Client.torrent_utils import TorrentReader 
from Client.bclient_logger import logger


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
    file_1_path = "/home/jose/Documents/proyectos/Bittorrent/Client/client_files/archivo1.txt"
    try:
        client.upload_file(file_1_path, tracker_urls)  # Cambia esto a un archivo real
        logger.info("Archivo subido correctamente")
    except Exception as e:
        logger.error(f"Error al subir el archivo: {e}")    

    # Obtener peers del tracker para verificar la funcionalidad
    dottorrent_file1_path = "Client/torrent_files/archivo1.torrent"

    try:
        tr = TorrentReader(dottorrent_file1_path)
        torrent_info = tr.build_torrent_info()
        peers = client.get_peers_from_tracker(torrent_info)
        print("Peers obtenidos del tracker:", peers)
    except Exception as e:
        logger.error(f"Error al obtener peers del tracker: {e}")

    # Simular otro cliente que se registre en el tracker
    another_client = Client("127.0.0.1", 6202)
    time.sleep(1)  # Esperar a que el segundo cliente esté listo


    
    try:
        another_client.upload_file("/home/jose/Documents/proyectos/Bittorrent/Client/client_files/archivo2.txt", tracker_urls)  # Cambia esto a otro archivo real
        logger.info("Segundo archivo subido correctamente.")
    except Exception as e:
        logger.error(f"Error al subir segundo archivo: {e}")

    time.sleep(1)  # Esperar a que se registre
    
    # Obtener peers nuevamente para verificar que ambos clientes están registrados
    dottorrent_file2_path = "Client/torrent_files/archivo2.torrent"
    
    try:
        tr = TorrentReader(dottorrent_file2_path)
        torrent_info = tr.build_torrent_info()
        peers_after_registration = client.get_peers_from_tracker(torrent_info)  # Cambia esto a un archivo real
        print("Peers después del registro:", peers_after_registration)
    except Exception as e:
        logger.error(f"Error al obtener peers después del registro: {e}")


def test_download():
    # Iniciar el tracker
    tracker_thread = threading.Thread(target=start_tracker)
    tracker_thread.start()

    time.sleep(1)  # Esperar a que el tracker esté listo


    # Iniciar un cliente para subir un archivo
    upload_client = start_client()

    time.sleep(1)  # Esperar a que el cliente esté listo

    # Simular la subida de un archivo al tracker
    file_to_upload = "Client/client_files/archivo1.txt"  # Cambia esto a un archivo real
    tracker_urls = ["127.0.0.1:6200"]
    
    try:
        upload_client.upload_file(file_to_upload, tracker_urls)
        logger.info("Archivo subido correctamente.")
    except Exception as e:
        logger.error(f"Error al subir archivo: {e}")

    time.sleep(1)  # Esperar a que se registre

    # Iniciar otro cliente para descargar el archivo
    download_client = start_client("127.0.0.1", 6202)

    time.sleep(1)  # Esperar a que el segundo cliente esté listo

    # Simular la descarga del archivo
    try:
        download_client.download_file("Client/torrent_files/archivo1.torrent", save_at='Client/downloaded_files')  # Cambia esto a un archivo torrent real
        logger.info("Descarga completada.")
    except Exception as e:
        logger.error(f"Error durante la descarga: {e}")

def test_clients_conection():
    # Iniciar varios clientes
    clients = []
    client_ip = "127.0.0.1"
    for i in range(3):
        client_port = 8000 + i  # Diferentes puertos para cada cliente
        clients.append(Client(client_ip, client_port))

    time.sleep(1)  # Esperar a que todos los clientes estén listos

    # Simular solicitudes entre clientes
    for i in range(len(clients)):
        target_client_index = (i + 1) % len(clients)  # Conectar con el siguiente cliente
        target_client = clients[target_client_index]
        clients[i].request_test(target_client.ip, target_client.port)
        #slogger.debug(response)

if __name__ == "__main__":
    test_clients_conection()
