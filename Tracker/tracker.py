import zmq

HOST = '127.0.0.1'
PORT1 = '8080'
PORT2 = '8001'

class Tracker:
    def __init__(self, ip, port) -> None:
        self.ip = ip
        self.port = port
        self.data = {}

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




    # def sart_server(self):
    #     print("Inicio el servidor")
    #     context = zmq.Context()
    #     p1 = "tcp://"+ HOST +":"+ PORT2 # how and where to connect
    #     socket = context.socket(zmq.REP) # reply socket
    #     socket.bind(p1)    
    #     print("Bindeo a " + p1)
    #     while True:
    #         message = socket.recv_pyobj()
    #         print(message)
    #         if not "STOP" in str(message):
    #             print("El mensaje es :" )
    #             #reply = str(message.decode())+'*'
    #             reply = message
    #             print(reply)
    #             #socket.send(reply.encode())
    #             socket.send_pyobj(reply)

    #         else:
    #             break




tr = Tracker('127.0.0.1', '8080')
tr.sart_server()
