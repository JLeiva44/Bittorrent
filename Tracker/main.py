import argparse
import logging
import socket
from tracker import Tracker  # Asegúrate de que el módulo de tu clase Tracker esté correctamente referenciado.
from tracker_logger import logger
from chord import ChordNode, ChordNodeReference

addresses = ['127.17.0.3','127.17.0.3',"127.17.0.2"]

def main():
    # Parser para argumentos desde la línea de comandos
    parser = argparse.ArgumentParser(description="Inicia el servidor del Tracker.")
    parser.add_argument('--ip', type=str, default=socket.gethostbyname(socket.gethostname()), help="Dirección IP en la que se ejecutará el Tracker.")
    parser.add_argument('--port', type=int, default=8080, help="Puerto en el que se ejecutará el Tracker.")
    parser.add_argument('--chord_m', type=int, default=160, help="Número de bits para el anillo Chord.")

    args = parser.parse_args()

    try:
        logger.info("--------------LOGER DEL TESTER-----------------")
        logger.info(f"Iniciando el TRACKER en {args.ip}:{args.port} con un anillo Chord de {args.chord_m} bits...")
        # Crear instancia del Tracker
        tracker = Tracker(ip=args.ip)  #, port=str(args.port), chord_m=args.chord_m)
        logger.info("Tracker inicializado exitosamente. Esperando conexiones...")

        # Vamos a conectarnos a los demas
        
        # Mantener el proceso activo
        while True:
            pass

    except KeyboardInterrupt:
        logger.info("El servidor del Tracker ha sido detenido manualmente.")
    except Exception as e:
        logger.error(f"Error crítico en el Tracker: {e}")

if __name__ == "__main__":
    main()
