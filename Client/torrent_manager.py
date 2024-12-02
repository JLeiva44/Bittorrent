from torrent_utils import TorrentCreator, TorrentReader
from pieces_manager import PieceManager
from bclient_logger import logger
import base64
import math
import random

class TorrentManager:
    def __init__(self):
        pass

    def upload_torrent(self, path, tracker_urls, private=False, comments="unknown", source="unknown"):
        """Crea un archivo .torrent y lo registra en los trackers."""
        try:
            logger.debug("Creating .torrent file...")
            torrent_maker = TorrentCreator(path, 1 << 18, private, tracker_urls, comments, source)
            sha1_hash = torrent_maker.get_hash_pieces()
            torrent_maker.create_dottorrent_file('torrent_files')

            logger.debug(f".torrent file created with SHA1 hash: {sha1_hash}")
            return sha1_hash  # Devuelve el hash SHA1 para registrar en los trackers
        except Exception as e:
            logger.error(f"Failed to create .torrent file: {e}")
            raise

    def download_torrent(self, dottorrent_file_path, save_at, peer_comm):
        """Descarga un archivo basado en un archivo .torrent."""
        logger.debug("Reading .torrent file and initializing download...")
        reader = TorrentReader(dottorrent_file_path)
        torrent_info = reader.build_torrent_info()

        peers = peer_comm.get_peers_from_tracker(torrent_info)
        piece_manager = PieceManager(torrent_info.metainfo['info'], save_at)

        while not piece_manager.completed:
            rarest_piece, owners = self.find_rarest_piece(peers, torrent_info, piece_manager.bitfield)
            if rarest_piece is None:
                logger.warning("No rarest piece found. Waiting for more peers...")
                break

            for owner in owners:
                try:
                    self.download_piece_from_peer(owner, torrent_info, rarest_piece, piece_manager, peer_comm)
                    break  # Salir del bucle si la descarga es exitosa
                except Exception as e:
                    logger.error(f"Failed to download piece {rarest_piece} from {owner}: {e}")

    def find_rarest_piece(self, peers, torrent_info, owned_pieces):
        """Encuentra la pieza más rara entre los peers disponibles."""
        count_of_pieces = [0] * torrent_info.number_of_pieces
        owners = [[] for _ in range(torrent_info.number_of_pieces)]

        for ip, port in peers:
            request = {"action": "get_bit_field", "info": dict(torrent_info.metainfo['info'])}
            request['info'].pop('md5sum', None)

            response = peer_comm.send_request(request, ip, port)
            if response:
                peer_bit_field = response.get('bitfield', [])
                for i in range(len(peer_bit_field)):
                    if peer_bit_field[i]:
                        count_of_pieces[i] += 1
                        owners[i].append((ip, port))
            else:
                logger.warning(f"No response from peer {ip}:{port} for bit field.")

        # Encuentra la pieza más rara que aún no posees
        rarest_piece = None
        for i, count in enumerate(count_of_pieces):
            if not owned_pieces[i] and count > 0:
                if rarest_piece is None or count < count_of_pieces[rarest_piece]:
                    rarest_piece = i

        return rarest_piece, owners[rarest_piece] if rarest_piece is not None else []

    def download_piece_from_peer(self, peer, torrent_info, piece_index, piece_manager, peer_comm):
        """Descarga una pieza desde un peer específico."""
        try:
            piece_size = (
                torrent_info.file_size % torrent_info.piece_size
                if piece_index == piece_manager.number_of_pieces - 1
                else torrent_info.piece_size
            )
            num_blocks = int(math.ceil(float(piece_size) / piece_manager.block_size))

            for i in range(num_blocks):
                request = {
                    "action": "get_block",
                    "info": dict(torrent_info.metainfo['info']),
                    "piece_index": piece_index,
                    "block_offset": i * piece_manager.block_size
                }
                request['info'].pop('md5sum', None)

                response = peer_comm.send_request(request, peer[0], peer[1])
                if response and 'data' in response:
                    try:
                        raw_data = base64.b64decode(response['data'].encode('utf-8'))
                        piece_manager.receive_block_piece(piece_index, i * piece_manager.block_size, raw_data)
                        logger.debug(f"Successfully downloaded block {i} of piece {piece_index} from {peer}")
                    except Exception as e:
                        logger.error(f"Error decoding/storing block {i} of piece {piece_index}: {e}")
                else:
                    logger.warning(f"Failed to receive block {i} of piece {piece_index} from {peer}")

        except Exception as e:
            logger.error(f"Error downloading piece {piece_index} from {peer}: {e}")
