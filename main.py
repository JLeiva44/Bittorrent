import threading
import time
import os
from Client.client import Client
from Tracker.tracker import Tracker

def setup_environment():
    """
    Configura un entorno de prueba con un tracker y dos peers (clientes).
    """
    # Iniciar el tracker
    tracker = Tracker(ip='127.0.0.1', port=8080)

    # Iniciar dos clientes (peers)
    client1 = Client(ip='127.0.0.1', port=8001, peer_id="Peer1")
    client2 = Client(ip='127.0.0.1', port=8002, peer_id="Peer2")
    
    return tracker, client1, client2


def test_upload_file(client, tracker):
    """
    Prueba la funcionalidad de subida de un archivo por un cliente.
    """
    print("\n[Test] Subida de archivo por Peer 1")

    # Crear un archivo de prueba
    test_file_path = "Client/client_files/test_file.txt"
    with open(test_file_path, "w") as f:
        f.write("Contenido del archivo de prueba.")

    tracker_url = ["127.0.0.1:8080"]
    client.upload_file(test_file_path, tracker_urls=tracker_url, private=False, comments="Prueba de archivo", source="local")

    print(f"Archivo '{test_file_path}' subido por Peer1.")
    os.remove(test_file_path)  # Limpieza del archivo de prueba


def test_download_file(client, tracker, peer_client):
    """
    Prueba la descarga de un archivo desde otro cliente.
    """
    print("\n[Test] Descarga de archivo por Peer 2")

    # Simular subida del archivo por Peer 1
    test_file_path = "Client/client_files/test_file.txt"
    with open(test_file_path, "w") as f:
        f.write("Contenido del archivo de prueba para descarga.")

    tracker_url = ["127.0.0.1:8080"]
    peer_client.upload_file(test_file_path, tracker_urls=tracker_url)

    # Peer 2 intenta descargar el archivo
    torrent_file_path = "Client/torrent_files/test_file.torrent"
    save_path = "Client/downloaded_files"
    os.makedirs(save_path, exist_ok=True)

    client.download_file(torrent_file_path, save_at=save_path)

    downloaded_file = os.path.join(save_path, "test_file.txt")
    if os.path.exists(downloaded_file):
        print(f"Descarga exitosa. Archivo descargado en: {downloaded_file}")
    else:
        print("Error: El archivo no fue descargado correctamente.")

    # Limpieza
    #os.remove(test_file_path)
    #os.rmdir(save_path)


def test_tracker_functionality(tracker):
    """
    Prueba las funcionalidades básicas del tracker, como añadir y eliminar peers.
    """
    print("\n[Test] Funcionalidad del Tracker")
    pieces_sha1 = "fake_sha1_hash"

    # Añadir un peer al tracker
    tracker.add_to_database(pieces_sha1, "127.0.0.1", 8001)
    print("Añadido Peer 1 al tracker.")

    # Obtener peers del tracker
    peers = tracker.get_peers(pieces_sha1)
    print(f"Peers registrados para el archivo {pieces_sha1}: {peers}")

    # Eliminar el peer
    tracker.remove_from_database(pieces_sha1, "127.0.0.1", 8001)
    print("Peer 1 eliminado del tracker.")

    # Verificar que no hay peers registrados
    peers = tracker.get_peers(pieces_sha1)
    print(f"Peers registrados tras eliminación: {peers}")


def test_peer_communication(client1, client2):
    """
    Prueba de comunicación entre dos peers.
    """
    print("\n[Test] Comunicación entre peers")

    # Peer 1 solicita información del bitfield de Peer 2
    client2.request_test(ip="127.0.0.1", port=8001)


if __name__ == "__main__":
    print("Iniciando pruebas de Bittorrent Client...")

    # Configurar el entorno de prueba
    tracker, client1, client2 = setup_environment()

    # Dar tiempo para que los servidores se inicien
    time.sleep(1)

    # Realizar pruebas individuales
    # test_tracker_functionality(tracker)
    # test_upload_file(client1, tracker)
    test_download_file(client2, tracker, client1)
    # test_peer_communication(client1, client2)

    print("Pruebas completadas.")









# import zmq
# import time
# import threading
# from Client.client import Client  # Asegúrate de que este archivo esté en el mismo directorio
# from Tracker.tracker import Tracker  # Asegúrate de que este archivo esté en el mismo directorio
# from Client.torrent_utils import TorrentReader 
# from Client.bclient_logger import logger


# def start_tracker(ip="127.0.0.1", port=6200):
#     tracker = Tracker(ip, port)
#     tracker.run()

# def start_client(ip="127.0.0.1", port=6201):
#     client = Client(ip, port)
    
