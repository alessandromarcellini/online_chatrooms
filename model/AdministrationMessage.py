import datetime
import pickle
import socket
from dotenv import dotenv_values

config = dotenv_values(".env")

ENCODING_FORMAT = config["ENCODING_FORMAT"]
HEADER_LENGTH = int(config["HEADER_LENGTH"])

class AdministrationMessage:    #Messages sent from the server to the users to make them connect to chatrooms and stuff like that
    id: int #the type of administration message
    msg: str
    datetime: datetime.datetime
    obj: object

    def __init__(self, msg: str, obj: object):
        self.id = -1
        self.msg = msg
        self.datetime = datetime.datetime.now()
        self.obj = obj


    def send(self, socket: socket.socket):
        pickled_msg = pickle.dumps(self)
        self._send_msg_length(socket, pickled_msg)
        socket.send(pickled_msg)

    def _send_msg_length(self, socket: socket.socket, msg):
        """Adding padding to match the header length"""
        pickle_length = str(len(msg)).encode(ENCODING_FORMAT)
        #add padding
        pickle_length += b' ' * (HEADER_LENGTH - len(pickle_length))
        socket.send(pickle_length)