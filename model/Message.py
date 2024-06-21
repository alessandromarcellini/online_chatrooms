import datetime
import socket
import pickle
from dotenv import dotenv_values

from bson import ObjectId

config = dotenv_values(".env")

ENCODING_FORMAT = config["ENCODING_FORMAT"]
HEADER_LENGTH = int(config["HEADER_LENGTH"])

class Message:
    #sender: UserDetails
    id: ObjectId
    chat_id: ObjectId
    msg: str
    date_time: datetime.datetime
    time: datetime.time
    tags: list#[User]
    #responding_to: Message => can be None
    #img: Image => can be None          TO ADD


    def __init__(self, id, chat_id, sender, msg: str, tags=[], responding_to=None):
        self.id = id
        self.chat_id = chat_id
        self.sender = sender #server_id = -1 => if it is -1 in user check for commands from server. If it is -2 it is a normal message from server
        self.msg = msg
        self.tags = tags
        self.date_time = datetime.datetime.now()
        self.responding_to = responding_to


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