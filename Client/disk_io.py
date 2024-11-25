import os

class DiskIO:

    @staticmethod
    def build_new_file(path, file_size):
        f = open(path,"wb")
        f.seek(file_size-1)
        f.write(b"\0")
        f.close()

    @staticmethod
    def write_to_disk(path, piece_offset, raw_data):
        new_file = open(path, 'r+b')
        new_file.seek(piece_offset)
        new_file.write(raw_data)
        new_file.close()   


    @staticmethod
    def write_to_disk(path, piece_offset, raw_data):
        new_file = open(path,'r+b')
        new_file.seek(piece_offset)
        new_file.write(raw_data)
        new_file.close()


    @staticmethod
    def read_from_disk(path, piece_offset, piece_size):
        new_file = open(path, 'rb')
        new_file.seek(piece_offset)
        raw_data = new_file.read(piece_size)
        new_file.close()
        return raw_data

    @staticmethod
    def create_folder(path)-> None:
        """Create a Forlder"""

        if not os.path.exists(path):         
            os.mkdir(path)