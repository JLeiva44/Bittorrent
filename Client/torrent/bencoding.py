# Bencoding is a way to specify and organize data in a terse format. It supports the following types: 
# byte strings, integers, lists, and dictionaries.
from collections import OrderedDict

# Indicates start of integers 
TOKEN_INTEGER = b'i'

# Indicates start of list
TOKEN_LIST = b'l'

# Indicates start of dcit
TOKEN_DICT = b'd'

# Indicates end of lists, dicts and integer 
TOKEN_END = b'e'

# Delimits string length from string data
TOKEN_STRING_SEPARATOR = b':'

class Encoder:
    """Encodes a python object to a bencoded sequence of bytes
    
    Supported python types are:
        -str
        -int
        -list
        -dict
        -bytes
    """
    def __init__(self,data) -> None:
        self._data = data

    def encode(self) -> bytes:  
        """Encode a python object to a bencoded binary string
        : return the bencoded binary data
        """
        return self.encode_next(self._data)

    def encode_next(self, data):  
        if type(data) == str:
            return self._encode_string(data)
        elif type(data) == int:
            return self._encode_int(data)
        elif type(data) == list:
            return self._encode_list(data)
        elif type(data) == dict or type(data) == OrderedDict:
            return self._encode_dict(data)
        elif type(data) == bytes:
            return self._encode_bytes(data)
        else:
            return None # => all other types of data will be ignored
        
    def _encode_int(self,value):
        """
        Integers are encoded as follows: i<integer encoded in base ten ASCII>e
        The initial i and trailing e are beginning and ending delimiters.
        
        i-0e is invalid. All encodings with a leading zero, such as i03e, are invalid, 
        other than i0e, which of course corresponds to the integer "0".
        """
        return str.encode('i' + str(value) + 'e')
    
    def _encode_string(self,value :str):
        """
        strings are encoded as follows: <string length encoded in base ten ASCII>:<string data>
        """
        res = str(len(value) + ':' + value)
        return str.encode(res)
    
    def _encode_bytes(self, value:str):
        result = bytearray()
        result += str.encode(str(len(value)))
        result += b':'
        result += str.encode(value)
        return result
    
    def _encode_list(self,data):
        """
        Lists are encoded as follows: l<bencoded values>e
        The initial l and trailing e are beginning and ending delimiters. 
        Lists may contain any bencoded type, including integers, strings, dictionaries, and even lists within other lists.

        Example: l4:spam4:eggse represents the list of two strings: [ "spam", "eggs" ]
        Example: le represents an empty list: []
        """
        result = bytearray('l','utf-8')
        result += b''.join([self.encode_next(item) for item in data])
        result += b'e'
        return result
    
    def _encode_dict(self, data:dict)->bytes:
        result = bytearray('d', 'utf-8')
        for k,v in data.items:
            key = self.encode_next(k)
            value = self.encode_next(v)
            if key and value:
                result += key
                result += value
            else:
                raise RuntimeError('Bad Dict')

        result += b'e'
        return result        



    
# def _encode_int(value):
#         """
#         Integers are encoded as follows: i<integer encoded in base ten ASCII>e
#         The initial i and trailing e are beginning and ending delimiters.
        
#         i-0e is invalid. All encodings with a leading zero, such as i03e, are invalid, 
#         other than i0e, which of course corresponds to the integer "0".
#         """
#         return str.encode('i' + str(value) + 'e')
    
# data = [1,2,3,4]
# result = bytearray('l','utf-8')
# result += b''.join([_encode_int(item) for item in data])
# result += b'e'
# print(result)