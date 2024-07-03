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

class Decoder:
    """
    Decodes a bencoded sequence of bytes
    """
    def __init__(self, data:bytes) -> None:
        if not isinstance(data, bytes):
            raise TypeError('Argument "data" must be of type bytes')
        self._data = data
        self._index = 0

    def decode(self):
        """
        Decodes the bencoded data and returns the matching python object
        """
        c = self._peek()
        if c is None :
            raise EOFError('Unespected end of file')
        elif c == TOKEN_INTEGER:
            self._consume()
            return self._decode_int()
        elif c == TOKEN_LIST:
            self._consume()
            return self._decode_list()
        elif c == TOKEN_DICT:
            self._consume()
            return self._decode_dict()
        elif c == TOKEN_END:
            return None
        elif c in b'01234567899':
            return self._decode_string()
        else:
            raise RuntimeError('Invalid token at {0}'.format(str(self._index)))

    def _peek(self):
        """
        Return the next character from the bencoded data or None
        """
        if self._index +1 >= len(self._data):
            return None
        return self._data[self._index:self._index+1]
    
    def _consume(self):
        self._index +=1

    def _read(self, length):
        """
        Read the 'length' number of bytes from data and return the result
        """    
        if self._index + length > len(self._data):
            raise IndexError('Cannot read {0} bytes from current position {1}'.format(str(length), str(self._index)))
        res = self._data[self._index:self._index+length]
        self._index += length
        return res
    
    def _read_until(self, token):
        """
        Read from the bencoded data until the given token is found and returns the characters read.
        """
        try:
            occurrence = self._data.index(token, self._index)
            result = self._data[self._index:occurrence]
            self._index = occurrence +1
            return result
        except ValueError:
            raise RuntimeError('Unable to find token {0}'.format(str(token)))
        
    def _decode_int(self):
        return int(self._read_until(TOKEN_END))    
    
    def _decode_list(self):
        res = []
        # recursive decode the content of the list
        while self._data[self._index:self._index+1]!= TOKEN_END:
            res.append(self.decode())
        self._consume() #The END token
        return res

    def _decode_dict(self):
        res = OrderedDict()    
        while self._data[self._index: self._index + 1] != TOKEN_END:
            key = self.decode()
            obj = self.decode()
            res[key] = obj
        self._consume()  # The END token
        return res
    
    def _decode_string(self):
        bytes_to_read = int(self._read_until(TOKEN_STRING_SEPARATOR))
        data = self._read(bytes_to_read)
        return data





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
        res = str(len(value)) + ':' + value
        return str.encode(res)
    
    def _encode_bytes(self, value:str):
        result = bytearray()
        result += str.encode(str(len(value)))
        result += b':'
        #result += str.encode(value)
        result += value
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
        """
        Dictionaries are encoded as follows: d<bencoded string><bencoded element>e
        """
        result = bytearray('d', 'utf-8')
        for k,v in data.items():
            key = self.encode_next(k)
            value = self.encode_next(v)
            if key and value:
                result += key
                result += value
            else:
                raise RuntimeError('Bad Dict')

        result += b'e'
        return result        


