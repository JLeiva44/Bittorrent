import argparse
import logging
#from Client.bclient_logger import logger  # Asegúrate de tener configurado este logger
from client import Client
import socket

logging.basicConfig(level=logging.DEBUG,filename=f'logs_{socket.gethostbyname(socket.gethostname())}.log',filemode='w', format='%(asctime)s - %(levelname)s - %(message)s')

logger = logging.getLogger(__name__)

def main():
    parser = argparse.ArgumentParser(description="Cliente para red P2P")
    parser.add_argument("--ip", type=str, default=socket.gethostbyname(socket.gethostname()), help="Dirección IP del cliente")
    parser.add_argument("--port", type=int,default=8080, help="Puerto del cliente")
    parser.add_argument("--peer-id", help="ID único del peer (opcional)")
    parser.add_argument("command", choices=["upload", "download", "connect-tracker", "get-peers", "test-request"], help="Comando a ejecutar")
    parser.add_argument("--path", type=str, default="client_files/test_file.txt", help="Ruta del archivo a cargar o .torrent a descargar")
    parser.add_argument("--save-at",type=str, default="downloaded_files", help="Directorio donde guardar los archivos descargados")
    parser.add_argument("--tracker-urls", nargs="+", help="URLs de trackers (formato IP:PORT)")
    parser.add_argument("--torrent-info", help="Archivo .torrent para obtener información")
    parser.add_argument("--remove", action="store_true", help="Eliminar peer del tracker")
    
    args = parser.parse_args()

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
        if not args.path or not args.save_at:
            logger.error("Para descargar un archivo necesitas proporcionar --path y --save-at")
            return
        client.download_file(args.path, args.save_at)
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

if __name__ == "__main__":
    main()
