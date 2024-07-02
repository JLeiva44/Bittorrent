from hashlib import sha1
from hashlib import md5
import bencodepy
import datetime
import os

class TorrentCreator:
    def __init__(self,file_path, piece_size, private, announce_list, comments, source) -> None:
        self.file_path = file_path
        self.piece_size = piece_size
        self.announce_list = announce_list
        self.comments = comments
        self.private = private
        self.source = source
        self.file_size = os.path.getsize(self.file_path)
        self.md5sum = md5(open(self.file_path,'rb').read()).digest()
        self.file_name = os.path.basename(self.file_path)

    @property 
    def hash_pieces():
        pass 

    def make_metainfo(self):
        pass

    def make_torrentfile(self):
        pass   

   
        

class Torrent :
    """ A class that represents a Torrent file data"""

    def __init__(self, torrentfile_path) -> None:
        self.torrentfile_path = torrentfile_path
        self.metadata = TorrentMetadata(self._parse_torrentfile())
        self.info = self.metadata.info
        self.files = []

    def _parse_torrentfile(self):
        t_file = open(self.torrentfile_path,'rb')
        content = t_file.read()    
        metainfo = bencodepy.decode(content)
        t_file.close()
        return metainfo
    
    @property
    def announce(self) -> str:
        """
        The announce URLs of the tracker(s)
        """
        return self.metadata[b'announce']
    
    @property
    def announce_list(self)-> list:
        trackers = []
        for tracker in self.metadata[b'announce-list']:
            splited = tracker.split(b':')
            trackers.append((splited[0], int(splited[1])))
        return trackers    
    
    # def __str__(self):
    #     return 'Filename: {0}\n' \
    #            'File length: {1}\n' \
    #            'Announce URL: {2}\n' \
    #            'Hash: {3}'.format(self.meta_info[b'info'][b'name'],
    #                               self.meta_info[b'info'][b'length'],
    #                               self.meta_info[b'announce'],
    #                               self.info_hash)
    

t = Torrent("/media/jose/A63C16883C1654211/Proyectos/Bittorrent/Bittorrent/Client/torrent/archivo.torrent")
print(t.metadata)    

class TorrentMetadata:
    def __init__(self, metadata) -> None:
        self.announce = metadata[b'announce'] # URL del tracker
        self.announce_list = metadata[b'announce-list']
        self.comment = metadata[b'comment']
        self.created_by = metadata[b'created by']
        self.creation_date = metadata[b'creation date']
        self.info = TorrentInfo(metadata[b'info'])
        

class TorrentInfo:   
    def __init__(self, info) -> None:
        self.length = info[b'length'] # tamano del archivo en bytes
        self.md5sum = info[b'md5sum']
        self.name = info[b'name']
        self.piece_length = info[b'piece length'] # numero de bytes x pieza
        self.pieces = info[b'pieces'] # una lista de hash. Concatenacion de cada hash SHA1 de las piezas
        self.private = info[b'private']
        self.info_hash = sha1(bencodepy.encode(info)).hexdigest() 


p = TorrentMetadata(t.metadata)
print(p.announce)        