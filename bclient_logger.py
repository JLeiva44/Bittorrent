import logging

'''Logging for BT'''

logging.basicConfig(level=logging.DEBUG,filename='Bittorrent.log', format='%(asctime)s - %(levelname)s - %(message)s')

logger = logging.getLogger("Bittorrent")
#logger.setLevel(logging.DEBUG)
handler = logging.StreamHandler()
# handler.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s", datefmt="%H:%M:%S"))
# logger.addHandler(handler)