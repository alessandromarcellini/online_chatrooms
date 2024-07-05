import socket
import threading
import pickle
from dotenv import dotenv_values

from .Message import Message
from .UserDetails import UserDetails

from pymongo import MongoClient
from bson import ObjectId

MESSAGES_PAGE_SIZE = 100

config = dotenv_values(".env")

ENCODING_FORMAT = config["ENCODING_FORMAT"]
HEADER_LENGTH = int(config["HEADER_LENGTH"])
DISCONNECT_MESSAGE = config["DISCONNECT_MESSAGE"]

SERVER_CHAT_ROOM_ID = 0

MONGODB_CONNECT = config["MONGODB_CONNECT"]

#commands:
    #send_active_users
    #send_subscribed_users



client = MongoClient(MONGODB_CONNECT)

mdb_db = client['chat_rooms']
mdb_messages = mdb_db['message']
mdb_users = mdb_db['user']

class ChatRoom:     #HOW SHOULD I KNOW WHICH USER HAS CONNECTED? => PROTOCOL
    #creator: User
    id: ObjectId
    owner: ObjectId
    name: str
    subscribed_users: set
    active_users: dict #TODO: when user connects send the notification to all the users connected to make them see the new user
    socket: socket.socket
    addr: tuple
    messages: dict #key: page_number, value: list of messages
    pages_loaded: dict #key: number of the page, value: number_of_users_using_it
                    # #A page of messages is made of 100 messages, the dict has in it only the pages that at least one user is using

    def __init__(self, id, owner,name, host: str, active_users=dict()):
        self.messages = {}
        self.pages_loaded = {}
        self.id = id
        self.owner = owner
        #self._retreive_messages() #id, messages and subscribed_users
        self.name = name #should be retreived from db
        self.active_users = active_users
        self.subscribed_users = set()
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.bind((host, 0))
        self.addr = (host, self.socket.getsockname()[1])
        print(f"PORT: {self.addr}")
        print(f"[CREATED] {self.name.capitalize()} has been created successfully on addr: {self.addr}, ID: {str(self.id)}")

    def _retreive_messages(self, user_socket=None, page_number=None):
        """loads from the db the requested page of messages if not in the messages list already.
        Sends the requested page of messages to the user requesting them.
        Note: a page of messages is made of MESSAGES_PAGE_SIZE messages"""
        number_of_msg_docs = mdb_messages.count_documents({'chat_id': self.id})
        number_of_pages = number_of_msg_docs // MESSAGES_PAGE_SIZE
        if not page_number:
            page_number = number_of_pages #get the number of the next page

        to_send = []
        skip_count = page_number * MESSAGES_PAGE_SIZE
        if page_number not in self.messages:
            #needs to be loaded from the db
            self.messages[page_number] = []
            messages = mdb_messages.find({'chat_id': self.id}).skip(skip_count).limit(MESSAGES_PAGE_SIZE)
            for msg in messages:
                #create the Message Object
                print(f"\n\n{msg}\n\n")
                sender_mdb = mdb_users.find({'_id': msg['sender_id']})[0]
                sender = UserDetails(sender_mdb['_id'], sender_mdb['nickname'])
                to_add = Message(msg['_id'], self.id, sender, msg['msg'], msg['tags'], msg['responding_to'])
                to_send.append(to_add)
                self.messages[page_number].append(to_add)
            self.pages_loaded[page_number] = 1
        else:
            #get them directly from the self.messages
            to_send = self.messages[page_number]
            self.pages_loaded[page_number] += 1
        #sending
        if user_socket:
            for msg in to_send:
                msg.send(user_socket)


    def add_active_user(self, user, user_socket):
        if user not in self.active_users:
            self.active_users[user] = user_socket

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

    def _client_handler(self, user_socket, addr):
        #retrieve user infos
        user_info = self._retrieve_user_info(user_socket)
        self.add_active_user(user_info, user_socket)
        print(f"[{self.name.upper()}] [CONNECTED] {user_info.nickname} has connected!")
        self._retreive_messages(user_socket=user_socket)
        while True:
            # wait for client to send msg
            msg_length = self._receive_msg_length(user_socket)
            message_received = user_socket.recv(msg_length)
            msg = pickle.loads(message_received)
            print(f"\n\nMSG_USER: {msg.sender.id}\n\n")
            self._check_for_commands(msg)
            if msg.msg == DISCONNECT_MESSAGE:
                break
            #TODO: should check if it is an AdministrationMessage, if it is => don't save it
            self._save_message_messages(msg)
            self._save_message_db(msg)
            self._send_to_all_clients_connected(msg, user_info)
            print(f"[{self.name.upper()}] [{user_info.nickname}] <<< HEAD {msg_length}>>  {msg.msg}")
        user_socket.close()
        del self.active_users[user_info]
        print(f"[{self.name.upper()}] {addr} disconnected :(")

    def _check_for_commands(self, msg):
        pass

    def _save_message_messages(self, msg):
        """
        This function runs when a user sends a new message in the chatroom.
        It will save that message in the self.messages dict with it's own page.
        """
        #get the page (greatest from db)
        number_of_msg_docs = mdb_messages.count_documents({'chat_id': self.id})
        page_number = number_of_msg_docs // MESSAGES_PAGE_SIZE

        #if page is a new one => create it
        if page_number not in self.messages: #if the message is of a new page => need to create the new page and load it for everyone connected
            self.messages[page_number] = []
            self.pages_loaded[page_number] = len(self.active_users)

        #save the message in self.messages[page]
        self.messages[page_number].append(msg)


    def _save_message_db(self, msg):
        #saving the message
        message = {
            'chat_id': msg.chat_id,
            'sender_id': msg.sender.id,
            'msg': msg.msg,
            'date_time': msg.date_time,
            'responding_to': msg.responding_to,
            'tags': msg.tags,
        }
        mdb_messages.insert_one(message)


    def _retrieve_user_info(self, client_socket):
        msg_length = self._receive_msg_length(client_socket)
        message_received = client_socket.recv(msg_length)
        msg = pickle.loads(message_received)
        if msg.msg != "user_info":
            raise Exception("Bad connecting protocol.")
        return msg.obj


    def _send_to_all_clients_connected(self, msg, sender_info=None, include_sender=False): #TODO test it
        """when receiving a message on the chatroom sends it to all the users except the one that sent it in the first place"""
        if not sender_info and include_sender:
            raise Exception("If you want to include_sender need to pass the sender_info")

        for user in self.active_users:
            if user != sender_info and not include_sender:
                user_socket = self.active_users[user]
                msg.send(user_socket)




    def _receive_msg_length(self, client_socket):
        msg_length = int(client_socket.recv(HEADER_LENGTH).decode(ENCODING_FORMAT))
        return msg_length

    def _receive_chat_room_id(self, client_socket):
        chat_room_id = client_socket.recv(4).decode(ENCODING_FORMAT)
        return chat_room_id