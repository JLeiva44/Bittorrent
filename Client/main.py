import argparse
import logging
import socket
from client2 import Client  
import threading

from bclient_logger import logger

# def process_command(client, command_args):
#     """Procesa y ejecuta un comando específico."""
#     try:
#         command = command_args[0]
#         if command == "upload":
#             path = command_args[1]
#             tracker_urls = command_args[2]
#             logger.debug(f"path: {path}")
#             logger.debug(f"tracker: {tracker_urls}")
#             if not path or not tracker_urls:
#                 logger.error("Para subir un archivo necesitas proporcionar la ruta y los trackers.")
#                 return
#             client.upload_file(path, tracker_urls)
#             logger.info("Archivo subido y añadido a los trackers.")

#         elif command == "download":
#             torrent_info = command_args[1]
#             save_at = command_args[2]
#             if not torrent_info or not save_at:
#                 logger.error("Para descargar un archivo necesitas proporcionar el archivo .torrent y el directorio destino.")
#                 return
#             client.download_file(torrent_info, save_at)
#             logger.info("Descarga completada.")

#         elif command == "connect-tracker":
#             torrent_info = command_args[1]
#             tracker_urls = command_args[2:]
#             trackers = [tuple(url.split(':')) for url in tracker_urls]
#             for tracker_ip, tracker_port in trackers:
#                 client.connect_to_tracker(tracker_ip, int(tracker_port), torrent_info, False)
#             logger.info("Conexión con trackers completada.")

#         elif command == "get-peers":
#             torrent_info = command_args[1]
#             from torrent_utils import TorrentReader
#             reader = TorrentReader(torrent_info)
#             info = reader.build_torrent_info()
#             peers = client.get_peers_from_tracker(info)
#             logger.info(f"Peers obtenidos: {peers}")

#         elif command == "test-request":
#             tracker_urls = command_args[1:]
#             for tracker in tracker_urls:
#                 ip, port = tracker.split(":")
#                 client.request_test(ip, int(port))
#             logger.info("Pruebas completadas.")

#         else:
#             logger.error(f"Comando desconocido: {command}")
#     except IndexError:
#         logger.error("Faltan argumentos para el comando.")
#     except Exception as e:
#         logger.error(f"Error ejecutando el comando '{command_args[0]}': {e}")

# def main():
#     parser = argparse.ArgumentParser(description="Cliente para red P2P")
#     parser.add_argument("--ip", type=str, default=socket.gethostbyname(socket.gethostname()), help="Dirección IP del cliente")
#     parser.add_argument("--port", type=int, default=8080, help="Puerto del cliente")
#     parser.add_argument("--peer-id", help="ID único del peer (opcional)")
    
#     args = parser.parse_args()

#     try:
#         # Configurar el cliente
#         client = Client(args.ip, str(args.port), args.peer_id)
#         threading.Thread(target=client.run_server, daemon=True).start() # Start server thread
#         logger.info("Cliente iniciado. Esperando comandos...")

#         # Bucle interactivo
#         while True:
#             try:
#                 user_input = input("Introduce un comando: ").strip()
#                 if user_input.lower() in ["exit", "quit"]:
#                     logger.info("Saliendo del cliente...")
#                     break
#                 command_args = user_input.split()
#                 process_command(client, command_args)
#             except KeyboardInterrupt:
#                 logger.info("Interrupción manual detectada. Cerrando cliente...")
#                 break

#     except Exception as e:
#         logger.error(f"Error crítico en el Cliente: {e}")

# if __name__ == "__main__":
#     main()




import argparse
import logging
#from Client.bclient_logger import logger  # Asegúrate de tener configurado este logger
from client2 import Client # este es el cliente viejo
import socket

logging.basicConfig(level=logging.DEBUG,filename=f'logs_{socket.gethostbyname(socket.gethostname())}.log',filemode='w', format='%(asctime)s - %(levelname)s - %(message)s')

logger = logging.getLogger(__name__)

def main():
    parser = argparse.ArgumentParser(description="Cliente para red P2P")
    parser.add_argument("--ip", type=str, default=socket.gethostbyname(socket.gethostname()), help="Dirección IP del cliente")
    parser.add_argument("--port", type=int,default=8080, help="Puerto del cliente")
    parser.add_argument("--peer-id", help="ID único del peer (opcional)")
    parser.add_argument("command", choices=["upload", "download", "connect-tracker", "get-peers", "test-request"], help="Comando a ejecutar")
    parser.add_argument("--path", type=str, default="client_files/foto.JPG", help="Ruta del archivo a cargar o .torrent a descargar")
    parser.add_argument("--save-at",type=str, default="downloaded_files/c3", help="Directorio donde guardar los archivos descargados")
    parser.add_argument("--tracker-urls", nargs="+", help="URLs de trackers (formato IP:PORT)")
    parser.add_argument("--torrent-info", default='torrent_files/foto.torrent', help="Archivo .torrent para obtener información")
    parser.add_argument("--remove", action="store_true", help="Eliminar peer del tracker")
    
    args = parser.parse_args()

    try:
        # Configurar el cliente
        client = Client(args.ip, str(args.port), args.peer_id)

        # Ejecutar el comando
        if args.command == "upload":
            if not args.path or not args.tracker_urls:
                logger.error("Para subir un archivo necesitas proporcionar --path y --tracker-urls")
                return
            
            client.upload_file(args.path, args.tracker_urls)
            logger.info("Archivo subido y añadido a los trackers.")

        elif args.command == "download":
            if not args.torrent_info or not args.save_at:
                logger.error("Para descargar un archivo necesitas proporcionar --path y --save-at")
                return
            client.download_file(args.torrent_info, args.save_at)
            logger.info("Descarga completada.")

        elif args.command == "connect-tracker":
            if not args.torrent_info or not args.tracker_urls:
                logger.error("Para conectar a un tracker necesitas proporcionar --torrent-info y --tracker-urls")
                return
            trackers = [tuple(url.split(':')) for url in args.tracker_urls]
            for tracker_ip, tracker_port in trackers:
                client.connect_to_tracker(tracker_ip, int(tracker_port), args.torrent_info, args.remove)
            logger.info("Conexión con trackers completada.")

        elif args.command == "get-peers":
            print("Entrando en get-peers")
            if not args.torrent_info:
                logger.error("Para obtener peers necesitas proporcionar --torrent-info")
                return
            from torrent_utils import TorrentReader
            reader = TorrentReader(args.torrent_info)
            info = reader.build_torrent_info()
            peers = client.get_peers_from_tracker(info)
            logger.info(f"Peers obtenidos: {peers}")

        elif args.command == "test-request":
            if not args.tracker_urls:
                logger.error("Para probar una solicitud necesitas proporcionar --tracker-urls")
                return
            for tracker in args.tracker_urls:
                ip, port = tracker.split(":")
                client.request_test(ip, int(port))
            logger.info("Pruebas completadas.")

        while True:
            pass    

    except KeyboardInterrupt:
        logger.info("El servidor del CLiente ha sido detenido manualmente.")
    except Exception as e:
        logger.error(f"Error crítico en el Cliente: {e}")

if __name__ == "__main__":
    main()
