
import Pyro4
import threading
import hashlib

HOST = '127.0.0.1'
PORT1 = '8080'
PORT2 = '8001'

def sha256_hash(s):
    return int(hashlib.sha256(s.encode()).hexdigest(), 16)


class Tracker:
    def __init__(self, ip, port) -> None:
        self.ip = ip
        self.port = port
        self.data = {}
        #self._sart_server()
        #threading.Thread(target=self._start_server, daemon=True).start()  # Start server thread

    def connect_to(self, ip, port, type_of_peer):
        ns = Pyro4.locateNS()
        # by default all peers, including tracker are registered in the name server as type_of_peerIP:Port
        uri = ns.lookup(f"{type_of_peer}{ip}:{port}")
        proxy = Pyro4.Proxy(uri=uri)

        # try:
        #     tracker_proxy._pyroConnection.ping()
        #     print(f"Succefuly connection with the TRACKER at {tracker_ip}:{tracker_port}")
        # except Pyro4.errors.CommunicationError:
        #     print("TRACKER Unreachable")

        return proxy

    @Pyro4.expose
    def add_to_trackers(self, pieces_sha1, ip, port):
        pieces_sha256 = sha256_hash(pieces_sha1)
        if self.successor == '':
            self.add_to_database(pieces_sha256, ip, port)
        else:
            tracker_ip, tracker_port = self.find_successor(pieces_sha256).split(':')
            proxy_tracker = self.connect_to(tracker_ip, int(tracker_port), 'tracker')
            proxy_tracker.add_to_database(pieces_sha256, ip, port)




tracker = Tracker("127.0.0.1", 6200)

daemon = Pyro4.Daemon(host=tracker.ip, port= tracker.port)
ns = Pyro4.locateNS()
uri = daemon.register(tracker)
ns.register(f"tracker{tracker.ip}:{tracker.port}", uri)
print(f"TRACKER {tracker.ip}:{tracker.port} STARTED")
daemon.requestLoop()
