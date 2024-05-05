import datetime
import pickle
import socket
from dotenv import dotenv_values

config = dotenv_values(".env")

ENCODING_FORMAT = config["ENCODING_FORMAT"]

class AdministrationMessage:    #Messages sent from the server to the users to make them connect to chatrooms and stuff like that
    sender_id: int
    msg: str
    datetime: datetime.datetime
    obj: object

    def __init__(self, msg: str, obj: object):
        self.sender_id = -1
        self.msg = msg
        self.datetime = datetime.datetime.now()
        self.obj = obj


    def send(self, socket: socket.socket):
        pickled_msg = pickle.dumps(self)
        pickle_length = str(len(pickled_msg)).encode(ENCODING_FORMAT)
        socket.send(pickle_length)
        socket.send(pickled_msg)