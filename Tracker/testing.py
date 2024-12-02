import zmq
import time
import random
import hashlib
import threading

# Función para obtener el hash de una cadena
def sha256_hash(s):
    return int(hashlib.sha256(s.encode()).hexdigest(), 16)

# Función para simular el fallo de un nodo
def simulate_node_failure(nodes, failed_nodes):
    node_to_fail = random.choice(nodes)
    nodes.remove(node_to_fail)
    failed_nodes.append(node_to_fail)
    print(f"Simulating failure of node: {node_to_fail}")
    time.sleep(2)  # Simular un fallo por unos segundos

# Función para simular la reintegración de un nodo
def simulate_node_recovery(nodes, failed_nodes):
    if failed_nodes:
        node_to_recover = failed_nodes.pop()
        nodes.append(node_to_recover)
        print(f"Simulating recovery of node: {node_to_recover}")
        time.sleep(2)  # Simular la recuperación de un nodo

# Función para almacenar y recuperar datos, y verificar la consistencia
def test_data_persistence(tracker_address, piece_hash, peer_ip, peer_port):
    context = zmq.Context()
    socket = context.socket(zmq.REQ)
    socket.connect(tracker_address)

    # Añadir un peer a la base de datos del tracker
    add_message = {
        "action": "add_to_database",
        "pieces_sha1": piece_hash,
        "peer": [peer_ip, peer_port]
    }
    socket.send_json(add_message)
    response = socket.recv_json()
    print(f"Add to database response: {response}")

    # Recuperar la lista de peers
    get_message = {
        "action": "get_peers",
        "pieces_sha1": piece_hash
    }
    socket.send_json(get_message)
    response = socket.recv_json()
    print(f"Get peers response: {response}")

    return response.get("peers", [])

# Función principal para verificar la red distribuida
def verify_network_stability(tracker_address, nodes):
    piece_hash = sha256_hash("test_piece")
    peer_ip = "127.0.0.1"
    peer_port = random.randint(8002, 9000)

    failed_nodes = []

    for _ in range(5):
        print("\n--- Running Test Step ---")
        # Probar la persistencia de datos con nodos activos
        peers = test_data_persistence(tracker_address, piece_hash, peer_ip, peer_port)
        if not peers:
            print("No peers found, something might be wrong with the network.")
            continue

        # Simular un fallo en un nodo aleatorio
        simulate_node_failure(nodes, failed_nodes)

        # Verificar la consistencia de datos después de la caída de un nodo
        print(f"Testing data consistency after node failure...")
        peers_after_failure = test_data_persistence(tracker_address, piece_hash, peer_ip, peer_port)
        if peers != peers_after_failure:
            print("Warning: Peers list changed after node failure.")

        # Simular la recuperación de un nodo
        simulate_node_recovery(nodes, failed_nodes)

        # Verificar la consistencia de datos después de la recuperación de un nodo
        print(f"Testing data consistency after node recovery...")
        peers_after_recovery = test_data_persistence(tracker_address, piece_hash, peer_ip, peer_port)
        if peers_after_failure != peers_after_recovery:
            print("Warning: Peers list changed after node recovery.")
        
        time.sleep(5)  # Esperar entre pruebas

# Configuración del servidor tracker
tracker_ip = "127.0.0.1"
tracker_port = "8080"
tracker_address = f"tcp://{tracker_ip}:{tracker_port}"

# Lista de nodos disponibles para la prueba (simulando múltiples nodos)
nodes = [f"127.0.0.1:{port}" for port in range(8002, 8020)]

# Ejecutar el script de prueba
verify_network_stability(tracker_address, nodes)
