from hashlib import sha1
import bencoding

class Torrent :
    """Represents the torrent meta-data"""

    def __init__(self, torrentfile_path) -> None:
        self.metadata = self._parse_torrentfile(torrentfile_path)
        self.files = []

    def _parse_torrentfile(torrentfile_path):
        t_file = open(torrentfile_path,'rb')
        content = t_file.read()    
        metainfo = decode_dict(content)
        t_file.close()
        return metainfo