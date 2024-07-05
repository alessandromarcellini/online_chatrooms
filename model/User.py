import socket
import pickle
import threading
from dotenv import dotenv_values

from .ChatRoomDetails import ChatRoomDetails
from .AdministrationMessage import AdministrationMessage
from .Message import Message
from .UserDetails import UserDetails
from .Auth import Auth

from pymongo import MongoClient
from bson import ObjectId

import getpass

config = dotenv_values(".env")

ENCODING_FORMAT = config["ENCODING_FORMAT"]
HEADER_LENGTH = int(config["HEADER_LENGTH"])
DISCONNECT_MESSAGE = config["DISCONNECT_MESSAGE"]
SERVER_CHAT_ROOM_ID = config["SERVER_CHAT_ROOM_ID"]
SERVER_HOST = config["SERVER_HOST"]
SERVER_PORT = int(config["SERVER_PORT"])
MONGODB_CONNECT =  config["MONGODB_CONNECT"]

client = MongoClient(MONGODB_CONNECT)
mdb_db = client['chat_rooms']
mdb_users = mdb_db['user']

class User: #Client
    id: ObjectId #unique =>make it a str and get it from the nickname
    nickname: str
    open_chat: ChatRoomDetails
    subscribed_chats: set #list of ChatRoom (Details) which the user is subscribed to
    socket: socket.socket
    #TODO: add a "loaded_pages" field so that when disconnecting we can notify the chatroom that we don't nedd them anymore

    details: UserDetails


    def __init__(self, id, nickname=None, password=None):
        self.id = id #should be loaded from db
        self.nickname = nickname
        self.password = password

        if input("Login / Register (L/r): ") == 'r':
            self.register()
        else:
            self.login()
        #self._load_from_db() #=> load id and subscribed_chats from db
        self.subscribed_chats = set() #TODO: SHOULD BE LOADED FROM DB
        #starting out the only open chat will be the server's one
        server = ChatRoomDetails(SERVER_CHAT_ROOM_ID, None, "SERVER", None, (SERVER_HOST, SERVER_PORT), None, None)
        self.subscribed_chats.add(server)
        self._connect_to_server(server)
        listening_thread = threading.Thread(target=self._listen)
        listening_thread.start()

    def login(self):
        print("LOGIN INTERFACE:")

        nickname = input("Nickname: ")
        pwd = getpass.getpass(prompt="Password: ")
        Auth.login(nickname, pwd)
        self.nickname = nickname
        self.password = pwd
        self._load_from_db()
        self.details = UserDetails(self.id, nickname)
        print("Logged in Successfully!")

    def register(self):
        print("REGISTER INTERFACE:")

        nickname = input("Nickname: ")
        pwd = getpass.getpass(prompt="Password: ")
        confirm_pwd = getpass.getpass(prompt="Confirm Password: ")
        Auth.register(nickname, pwd, confirm_pwd)
        self.nickname = nickname
        self.password = pwd
        self.details = UserDetails(self.id, nickname)
        self.subscribed_chats = set()
        print("Registered Successfully!")


    def _listen(self):
        print("I'm listening")
        while True:
            #wait for length of message
            msg_length = int(self.socket.recv(HEADER_LENGTH).decode(ENCODING_FORMAT))
            #receive the msg
            msg_pickled = self.socket.recv(msg_length)
            msg = pickle.loads(msg_pickled)
            if msg.id == -1:
                self._check_for_commands_from_server(msg)
                print(f"[ADMINISTRATION] <<<< HEAD {msg_length} >> {msg.msg}")
            else:
                print(f"[{msg.sender.nickname}] <<<< HEAD {msg_length} >> {msg.msg}")

    def _check_for_commands_from_server(self, command: AdministrationMessage):
        if command.msg == "connect_to_chatroom":
            chatroom = command.obj
            self.connect_to_chatroom(chatroom)
        elif command.msg == "delete_chatroom":
            chatroom = command.obj
            self.subscribed_chats.discard(chatroom) #TODO: test it----------------------------------------------------------------
            if self.open_chat == chatroom:
                self.open_chat = None

    def _connect_to_server(self, server):
        print(f"connecting to server... {server.addr}")
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.open_chat = server
        self.socket.connect(self.open_chat.addr)


    def connect_to_chatroom(self, chatroom: ChatRoomDetails):
        #should be loading at least the last 1000 messages in this chat to show to the user

        # if chatroom not in self.subscribed_chats: TODO later
        #     raise Exception("You're not subscribed to this chat")

        print(f"connecting to {chatroom.name}...")
        if self.socket:
            disconnect_message = Message(1, self.open_chat.id, self.details, DISCONNECT_MESSAGE)
            disconnect_message.send(self.socket)
            self.socket.close()
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

        self.open_chat = chatroom

        print(f"ADDR: {self.open_chat.addr}")
        self.socket.connect(self.open_chat.addr) #TODO: add error handling
        self.subscribed_chats.add(self.open_chat)

        #send your informations
        self._send_infos()
        print(f"[CONNECTED] Connected to ChatRoom {chatroom.name}")

    def _send_infos(self):
        """As a protocol when connecting to a chatroom the user sends his informations for identification"""
        infos = UserDetails(self.id, self.nickname, self.subscribed_chats)
        msg = AdministrationMessage("user_info", infos)
        msg.send(self.socket)

    def _load_from_db(self): #TODO: TO COMPLEATE
        user = mdb_users.find_one({'nickname': self.nickname})
        if not user:
            raise Exception(f"No user named {self.nickname}.")
        print(f"LOG_INUSER_ID {user['_id']}")
        self.id = user['_id']
        print(self.id)

    def send_msg(self, msg: Message):   #client.py will create the message and pass it to Client.send_msg
        #client.send_msg checks for chat_room availability and calls msg.send

        chat_id = msg.chat_id
        #check if chat is in subscribed => else throw error
        chat = self._get_chat_if_present(chat_id, self.subscribed_chats)
        if not chat:
            raise Exception("You're not subscribed to this ChatRoom.")
        else:
            if self.open_chat == chat:
                msg.send(self.socket)
            else:
                self.connect_to_chatroom(chat)
                msg.send(self.socket)

    def _get_chat_if_present(self, chat_id, to_scan):
        for chat in to_scan:
            if chat.id == chat_id:
                return chat
        return None

    def remove_chat_from_subscribed_chats(self, chat):
        if chat in self.subscribed_chats:
            self.subscribed_chats.remove(chat)
        else:
            raise Exception("You're not subscribed to this chat room.")

    def create_chat_room(self, host, port):
        #Message format:, id, chat_id=None, sender, msg=command
        #create_chat_room id host port
        command = Message(1, SERVER_CHAT_ROOM_ID, self.details, f"create_chat_room {host} {port}")
        self.send_msg(command)

