import logging
import socket
#Configurar el logger
logging.basicConfig(level=logging.DEBUG,filename=f'logs_{socket.gethostbyname(socket.gethostname())}.log',filemode='w', format='%(asctime)s - %(levelname)s - %(message)s')

logger = logging.getLogger(__name__)