#     # Iniciar el servidor del cliente en un hilo separado
#     server_thread = threading.Thread(target=client.run_server)
#     server_thread.start()
    
#     return client

# def test_tracker_and_client():
#     # Iniciar el tracker
#     tracker = Tracker(ip="127.0.0.1", port=6200)
    
#     time.sleep(1)  # Esperar a que el tracker esté listo

#     # Iniciar un cliente
#     client = Client(ip="127.0.0.1", port=8000)

#     time.sleep(1)  # Esperar a que el cliente esté listo

#     # Simular la subida de un archivo al tracker
#     tracker_urls = ["127.0.0.1:6200"]
#     file_1_path = "/home/jose/Documents/proyectos/Bittorrent/Client/client_files/archivo1.txt"
#     try:
#         client.upload_file(file_1_path, tracker_urls)  # Cambia esto a un archivo real
#         logger.info("Archivo subido correctamente")
#     except Exception as e:
#         logger.error(f"Error al subir el archivo: {e}")    

#     # Obtener peers del tracker para verificar la funcionalidad
#     dottorrent_file1_path = "Client/torrent_files/archivo1.torrent"

#     try:
#         tr = TorrentReader(dottorrent_file1_path)
#         torrent_info = tr.build_torrent_info()
#         peers = client.get_peers_from_tracker(torrent_info)
#         print("Peers obtenidos del tracker:", peers)
#     except Exception as e:
#         logger.error(f"Error al obtener peers del tracker: {e}")

#     # Simular otro cliente que se registre en el tracker
#     another_client = Client("127.0.0.1", 8002)
#     time.sleep(1)  # Esperar a que el segundo cliente esté listo


    
#     try:
#         another_client.upload_file("/home/jose/Documents/proyectos/Bittorrent/Client/client_files/archivo2.txt", tracker_urls)  # Cambia esto a otro archivo real
#         logger.info("Segundo archivo subido correctamente.")
#     except Exception as e:
#         logger.error(f"Error al subir segundo archivo: {e}")

#     time.sleep(1)  # Esperar a que se registre
    
#     # Obtener peers nuevamente para verificar que ambos clientes están registrados
#     dottorrent_file2_path = "Client/torrent_files/archivo2.torrent"
    
#     try:
#         tr = TorrentReader(dottorrent_file2_path)
#         torrent_info = tr.build_torrent_info()
#         peers_after_registration = client.get_peers_from_tracker(torrent_info)  # Cambia esto a un archivo real
#         print("Peers después del registro:", peers_after_registration)
#     except Exception as e:
#         logger.error(f"Error al obtener peers después del registro: {e}")


# def test_download():
#     # Iniciar el tracker
#     tracker = Tracker(ip="127.0.0.1", port=6200)

#     time.sleep(1)  # Esperar a que el tracker esté listo


#     # Iniciar un cliente para subir un archivo
#     upload_client = Client(ip="127.0.0.1", port=8000)

#     time.sleep(1)  # Esperar a que el cliente esté listo

#     # Simular la subida de un archivo al tracker
#     file_to_upload = "Client/client_files/archivo1.txt"  # Cambia esto a un archivo real
#     tracker_urls = ["127.0.0.1:6200"]
    
#     try:
#         upload_client.upload_file(file_to_upload, tracker_urls)
#         logger.info("Archivo subido correctamente.")
#     except Exception as e:
#         logger.error(f"Error al subir archivo: {e}")

#     time.sleep(1)  # Esperar a que se registre

#     # Iniciar otro cliente para descargar el archivo
#     download_client = Client("127.0.0.1", 8001)

#     time.sleep(1)  # Esperar a que el segundo cliente esté listo

#     # Simular la descarga del archivo
#     try:
#         download_client.download_file("Client/torrent_files/archivo1.torrent", save_at='Client/downloaded_files')  # Cambia esto a un archivo torrent real
#         logger.info("Descarga completada.")
#     except Exception as e:
#         logger.error(f"Error durante la descarga: {e}")

# def test_clients_conection():
#     # Iniciar varios clientes
#     clients = []
#     client_ip = "127.0.0.1"
#     for i in range(3):
#         client_port = 8000 + i  # Diferentes puertos para cada cliente
#         clients.append(Client(client_ip, client_port))

#     time.sleep(1)  # Esperar a que todos los clientes estén listos

#     # Simular solicitudes entre clientes
#     for i in range(len(clients)):
#         target_client_index = (i + 1) % len(clients)  # Conectar con el siguiente cliente
#         target_client = clients[target_client_index]
#         clients[i].request_test(target_client.ip, target_client.port)
#         #slogger.debug(response)

# if __name__ == "__main__":
#     test_download()
