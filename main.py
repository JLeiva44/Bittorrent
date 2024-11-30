import threading
import time
import os
from Client.client import Client
from Tracker.tracker import Tracker
from Tracker.chord import ChordNode, ChordNodeReference
def getShaRepr(data: str):
    return int(hashlib.sha1(data.encode()).hexdigest(), 16)

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
    #test_file_path = "Client/client_files/test_file.txt"
    test_file_path = "Client/client_files/archivo2.txt"
    # with open(test_file_path, "w") as f:
    #     f.write("Contenido del archivo de prueba para descarga.")

    tracker_url = ["127.0.0.1:8080"]
    peer_client.upload_file(test_file_path, tracker_urls=tracker_url)

    # Peer 2 intenta descargar el archivo
    torrent_file_path = "Client/torrent_files/archivo2.torrent"
    save_path = "Client/downloaded_files"
    os.makedirs(save_path, exist_ok=True)

    client.download_file(torrent_file_path, save_at=save_path)

    downloaded_file = os.path.join(save_path, "archivo2.txt")
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


def test_chord():
    # Crear tres nodos con IPs locales
    ip1 = "127.0.0.1"
    ip2 = "127.0.0.2"
    ip3 = "127.0.0.3"

    print("Creando nodo 1...")
    node1 = ChordNode(ip1, port=8001)

    # Esperar unos segundos para que el nodo 1 inicialice
    time.sleep(2)

    print("Creando nodo 2 y uniéndolo al nodo 1...")
    node2 = ChordNode(ip2, port=8002)
    node2.join(node1.ref)  # Nodo 2 se une al anillo utilizando Nodo 1

    # Esperar unos segundos para que se complete el proceso de unión
    time.sleep(2)

    print("Creando nodo 3 y uniéndolo al nodo 1...")
    node3 = ChordNode(ip3, port=8003)
    node3.join(node1.ref)  # Nodo 3 se une al anillo utilizando Nodo 1

    # Esperar unos segundos para que se estabilice el anillo
    time.sleep(5)

    # Imprimir información sobre los nodos
    print(f"Nodo 1: Sucesor -> {node1.succ}, Predecesor -> {node1.pred}")
    print(f"Nodo 2: Sucesor -> {node2.succ}, Predecesor -> {node2.pred}")
    print(f"Nodo 3: Sucesor -> {node3.succ}, Predecesor -> {node3.pred}")

    # Probar búsqueda de claves en el anillo
    key = "test-key"
    hashed_key = getShaRepr(key)
    print(f"Búsqueda del sucesor de la clave '{key}' (hash: {hashed_key})...")
    successor = node1.find_succ(hashed_key)
    print(f"Sucesor encontrado: {successor}")


if __name__ == "__main__":
    print("Iniciando pruebas de Bittorrent Client...")

    # Configurar el entorno de prueba
    # tracker, client1, client2 = setup_environment()

    # # Dar tiempo para que los servidores se inicien
    # time.sleep(1)

    # # Realizar pruebas individuales
    # # test_tracker_functionality(tracker)
    # # test_upload_file(client1, tracker)
    # test_download_file(client2, tracker, client1)
    # # test_peer_communication(client1, client2)

    # print("Pruebas completadas.")

    test_chord()
