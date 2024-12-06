from torrent_utils import TorrentCreator, TorrentReader, TorrentInfo
from pieces_manager import PieceManager
from block import State, DEFAULT_Block_SIZE, Block
from bclient_logger import logger
import random
import base64
import math
PIECE_SIZE =  2**18 # 256 Kb (kilobibits) = 262144 bits

class TorrentManager:
    def __init__(self, peer_comm, tracker_handler):
        self.peer_comm = peer_comm
        self.tracker_handler = tracker_handler

    def upload_file(self, path, tracker_urls, private, comments, source):
        """Sube un archivo y actualiza trackers."""
        torrent_creator = TorrentCreator(path, PIECE_SIZE, private, tracker_urls, comments, source)
        sha1 = torrent_creator.get_hash_pieces()
        torrent_creator.create_dottorrent_file('torrent_files')

        trackers = [tuple(url.split(':')) for url in tracker_urls]
        for tracker_ip, tracker_port in trackers:
            self.tracker_handler.update_tracker(tracker_ip, tracker_port, sha1)

    def download_file(self, dottorrent_file_path, save_at):
        """Descarga un archivo usando el archivo .torrent."""
        tr = TorrentReader(dottorrent_file_path)
        torrent_info = tr.build_torrent_info()
        peers = self.tracker_handler.get_peers_from_tracker(torrent_info)
        # Aquí puedes delegar más lógica al `PieceManager`
        piece_manager_inst = PieceManager(torrent_info.metainfo['info'], save_at)

        trackers = torrent_info.get_trackers()
        for tracker_ip, tracker_port in trackers:
            self.tracker_handler.update_tracker(tracker_ip, tracker_port, torrent_info.dottorrent_pieces)

        # Descargar las piezas
        while not piece_manager_inst.completed:
            rarest_piece, owners = self.find_rarest_piece(peers, torrent_info, piece_manager_inst.bitfield)
            while owners:
                peer_for_download = random.choice(owners)
                owners.remove(peer_for_download)
                piece_manager_inst.clean_memory(rarest_piece)
                try:
                    self.download_piece_from_peer(peer_for_download, torrent_info, rarest_piece, piece_manager_inst)
                except Exception as e:
                    logger.error(f"Error downloading piece {rarest_piece} from {peer_for_download}: {e}")

                break    



    def find_rarest_piece(self, peers, torrent_info: TorrentInfo, owned_pieces):
        logger.debug(f"Pers en finrerestpiece {peers}")
        count_of_pieces = [0] * torrent_info.number_of_pieces
        owners = [[] for _ in range(torrent_info.number_of_pieces)]

        
        for ip, port in peers:
            request = {
                    "action": "get_bit_field",
                    "info": dict(torrent_info.metainfo['info'])
                }
            request['info'].pop('md5sum')
            response = self.peer_comm._send_data(request,ip,port)
            
            if response:
                peer_bit_field = response.get('bitfield', [])
                for i in range(len(peer_bit_field)):
                    if peer_bit_field[i]:
                        count_of_pieces[i] += 1
                        owners[i].append((ip, port))

            else :
                logger.warning(f"No response from peer {ip}:{port} for bit field.")

        # encuentra la pieza mas rara        
        rarest_piece = -1
        for i, count in enumerate(count_of_pieces):
            if not owned_pieces[i] and count > 0:
                if rarest_piece == -1 or count < count_of_pieces[rarest_piece]:
                    rarest_piece = i

        return rarest_piece, owners[rarest_piece] if rarest_piece != -1 else []
            
    def download_piece_from_peer(self, peer, torrent_info: TorrentInfo, piece_index: int,
                              piece_manager: PieceManager):
        
        try:
            piece_size = (
                torrent_info.file_size % torrent_info.piece_size
                if piece_index == piece_manager.number_of_pieces - 1
                else torrent_info.piece_size
            )
            
            num_blocks = int(math.ceil(float(piece_size) / DEFAULT_Block_SIZE))

            for i in range(num_blocks):
                request = {
                    "action": "get_block",
                    "info": dict(torrent_info.metainfo['info']),
                    "piece_index": piece_index,
                    "block_offset": i * DEFAULT_Block_SIZE
                }
                request['info'].pop('md5sum', None)

                response = self._send_data(request, peer[0], peer[1])

                if response and 'data' in response:
                    try:
                        # Decodificar el bloque recibido
                        raw_data = base64.b64decode(response['data'].encode('utf-8'))
                        piece_manager.receive_block_piece(piece_index, i * DEFAULT_Block_SIZE, raw_data)
                        logger.debug(f"Successfully downloaded block {i} of piece {piece_index} from {peer}")
                    except Exception as e:
                        logger.error(f"Error decoding/storing block {i} of piece {piece_index} from {peer}: {e}")
                else:
                    logger.warning(f"Failed to receive block {i} of piece {piece_index} from {peer}")

        except Exception as e:
            logger.error(f"Error downloading piece {piece_index} from {peer}: {e}")
        
    def get_block_of_piece(self, info: dict, piece_index: int, block_offset: int):
        try:
            piece_manager = PieceManager(info, 'client_files')
            block = piece_manager.get_block_piece(piece_index, block_offset)

            # Asegurarse de que los datos estén codificados en Base64
            return {"data": base64.b64encode(block.data).decode('utf-8')}
        except Exception as e:
            logger.error(f"Error retrieving block {block_offset} of piece {piece_index}: {e}")
            return {"error": "Failed to retrieve block"}
            # piece_manager = PieceManager(info['info'], 'Client/client_files')
            # return {"data": piece_manager.get_block_piece(piece_index, block_offset).data}   
    
    