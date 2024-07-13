from hashlib import sha1
import bencoding
from collections import namedtuple
import os

class TorrentMaker:
    """
        Create a .torrent file from an input file
    """
    def __init__(self, path, piece_size,trackers_urls, source) -> None:
        self.path = path
        self.piece_size = piece_size
        self.trackers_urls = trackers_urls
        self.source = source

    @property
    def file_size(self):
        return os.path.getsize(self.path)

    @property
    def filename(self):
        return os.path.basename(self.path)
    
    @property
    def pieces(self) -> bytes:
        """
        The info pieces is a string representing all pieces SHA1 hashes
        (ecah 20 bytes long)
        """
        pieces = b''
        with open(f'{self.path}','rb') as f:
            chunk = f.read(self.piece_size)
            while(chunk):
                pieces += sha1(chunk).digest()
                chunk = f.read(self.piece_size)

            return pieces

    def create_metainfo(self):
        """Creates the meta-info bencode dict for a torrent file"""
        metainfo = {}
        metainfo['announce'] = self.trackers_urls[0]
        metainfo['info'] = {}
        metainfo['info']['name'] = self.filename
        metainfo['info']['length'] = self.file_size
        metainfo['info']['pieces'] = self.pieces
        metainfo['info']['piece length'] = self.piece_size
        metainfo['info']['created by'] = self.source
        # ver si despues me hace falta agregar mas cosas 
        # como la fecha, comments, created by ...   
        return bencoding.Encoder(metainfo).encode()     
    
    def create_file(self, folder = '/media/jose/A63C16883C1654211/Proyectos/Bittorrent/Bittorrent/Files'):
        """
        Creates a .torrent file
        """
        metainfo = self.create_metainfo()
        t_file = open(f'{folder}/{os.path.splitext(self.filename)[0]}.torrent','wb')
        t_file.write(metainfo)
        t_file.close() 
    



TorrentFile = namedtuple('File',['name','length'])
class Torrent :
    """Represents the torrent meta-data that is kept within a .torrent file"""

    def __init__(self, file_path) -> None:
        self.file_path = file_path
        self.files = []

        with open(self.file_path, 'rb') as f:
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




# tc = TorrentMaker('Client/torrent',14)
# t = Torrent('Client/torrent/archivo.torrent')
# print(t.piece_length)

# tm = TorrentMaker('Files/file2.txt',262144, ['127.0.0.1:8080'],'EL pepe')
# tm.create_file()