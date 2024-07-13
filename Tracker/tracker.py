import zmq

HOST = '127.0.0.1'
PORT1 = '8080'
PORT2 = '8001'

class Tracker:
    def __init__(self, ip, port) -> None:
        self.ip = ip
        self.port = port
        self.data = {}
        self._sart_server()



    def _sart_server(self):
        context = zmq.Context()
        p1 = "tcp://"+ self.ip +":"+ self.port # how and where to connect
        socket = context.socket(zmq.REP) # reply socket
        socket.bind(p1)    
        message = socket.recv_pyobj()
        while not message[0] == 'STOP':
            if message[0] == 'REQUEST PEERS':
                pieces = message[1]
                print(pieces)
                print(self.data)
                reply = self.get_clients_for_a_file[pieces]
                socket.send_pyobj(['REPLY PEERS',reply])

            elif message[0] == 'WRITE':
                pieces = message[1]
                ip = message[2]
                port = message[3]
                self.add_client_to_data(pieces,ip, port)
                print("Se anadio un peer ")
                print(self.data)
                socket.send_pyobj(['OK'])

                
            message = socket.recv_pyobj()    ;
                



    def get_clients_for_a_file(self, pieces):
        # OJO aqui en realidad hay que ponerse a buscar x el CHORD y to eso

        return self.data[pieces]

    def add_client_to_data(self,pieces, ip, port):
        try:
            self.data[pieces]
        except KeyError:
            self.data[pieces] = [(ip,port)]
        else:
            self.data[pieces].append((ip,port))

    def remove_client_from_data(self,pieces, ip, port):
        try:
            self.data[pieces]
        except KeyError:
            raise Exception("Esa llave no existe")
        else:
            self.data[pieces].remove((ip,port))




    




tr = Tracker('127.0.0.1', '8080')
#tr.sart_server()
