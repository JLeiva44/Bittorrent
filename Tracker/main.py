import logging
import requests

# Configuración del logger
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

TRACKER_HOST = "localhost"
TRACKER_PORT = 8080
TRACKER_URL = f"http://{TRACKER_HOST}:{TRACKER_PORT}"


def test_tracker():
    """
    Verifica las funcionalidades básicas del Tracker.
    """
    logging.info("Probando funcionalidades del Tracker...")

    # Obtener la base de datos inicial del Tracker
    try:
        response = requests.post(f"{TRACKER_URL}/get_database")
        logging.info(f"Base de datos inicial del Tracker: {response.json()}")
    except Exception as e:
        logging.error(f"Error al obtener la base de datos del Tracker: {e}")
        return False

    return True


def main():
    if test_tracker():
        logging.info("El Tracker está funcionando correctamente.")
    else:
        logging.error("El Tracker tiene problemas de funcionamiento.")


if __name__ == "__main__":
    main()
