import socket
import threading
import pickle
from dotenv import dotenv_values

from .Message import Message

config = dotenv_values(".env")

ENCODING_FORMAT = config["ENCODING_FORMAT"]
HEADER_LENGTH = int(config["HEADER_LENGTH"])
DISCONNECT_MESSAGE = config["DISCONNECT_MESSAGE"]

SERVER_CHAT_ROOM_ID = 0

class ChatRoom:     #HOW SHOULD I KNOW WHICH USER HAS CONNECTED? => PROTOCOL
    #creator: User
    id: int
    name: str
    subscribed_users: set
    active_users: dict #dict user: sockets? #when user connects send the notification to all the users connected to make them see the new user
    socket: socket.socket
    messages: list#[Message]
    addr: tuple

    def __init__(self, id, name, host: str, active_users=dict()):
        self.id = id
        self._load_from_db() #id, messages and subscribed_users
        self.name = name #should be retreived from db
        self.active_users = active_users
        self.subscribed_users = set()
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.bind((host, 0))
        self.addr = (host, self.socket.getsockname()[1])
        print(f"PORT: {self.addr}")
        self.messages = []
        print(f"[CREATED] {self.name.capitalize()} has been created successfully on addr: {self.addr}")

    def _load_from_db(self):
        pass

    def add_active_user(self, user, client_socket):
        if user not in self.active_users:
            self.active_users[user] = client_socket

    def rm_active_user(self, user):
        if user in self.active_users:
            del self.active_users[user]

    def add_subscribed_user(self, user):
        self.subscribed_users.add(user)

    def rm_subscribed_user(self, user):
        if user in self.subscribed_users:
            self.subscribed_users.remove(user)

    def start(self):    #SHOULD GO ON UNTIL SERVER SENDS TERMINATE MESSAGE OR ACTIVE USERS DROP TO ZERO
        #start listening and creating threads for every client connecting
        print(f"[{self.name.upper()}] [LISTENING] {self.name} is listening.")
        self.socket.listen()
        while True: #TODO: SHOULD GO ON UNTIL THERE ARE USERS CONNECTED => EVERY TIME A USER DISCONNECTS RUN A FUNCTION THAT CHECKS THE NUMBER OF USERS CONNECTED AND IN CASE == 0 => CLOSES THE CHATROOM
            # handle the connection of a new client
            client_socket, addr = self.socket.accept()

            # creating new thread to handle this client
            client_thread = threading.Thread(target=self._client_handler, args=(client_socket, addr))
            client_thread.start()
        #send signal to server communicating the closing
        #self.socket.close()

    def _client_handler(self, client_socket, addr):
        #retrieve user infos
        user_info = self._retrieve_user_info(client_socket)
        self.active_users[user_info] = client_socket
        print(f"[{self.name.upper()}] [CONNECTED] {user_info.nickname} has connected!")

        while True:
            # wait for client to send msg
            msg_length = self._receive_msg_length(client_socket)
            message_received = client_socket.recv(msg_length)
            msg = pickle.loads(message_received)
            if msg.msg == DISCONNECT_MESSAGE:
                break
            self._send_to_all_clients_connected(user_info, msg)
            print(f"[{self.name.upper()}] [{addr}] <<< HEAD {msg_length}>>  {msg.msg}")
            #TODO: save the new message in the db and send it in real time to the connected users (self._send_to_client())
        client_socket.close()
        del self.active_users[user_info]
        print(f"[{self.name.upper()}] {addr} disconnected :(")

    def _retrieve_user_info(self, client_socket):
        msg_length = self._receive_msg_length(client_socket)
        message_received = client_socket.recv(msg_length)
        msg = pickle.loads(message_received)
        if msg.msg != "user_info":
            raise Exception("Bad connecting protocol.")
        return msg.obj


    def _send_to_all_clients_connected(self, user_info, msg: Message): #TODO test it
        """when receiving a message on the chatroom sends it to all the users except the one that sent it in the first place"""
        for user in self.active_users:
            if user != user_info:
                user_socket = self.active_users[user]
                msg.send(user_socket)



    def _receive_msg_length(self, client_socket):
        msg_length = int(client_socket.recv(HEADER_LENGTH).decode(ENCODING_FORMAT))
        return msg_length

    def _receive_chat_room_id(self, client_socket):
        chat_room_id = client_socket.recv(4).decode(ENCODING_FORMAT)
        return chat_room_id