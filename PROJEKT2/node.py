import sys
import socket
import threading
import time
import pickle
import ast
import numpy as np
import json
import sympy
import itertools
import random

from helper import p2p, ServerRunning, Message
from elgamal import Gamal

HEADERSIZE = 10

class Peer:
    def __init__(self, addr, port):
        self.s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            self.s.connect((addr, port))
        except ConnectionRefusedError:
            print("No Node with that Address")
            sys.exit()
        p2p.connections.append(self.s)


        self.myIP = self.s.getsockname()
        print(f"[*] My Address: {self.myIP}")

        # Check if I am a intermediate Node and need to send
        # linear combinations of packets
        self.intermediate_node = False

        self.c = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.c.setsockopt(socket.SOL_SOCKET, socket.SOCK_STREAM, 1)
        self.c.bind(self.myIP)
        self.c.listen(10)
        
        self.connections = []
        self.packet_buffer = []
        self.lc_puffer = []

        self.elgamal = Gamal()
        self.elgamal_key = 0
        self.file_format = ""
        self.number_of_packets_1 = 0
        self.number_of_packets_2 = 0

        self.matrix = []

        self.dec_list = []
        
        c_thred = threading.Thread(target=self.handle2)
        c_thred.daemon = True
        c_thred.start()
        
        while True:
            # listen for incomming connections
            conn, a = self.c.accept()
            thread = threading.Thread(target=self.handle, args=(conn, a))
            thread.daemon = True
            thread.start()
            self.connections.append(conn)
            p2p.connections.append(conn)
            print("[*] New connetion FROM ", a)

            # Check for intermediate (at least two incomming connections)
            # If connection len(list) >= 3, (2 incomming, 1 outcomming)
            if len(p2p.connections) >= 3:
                self.intermediate_node = True


    def send_linear_combinations(self, conn):
        """ Send the linear combinations of the sofar collected encrypted packets
            In the "self.packer_buffer" are the collected packets.
            If we have a list of 4 packets, we need to create 4 different linear combinations
            and send them all out.
        """
        packets = self.packet_buffer
        for i in range(0, len(packets)):
            c1, c2, x = self.compute_linear_combinations(packets)
            linear_combination = {"PACKET": (c1, c2), "exponents": x, "LC": 1, "key": self.elgamal.private_key, "p": self.elgamal.p, "format": self.file_format, "LC_Num": self.number_of_packets_1+self.number_of_packets_2}
            serialized_message = pickle.dumps(linear_combination)
            serialized_message = bytes(f"{len(serialized_message):<{HEADERSIZE}}", 'utf-8')+serialized_message
            for p in p2p.connections:
                try:
                    if p != self.s and p != conn:
                        p.send(serialized_message)
                        time.sleep(0.1)
                except:
                    print("Failed to send LC")


    def compute_linear_combinations(self, packets):
        """ Compute the linear combinations of the sofar collected encrypted packages
            (It only computes one combination)
            
            1. Take every element from the list to the power of a random integer r
               [(c1_1,c2_1), (c1_2,c2_2),...,(c1_n, c2_n)] => [(c1_1,c2_1)^a, (c1_2,c2_2)^b,...,(c1_n, c2_n)^n]
            
            2. Multiply every component of the list
               C1_1^a * c1_2^b * ... * c1_n^n
               c2_1^a * c2_2^b * ... * C2_n^n
            
            3. Return the new list with the linear combination and the used exponents
        """
        exp_list = []
        e = []
        c1 = 1
        p = self.elgamal.p
        for i in range(0, len(packets)):
            r = random.randint(2, 9)
            exponent_list = [sympy.Pow(x,r) % p for x in packets[i][1]]
            c1 *= sympy.Pow(packets[i][0], r) % p 
            c1 = c1 % p 
            exp_list.append(exponent_list)
            e.append(r)
        res = exp_list[0]
        for sublist in exp_list[1:]:
            res = [(a * b) % p for a,b in zip(res, sublist)]
        return c1, res, e


                
    def recalculate_result(self, lc, matrix, p):
        """ Recalculate the original message based in linear combinations
            1. decrypt every package
            2. compute the matrix inverse modulo q
            3. Use matrix multiplication to get the messages
        
        """
        dec = [self.elgamal.decryption(lc[i][0], lc[i][1], self.elgamal.private_key) for i in range(len(lc))]
        #print("DEC:  ", dec)
        m = sympy.Matrix(matrix)
        matrix_inverse = m.inv_mod(self.elgamal.q)
        #print("INVERSE MATRIX: ", matrix_inverse)
        X = self.calculate_results(dec, matrix_inverse, p)
        return X
    

    def calculate_results(self, lc_list, B, p):
        """ Inverse matrix multiplication
                -> lc[0]**B[0][0] * lc[1]**B[0][1] * ... * lc[0]**B[0][n]  = m1
                   lc[1]**B[1][0] * lc[1]**B[1][1] * ... * lc[1]**B[1][n]  = m2
                                ....                            ....
                   lc[n]**B[n][0] * lc[1]**B[n][1] * ... * lc[n]**B[n][n]  = m_n

            1. Take every element from the list to the power of the corresponding element from the inverse matrix
            2. Multiply every corresponding element
            3. Return a list with the original messages
        
        """
        final_res = []
        mat = np.array(B)
        for i in range(0, len(lc_list)):
            res = []
            for j in range(0, len(lc_list)):
                r = [sympy.Pow(x, mat[i][j]) % p for x in lc_list[j]]
                res.append(r)
            t = res[0]
            result = []
            for sublist in res[1:]:
                t = [(a * b) % p for a,b in zip(t, sublist)]
            t = [p - x if x > 256 else x for x in t] # Sometimes the bigger values are represented
            result.append(t)
            result = list(itertools.chain.from_iterable(result))
            final_res.append(result)
        return final_res


    def decode_linear_combinations(self, message):
        """ We have a message that is a linear combinatiom, so we need to decode that message
            We also have the exponents used for that specific message

            1. Collect all the exponents in a matrix
                    -> If we have 3 exponents, that means we need at least 3 linear combinations to successfully decode the original message
                    -> So we need to wait for the other messages and exponets

            2. If we have all messages corresponding to the expontnts, we can look if we have enough combinations to decrypt the whole message
                -> If we have 4 messages in total from all peers, we need a 4 x 4 matrix
                -> So if we just have 2 messages we have a 2 x 2 matrix and not enough to decrypt the whole message
                -> Compute the rank of the matrix, if the rang % q = n we have enough
            
            3. If we have enough combinations we can decode it
        
        """
        ma = message["exponents"]
        self.matrix.append(ma)
        
        if len(ma) > len(self.matrix[0]):
            for i in range(0, len(self.matrix[0])):
                self.matrix.pop(0)
            self.lc_puffer = []
        self.lc_puffer.append(message["PACKET"])
        print(f"MATRIX: {self.matrix}")
        ma = np.array(self.matrix)
        rank = np.linalg.matrix_rank(ma)
        total_number = message["LC_Num"]
        #print("TOTAL NUMBER", total_number)
        if rank % self.elgamal.q == total_number:
            #print("WE HAVE ENOUGH")
            #print("LC_PUFFER: ", self.lc_puffer)
            Message.message = self.recalculate_result(self.lc_puffer, self.matrix, self.elgamal.p)
            Message.message_ready = True
            #print(X)
            # Message.message....


    def handle2(self):
        """ Handle the First connnetion with another peer.
            Retrieve every packet and consider what to do with it

            Options:
                1. We have an linear combination (lc = 1) which means we need to decode it
                2. We are not a intermediade node 
                    -> Just collect the packets, decrypt them and if all packets are decrypted we can download the file 
                    -> Also just send the received packets as they are to all connected peers
                3. We are a intermediade node
                    -> We need to collect the packages and create linear combinations of them 
                    -> After creating the linear packages, send them to all connected peers
        
        """
        try:
            full_msg = b''
            new_msg = True
            while True:
                msg = self.s.recv(16)
                if new_msg:
                    msglen = int(msg[:HEADERSIZE])
                    new_msg = False
                full_msg += msg
                    
                if len(full_msg)-HEADERSIZE == msglen:
                    message = pickle.loads(full_msg[HEADERSIZE:])
                    new_msg = True
                    full_msg = b''

                    print(f"Message from {self.s.getpeername()}")
                    is_lc = message["LC"]

                    if is_lc == 1:
                        # We have a linear combination
                        self.decode_linear_combinations(message)
                    
                    
                    elif self.intermediate_node == False:
                        # just keep sending normal packets
                        number_packets = message["N"]
                        serialized_message = pickle.dumps(message)
                        serialized_message = bytes(f"{len(serialized_message):<{HEADERSIZE}}", 'utf-8')+serialized_message
                        decrypt = self.elgamal.decryption(message["PACKET"][0], message["PACKET"][1], self.elgamal.private_key)
                        self.dec_list.append(decrypt)
                        if len(self.dec_list) == number_packets:
                            # We have all messages
                            Message.format = message["format"]
                            Message.message = self.dec_list
                            Message.message_ready = True
                        for p in p2p.connections:
                            if p != self.s:
                                p.send(serialized_message)
                                time.sleep(0.1)
                        
                    elif self.intermediate_node == True:
                        number = message["N"]
                        self.number_of_packets_1 = number
                        self.elgamal_key = message["key"]
                        self.file_format = message["format"]
                        self.packet_buffer.append(message['PACKET'])
                        self.send_linear_combinations(self.s)
        except OSError:
            print(f"Peer {self.s} disconncted")
        
    def handle(self, conn, a):
        """ Handle the all connections (execpt the First).
            Retrieve every packet and consider what to do with it

            Options:
                1. We have an linear combination (lc = 1) which means we need to decode it
                2. We are not a intermediade node 
                    -> Just collect the packets, decrypt them and if all packets are decrypted we can download the file 
                    -> Also just send the received packets as they are to all connected peers
                3. We are a intermediade node
                    -> We need to collect the packages and create linear combinations of them 
                    -> After creating the linear packages, send them to all connected peers
        """
        try:
            full_msg = b''
            new_msg = True
            while True:
                msg = conn.recv(16)
                if new_msg:
                    msglen = int(msg[:HEADERSIZE])
                    new_msg = False
                full_msg += msg
                    
                if len(full_msg)-HEADERSIZE == msglen:
                    message = pickle.loads(full_msg[HEADERSIZE:])
                    new_msg = True
                    full_msg = b''

                    print(f"Nachricht von {a}")
                    #print(message)
                    is_lc = message["LC"]
                    if is_lc == 1:
                        # We have a linear combination
                        self.decode_linear_combinations(message)


                    elif self.intermediate_node == False:
                        # just keep sending normal packets
                        number_packets = message["N"]
                        serialized_message = pickle.dumps(message)
                        serialized_message = bytes(f"{len(serialized_message):<{HEADERSIZE}}", 'utf-8')+serialized_message
                        decrypt = self.elgamal.decryption(message["PACKET"][0], message["PACKET"][1], self.elgamal.private_key)
                        self.dec_list.append(decrypt)
                        if len(self.dec_list) == number_packets:
                            # We have all messages
                            Message.format = message["format"]
                            Message.message = self.dec_list
                            Message.message_ready = True
                        for p in p2p.connections:
                            if p != conn:
                                p.send(serialized_message)
                                time.sleep(0.1)
                    
                    elif self.intermediate_node == True:
                        number = message["N"]
                        if number != self.number_of_packets_2:
                            self.number_of_packets_2 += number
                        #print("NUMBER_2:  ", self.number_of_packets_2)
                        self.elgamal_key = message["key"]
                        self.file_format = message["format"]
                        self.packet_buffer.append(message['PACKET'])
                        self.send_linear_combinations(conn)

        except OSError as e:
            print(f"Peer {conn} disconnected")
