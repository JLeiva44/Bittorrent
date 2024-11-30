import logging
import requests

# Configuración del logger
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

TRACKER_HOST = "localhost"
TRACKER_PORT = 8080
TRACKER_URL = f"http://{TRACKER_HOST}:{TRACKER_PORT}"

CLIENTS = [
    {"id": 1, "host": "localhost", "port": 9001},
    {"id": 2, "host": "localhost", "port": 9002},
]

TEST_FILE = "testfile.txt"


def register_file(client, file_name):
    """
    Simula el registro de un archivo desde un cliente.
    """
    logging.info(f"Cliente {client['id']} registrando archivo {file_name} en el Tracker...")
    data = {
        "action": "add_to_database",
        "pieces_sha1": file_name,
        "peer": [client["host"], client["port"]],
    }
    try:
        response = requests.post(f"{TRACKER_URL}/", json=data)
        logging.info(f"Respuesta del Tracker: {response.json()}")
        return True
    except Exception as e:
        logging.error(f"Error al registrar archivo: {e}")
        return False


def search_file(client, file_name):
    """
    Simula la búsqueda de un archivo desde un cliente.
    """
    logging.info(f"Cliente {client['id']} buscando archivo {file_name} en el Tracker...")
    data = {"action": "get_peers", "pieces_sha1": file_name}
    try:
        response = requests.post(f"{TRACKER_URL}/", json=data)
        logging.info(f"Peers encontrados para {file_name}: {response.json()}")
        return True
    except Exception as e:
        logging.error(f"Error al buscar archivo: {e}")
        return False


def main():
    for client in CLIENTS:
        # Registrar el archivo
        if register_file(client, TEST_FILE):
            # Buscar el archivo
            search_file(client, TEST_FILE)


if __name__ == "__main__":
    main()
