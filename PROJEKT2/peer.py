import socket
import threading
import argparse

PORT = 65432

class NodeConnection(threading.Thread):
    def __inint__(self, main_node, sock, id, host, port):
        super(NodeConnection, self).__init__()

        self.host = host 
        self.port = port 
        self.main_node = main_node
        self.sock = sock
        self.terminate_flag = threading.Event()
        # variable for parsing incoming messages
        self.buffer = ""      

        # The id of the connected node
        self.id = id 

    def send(self, data):
        try:
            data = data +"-TSN"
            self.sock.sendall(data.encode("utf-8"))
        except Exception as e:
            print("Exception: ", e)
            self.terminate_flag.set()

    def stop(self):
        self.terminate_flag.set()

    def run(self):
        while not self.terminate_flag.is_set():
            line = ""
            try:
                line = self.sock.recv(4069)
            except Exception as e:
                self.terminate_flag.set()
                


            

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    #parser.add_argument("-p")
    parser.add_argument("my_port", type=int, help="Port for this Peer")
    parser.add_argument("connection_port", type=int, help="Port to connect to")
    args = parser.parse_args()

    my_port = args.my_port
    conn_port = args.connection_port
    
    #print(port)

    host = '127.0.0.1'
    node = Peer(host, my_port, conn_port)
