import sys
import time
import threading
import zmq
from Tracker.chordpgr import ChordNode, ChordNodeReference,getShaRepr
# Función para obtener una dirección IP local

# Función para crear y unirse a un nodo Chord
def create_and_join_chord_node(ip, port, join_ip=None):
    node = ChordNode(ip, port)
    
    if join_ip:
        print(f"Un nodo nuevo se unirá a la red Chord en {join_ip}.")
        join_node = ChordNodeReference(getShaRepr(join_ip), join_ip, port)
        node.join(join_node)
    else:
        print("Nodo creado como el primer nodo en la red Chord.")
    
    return node

# Función para probar las operaciones de Chord
def test_chord_operations(node):
    print(f"Probando operaciones con el nodo: {node.ref}")

    # Verificar el sucesor y predecesor
    print("Verificando sucesor y predecesor...")
    print(f"Sucesor: {node.succ}")
    print(f"Predecesor: {node.pred}")
    
    # Realizar búsqueda de sucesor
    test_id = node.id + 1  # Usamos un id mayor al del nodo
    print(f"Buscando sucesor para el id {test_id}...")
    successor = node.find_succ(test_id)
    print(f"Sucesor encontrado: {successor}")

    # Verificar la tabla de dedos (finger table)
    print("Verificando la tabla de dedos (finger table)...")
    for i in range(len(node.finger)):
        print(f"Finger {i}: {node.finger[i]}")

    # Verificar el predecesor más cercano (closest preceding finger)
    print(f"Buscando predecesor más cercano para el id {test_id}...")
    closest_preceding_finger = node.closest_preceding_finger(test_id)
    print(f"Predecesor más cercano: {closest_preceding_finger}")

# Función para crear múltiples nodos y probar la funcionalidad
def test_chord_network():
    ip = '127.0.0.1'
    port = 8001
    print("Creando nodo 1 (primer nodo de la red Chord)...")
    node1 = ChordNode(ip,port)
    ref1 = node1.ref

    time.sleep(2)  # Esperar para que el nodo 1 se estabilice

    # Crear segundo nodo y unirlo a la red
    print("\nCreando nodo 2 y uniéndolo a la red...")
    node2 = ChordNode(ip,8002)
    ref2 = node2.ref

    time.sleep(2)  # Esperar para que el nodo 2 se estabilice

    # Crear tercer nodo y unirlo a la red
    print("\nCreando nodo 3 y uniéndolo a la red...")
    node3 = ChordNode(ip,8003)
    ref3 = node3.ref

    time.sleep(2)  # Esperar para que el nodo 3 se estabilice
    node2.join(node1.ref)  # Nodo 2 se une al anillo utilizando Nodo 1

    time.sleep(2)

    node3.join(node1.ref)  # Nodo 3 se une al anillo utilizando Nodo 1

    # Esperar unos segundos para que se estabilice el anillo
    time.sleep(5)

    # Imprimir información sobre los nodos
    print(f"Nodo 1: Sucesor -> {node1.succ}, Predecesor -> {node1.pred}")
    print(f"Nodo 2: Sucesor -> {node2.succ}, Predecesor -> {node2.pred}")
    print(f"Nodo 3: Sucesor -> {node3.succ}, Predecesor -> {node3.pred}")


    
if __name__ == "__main__":
    test_chord_network()
