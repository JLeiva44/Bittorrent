import hashlib
import datetime
import os
import math
import bencode
import math
import pickle

class TorrentCreator:
    '''
        Create .torrent file from an input file
    '''
    def __init__(self, path_file: str, piece_size: int, private: bool, trackers_urls, comments: str, source: str):
        self.path_file = path_file
        self.piece_size = piece_size
        self.trackers_urls = trackers_urls
        self.comments = comments
        self.private = private
        self.source = source
    
    @property
    def file_size(self):
        return os.path.getsize(self.path_file) 
    
    @property
    def file_md5sum(self):
        '''
            md5sum of the file calculates and verifies 128-bit MD5 hashes
        '''
        return hashlib.md5(open(self.path_file, 'rb').read()).digest() 
     
    @property
    def filename(self):
        return os.path.basename(self.path_file)


    
    def get_hash_pieces(self):
        '''
            String consisting of the concatenation of all 20-byte SHA1 hash values, one per piece
        '''
        pieces_hash = ''
        with open(f'{self.path_file}', 'rb') as f:
            chunk = f.read(self.piece_size)
            while(chunk):
                pieces_hash += hashlib.sha1(chunk).hexdigest() 
                chunk = f.read(self.piece_size)    

        return pieces_hash
    

    def create_metainfo(self):
        '''
            Create a metainfo file
        '''

        metainfo = {}
        metainfo["announce"] = self.trackers_urls[0]
        metainfo["announce-list"] = self.trackers_urls
        metainfo["info"] = {}
        metainfo["info"]["name"] = self.filename
        metainfo["info"]["length"] = self.file_size
        metainfo["info"]["piece length"] = self.piece_size
        metainfo["info"]["pieces"] = self.get_hash_pieces()
        metainfo["info"]["private"] = self.private
        metainfo["info"]["md5sum"] = self.file_md5sum  # a 32-character hexadecimal string corresponding to the MD5 sum of the file
        metainfo["creation date"] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S").encode('utf-8')
        metainfo["comment"] = self.comments
        metainfo["created by"] = self.source
        return bencode.encode(metainfo)
    
    def create_dottorrent_file(self, folder = '.'):
        '''
            create .torrent file 
        '''
        metainfo = self.create_metainfo()
        
        ftorrent = open(f'{folder}/{os.path.splitext(self.filename)[0]}.torrent', 'wb')
        ftorrent.write(metainfo)
        ftorrent.close()



class TorrentInfo:
    def __init__(self, metainfo):
        '''
            Representation of the Torrent File
            to Download File
        '''
        self.metainfo = dict(metainfo)
        self.file_md5sum = self.metainfo['info']['md5sum']
        self.file_name = self.metainfo['info']['name']
        self.file_size = self.metainfo['info']['length']
        self.piece_size = self.metainfo['info']['piece length']
        self.number_of_pieces = math.ceil(self.file_size/self.piece_size)
        self.dottorrent_pieces = self.metainfo['info']['pieces']
        self.trackers = self.get_trackers()
        #  urlencoded 20-byte SHA1 hash of the value of the info key from the Metainfo file. Note that the value will be a bencoded dictionary, given the definition of the info key above.
        self.info_hash = hashlib.sha1(bencode.encode(self.metainfo['info'])).hexdigest()
        
        
    
    def get_trackers(self):
        '''
            from 'IP: PORT' return  {
                'IP': 'IP',
                'PORT': 'PORT'
            }
        '''
        trackers = []
        for tracker in self.metainfo['announce-list']:
            splited = tracker.split(':')
            trackers.append((splited[0], int(splited[1])))
        return trackers

class TorrentReader:
    
    def __init__(self, dottorrent_path):
        self.dottorrent_path = dottorrent_path
        self.metainfo = self.__read()
    
    def __read(self):
        dottorrent_f =  open(self.dottorrent_path, 'rb')
        contents = dottorrent_f.read()
        metainfo = bencode.decode(contents) 
        dottorrent_f.close()
        return dict(metainfo)
    
    def build_torrent_info(self):
        return TorrentInfo(self.metainfo)