import datetime
import socket
import pickle
from dotenv import dotenv_values

config = dotenv_values(".env")

ENCODING_FORMAT = config["ENCODING_FORMAT"]

class Message:
    #sender_id: User.id
    id: int
    chat_id: int
    msg: str
    datetime: datetime.datetime
    tags: list#[User]
    #responding_to: Message => can be None
    #img: Image => can be None          TO ADD


    def __init__(self, id, chat_id, sender_id, msg: str, tags=[], responding_to=None):
        self.id = id
        self.chat_id = chat_id
        self.sender_id = sender_id #server_id = -1 => if it is -1 in user check for commands from server. If it is -2 it is a normal message from server
        self.msg = msg
        self.tags = tags
        self.responding_to = responding_to


    def send(self, socket: socket.socket):
        pickled_msg = pickle.dumps(self)
        pickle_length = str(len(pickled_msg)).encode(ENCODING_FORMAT)
        socket.send(pickle_length)
        socket.send(pickled_msg)