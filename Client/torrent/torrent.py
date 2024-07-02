from hashlib import sha1
import bencodepy


class Torrent :
    """Un torrent es un diccionario con las siguientes claves
    -announce: URL del tracker
    -info: diccionario cuyas claves son independientes de si 1 o mas archivos son compartidos
        -"""

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