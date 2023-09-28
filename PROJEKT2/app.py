import argparse
import itertools
import json
import random
import os
import pickle
import sys
import threading
import time
from PIL import Image
import customtkinter
from tkinter import filedialog as fd
from CTkTable import *
import numpy as np
import socket
import sympy
from elgamal import Gamal

from helper import p2p, ServerRunning, Message
from server import StartGenesisNode
from node import Peer


class App2(customtkinter.CTk):
    def __init__(self):
        super().__init__()

        customtkinter.set_appearance_mode("System")
        customtkinter.set_default_color_theme("blue")

        self.title("File Transfer")
        self.geometry("600x400")
        self.resizable(0,0)

        self.home_frame = customtkinter.CTkFrame(self, corner_radius=0, fg_color="transparent")
        self.home_frame.grid(row=0, column=1, sticky="nsew")

        self.send_frame = customtkinter.CTkFrame(self, corner_radius=0, fg_color="transparent")
        self.receive_frame = customtkinter.CTkFrame(self, corner_radius=0, fg_color="transparent")
        
         # load images
        image_path = os.path.join(os.getcwd(), "images")
        self.home_image = customtkinter.CTkImage(dark_image=Image.open(os.path.join(image_path, "home_light.png")), size=(20,20,))

        self.filename = ""
        self.elgamal = Gamal()
        #self.my_public_key = self.elgamal.h
        self.file_format = ""
        self.new_filename = ""
        self.packet_number = ""
        self.total_packets = ""

        self.flag = True

        self.active = threading.Event()
    

        self.prime_number_q = 911
        self.prime_number_p = 2*self.prime_number_q + 1

        self.protocol("WM_DELETE_WINDOW", self.on_closing)

        
        def send_button_function():
            self.home_frame.grid_forget()
            self.send_frame.grid(row=0, column=1, sticky="nsew")
            print("Go to send Frame")
            

        def receive_button_function():
            if Message.message_ready == True:
                self.home_frame.grid_forget()
                self.receive_frame.grid(row=0, column=1, sticky="nsew")
                print("Go to receive Frame")
                receive_file_button = customtkinter.CTkButton(self.receive_frame, text="Get File", command=receive_message)
                receive_file_button.grid(row=3, column=1, padx=180, pady=40)
            else:
                print("[*] Not enough linear combinations to recover the file")
            
            
        def back_to_home_from_S():
            #self.send_frame.grid_forget()
            self.send_frame.destroy()
            self.home_frame.grid(row=0, column=1, sticky="nsew")

        def back_to_home_from_R():
            self.receive_frame.grid_forget()
            self.home_frame.grid(row=0, column=1, sticky="nsew")
        
        def open_file():
            filetypes = (('text files', '*.txt'), ('All files', '*.*'))
            # select one or more files
            self.filename = fd.askopenfilename(filetypes=filetypes)
            
            #change label content
            label_file_explorer.destroy()
            #label_file_explorer.configure(text="File Opened: "+filename)

            if self.filename:
                display_file(self.filename)

        def display_file(filepath):
            filename = os.path.basename(filepath)
            size = os.path.getsize(filepath)
            file_format = os.path.splitext(filepath)[1]
            self.file_format = file_format
            self.new_filename = filename

            data = [["Name", "Size (bytes)", "Format"],
                    [filename, size, file_format]]

            table = CTkTable(master=self.send_frame, row=len(data), column=3, values=data)
            table.grid(row=1, column=1, padx=10, pady=30)

            #send_button = customtkinter.CTkButton(self.send_frame, text="Send", command=send_file_to_all_peers)
            # place send button
            send_button.grid(row=2, column=1, padx=10, pady=10)


        def split_file_into_packets(file_path, packet_size):
            packets = []
    
            with open(file_path, 'rb') as file:
                while True:
                    packet = file.read(packet_size)
                    if not packet:
                        break
                    packets.append(packet)
    
            return packets
        
        def pad_packets(packets, target_size):
            padded_packets = []
            for packet in packets:
                if len(packet) < target_size:
                    padding = bytes([1] * (target_size - len(packet)))
                    padded_packet = packet + padding
                    padded_packets.append(padded_packet)
                else:
                    padded_packets.append(packet)
            return padded_packets
        
        def unpad_packets(padded_packets):
            unpadded_packets = []
            for packet in padded_packets:
                # Remove Padding. Remove the Nullbytes at the end
                unpadded_packet = packet.rstrip(b'\x01')
                unpadded_packets.append(unpadded_packet)
            return unpadded_packets
        
        def join_packets(packets):
            return b''.join(packets)
            

        def send_message():
            """ send the encrypted packets to the connected peers
                1. split the file in equally sized packets
                2. encrypt all packets using elgamal encryption
                3. Send the encrypted packets out

            """
            packet_size = 128
            packets = split_file_into_packets(self.filename, packet_size)
            padded_packets = pad_packets(packets, packet_size)

            # Encrypt every package using elgamal encryption and send them through the network
            for i in range(0, len(padded_packets)):
                c1, c2 = self.elgamal.encryption(padded_packets[i])
                #print("ENC:  ", (c1, c2))
                send_formated({"PACKET": (c1, c2), "LC": 0, "key": self.elgamal.private_key, "p": self.elgamal.p, "format": self.file_format, "N": len(padded_packets)}, i, len(padded_packets))
                time.sleep(0.2)

        def send_formated(message, number, total):
            """ Prepare the message before sending it.
                Use pickle and a fixec HEADERSIZE for better handling and
                to know the length of the packet
            """
            serialized_message = pickle.dumps(message)
            HEADERSIZE = 10
            serialized_message = bytes(f"{len(serialized_message):<{HEADERSIZE}}", 'utf-8')+serialized_message
            if len(p2p.connections) != 0:
                for p in p2p.connections:
                    try:
                        p.send(serialized_message)
                        print(f"[*] Sended packet successfully {number+1} / {total}")
                    except:
                        print(f"[*] Failed to send message")

        def receive_message():
            """ Write the collected packets to a file.
                Convert them back to byte representation
            """
            #print(Message.message)
            s = list(itertools.chain.from_iterable(Message.message))
            res = []
            file = []
            for i in range(0, len(s)):
                res.append(int.to_bytes(s[i], 1, 'big'))
            st = b''.join(res)
            file.append(st)

            unpadded_packets = unpad_packets(file)
            reconstruct_data = join_packets(unpadded_packets)
            #print(reconstruct_data)

            new_file = "Received_file"+Message.format

            with open(new_file, "wb") as file:
                file.write(reconstruct_data)

            print("[*] Data has successfull been written to the file")
           


        def send_file_to_all_peers():
            send_message()
            # After the message was sended destroy the button
            #send_button.destroy()
            #file_sended.grid(row=1, column=1, padx=180, pady=40)

            



        # Home frame
        self.button = customtkinter.CTkButton(self.home_frame, text="Send", command=send_button_function)
        self.button.grid(row=0, column=0, padx=80, pady=200)
        self.button2 = customtkinter.CTkButton(self.home_frame, text="Receive", command=receive_button_function)
        self.button2.grid(row=0, column=1, padx=80, pady=200)

        self.ip = socket.gethostname()

        # Send Frame
        self.back_button_send = customtkinter.CTkButton(self.send_frame, text="",image=self.home_image, command=back_to_home_from_S,
                                                        fg_color="transparent", width=20, font=customtkinter.CTkFont(size=30))
        self.back_button_send.grid(row=0, column=0)
        label_file_explorer = customtkinter.CTkLabel(self.send_frame, text="No file selected", width=100, height=4)
        label_file_explorer.grid(row=1, column=1, padx=180, pady=40)
        self.open_file_button = customtkinter.CTkButton(self.send_frame, text="Open File", command=open_file)
        self.open_file_button.grid(row=3, column=1, padx=180, pady=40)

        send_button = customtkinter.CTkButton(self.send_frame, text="Send", command=send_file_to_all_peers)
        #send_button.grid(row=2, column=1, padx=10, pady=10)

        # Receive Frame
        self.back_button_receive = customtkinter.CTkButton(self.receive_frame, text="",image=self.home_image, command=back_to_home_from_R,
                                                        fg_color="transparent", width=20, font=customtkinter.CTkFont(size=30))
        self.back_button_receive.grid(row=0, column=0)
        #self.receive_file_button = customtkinter.CTkButton(self.receive_frame, text="Get File", command=receive_message)
        #self.receive_file_button.grid(row=3, column=1, padx=180, pady=40)
        file_sended = customtkinter.CTkLabel(self.send_frame, text="No file selected", width=100, height=4)
        #file_sended.grid(row=3, column=1, padx=180, pady=40)


        
    def on_closing(self):
        print("Destroy GUI")
        p2p.stop = True
        self.flag = False
        self.destroy()
        self.active.set()
        #quit()


def foreground():
    global app
    app = App2()
    app.mainloop()

def background(port):
    print("[*] Connecting to the Network")
    # Start Genisis Node (Server)
    time.sleep(3)
    if port is not None:
        # we have a port to connect to
        Peer('127.0.0.1', port)
    else:
        StartGenesisNode()
     
if __name__=="__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("connection_port", type=int, help="Port to connect to (up to 3)", nargs="?", default=None)
    args = parser.parse_args()

    conn_port = args.connection_port
    b = threading.Thread(name="background", target=background, args=(conn_port,))
    f = threading.Thread(name="foreground", target=foreground)
    #b.daemon = True
    f.start()
    b.start()

    