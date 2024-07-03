from hashlib import sha1
from . import bencoding
from collections import namedtuple

class TorrentMaker:
    def __init__(self) -> None:
        pass

TorrentFile = namedtuple('File',['name','length'])
class Torrent :
    """Represents the torrent meta-data that is kept within a .torrent file"""

    def __init__(self, file_path) -> None:
        self.file_path = file_path
        self.files = []

        with open(self.torrentfile_path, 'rb') as f:
            meta_info = f.read()
            self.meta_info = bencoding.Decoder(meta_info).decode()
            info = bencoding.Encoder(self.meta_info[b'info']).encode()
            self.info_hash = sha1(info).digest()
            self._identify_files()

    def _identify_files(self):
        """
        Identifies the files included in this torrent
        """
        self.files.append(
            TorrentFile(
                self.meta_info[b'info'][b'name'].decode('utf-8'),
                self.meta_info[b'info'][b'length'])
        )

    @property
    def announce(self):
        """
        The announce URL to the tracker
        """
        return self.meta_info[b'announce'].decode('utf-8')
    
    @property 
    def piece_length(self):
        """
        Get the length in bytes for each piece
        """
        return self.meta_info[b'info'][b'piece length']

    @property 
    def total_size(self):
        """
        The total size (in bytes) for all the files in this torrent. For a
        single file torrent this is the only file, for a multi-file torrent
        this is the sum of all files.

        :return: The total size (in bytes) for this torrent's data.
        """
        return self.files[0].length
    
    @property
    def pieces(self):
        """
        The info pieces is a string representing all pieces SHA1 hashes
        (ecah 20 bytes long).read that data and slice it up into the actual pieces
        """
        data = self.meta_info[b'info'][b'pieces']
        pieces = []
        offset = 0
        length = len(data) 

        while offset < length:
            pieces.append(data[offset:offset+20])
            offset += 20
        return pieces 

    @property
    def output_file(self):
        return self.meta_info[b'info'][b'name'].decode('utf-8')

    def __str__(self):
        return 'Filename: {0}\n' \
               'File length: {1}\n' \
               'Announce URL: {2}\n' \
               'Hash: {3}'.format(self.meta_info[b'info'][b'name'],
                                  self.meta_info[b'info'][b'length'],
                                  self.meta_info[b'announce'],
                                  self.info_hash)


