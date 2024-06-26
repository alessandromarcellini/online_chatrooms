import socket
import pickle
import threading
import argparse

from dotenv import dotenv_values

from .Message import Message
from .ChatRoomDetails import ChatRoomDetails
from .AdministrationMessage import AdministrationMessage
from .ChatRoom import ChatRoom
from .UserDetails import UserDetails

from pymongo import MongoClient
from bson import ObjectId

config = dotenv_values(".env")

ENCODING_FORMAT = config["ENCODING_FORMAT"]
HEADER_LENGTH = int(config["HEADER_LENGTH"])
DISCONNECT_MESSAGE = config["DISCONNECT_MESSAGE"]
SERVER_HOST = config["SERVER_HOST"]
MONGODB_CONNECT = config["MONGODB_CONNECT"]



client = MongoClient(MONGODB_CONNECT)

mdb_db = client['chat_rooms']
mdb_chatrooms = mdb_db['chatroom']
mdb_messages = mdb_db['message']



class Server:
    addr: tuple
    chat_rooms_created: set
    active_chat_rooms: set #they're active if at least one user is connected
    socket: socket.socket #socket to handle requests to the server like creating chatrooms, deleting them, opening them or
    parser: argparse.ArgumentParser

    details: UserDetails

    def __init__(self, port: int):

        print("[STARTING] Server is starting")
        self.details = UserDetails(0, "server")
        self._set_parser()
        self.chat_rooms_created = set()
        self.active_chat_rooms = set()
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.addr = (SERVER_HOST, port) #socket.gethostbyname(socket.gethostname())
        self.socket.bind(self.addr)
        self._load_from_db()
        print(f"[READY] Server is ready at port: {self.addr}")

    def _set_parser(self):
        self.parser = argparse.ArgumentParser(description="Server parser")

        argsubparsers = self.parser.add_subparsers(title="Commands", dest="command")
        argsubparsers.required = True

        #subparser for create_chatroom
        argsp = argsubparsers.add_parser("create_chatroom", help="create chatroom")
        #id needs to be auto computed
        argsp.add_argument("name", help="The ChatRoom name.")

        #subparser for delete_chatroom
        argsp = argsubparsers.add_parser("delete_chatroom")
        argsp.add_argument("id", help="The ChatRoom id.")

        #subparser for open_chatroom
        argsp = argsubparsers.add_parser("open_chatroom", help="Open an existing chatroom")
        argsp.add_argument("id", help="The id of the ChatRoom to open.")

        #fake subparser for disconnect message
        argsp = argsubparsers.add_parser(DISCONNECT_MESSAGE)



    def _load_from_db(self):
        """loads the chatrooms from the db"""
        chatrooms = mdb_chatrooms.find()
        for cht in chatrooms:
            to_add = ChatRoomDetails(cht['_id'], cht['name'], cht['subscribed_users'])#, to_start.addr)
            self.chat_rooms_created.add(to_add)
            self.active_chat_rooms.add(to_add)
            print(f"Added: {to_add.id}")

    def start(self):
    #start listening and creating threads for every client connecting
        print("[LISTENING] server is listening for commands from the users.")
        self.socket.listen()
        while True:
            # handle the connection of a new client that wants to request something to the server
            client_socket, addr = self.socket.accept()

            # creating new thread to handle this client
            client_thread = threading.Thread(target=self._client_handler, args=(client_socket, addr))
            client_thread.start()
        #self.socket.close()

    def _client_handler(self, client_socket, addr):
        # one thread to receive messages from client and one to send to them
        #TODO: should probably identify the user with the same protocol as the chatroom's
        print(f"[CONNECTED] {addr[0]}:{addr[1]} has connected!")

        while True:
            # wait for client to send msg
            msg_length = self._receive_msg_length(client_socket)
            message_received = client_socket.recv(msg_length)
            msg = pickle.loads(message_received)
            self._handle_command(msg.msg, client_socket)
            if msg.msg == DISCONNECT_MESSAGE:
                break

        client_socket.close()
        print(f"{addr} disconnected :(")


    def _receive_msg_length(self, client_socket):
        msg = client_socket.recv(HEADER_LENGTH).decode(ENCODING_FORMAT)
        msg_length = int(msg)
        return msg_length

    #PARSING COMMANDS--------------------------------------------------------------------------------------------------
    def _handle_command(self, command, client_socket):
        try:
            args = self.parser.parse_args(command.split())
            if args.command == "create_chatroom":
                self._create_chatroom(client_socket, args)
            elif args.command == "delete_chatroom":
                self._delete_chat_room()
                #MAKE THE USER DISCONNECT
            elif args.command == "open_chatroom":
                self._open_chatroom(args, client_socket)

        except Exception as e:
            print(e)
            response = Message(-2, 0, self.details, f"'{command}' is not a command. You can only send commands to the main server!")
            response.send(client_socket)

    def _open_chatroom(self, args, client_socket):
        chatroom_details = self._get_chatroom_by_id(ObjectId(args.id))  # TODO: if chatroom is suspended (no one was in it for 3 minutes [STILL TO ADD]) activate it in _get_chatroom_by_id
        if args.id not in self.active_chat_rooms: # if chatroom isn't active right now => open it
            print("ACTIVATED CHATROOM:")
            self.active_chat_rooms.add(chatroom_details.id)
            print(self.active_chat_rooms)
            to_start = ChatRoom(chatroom_details.id, chatroom_details.name, self.addr[0])
            chatroom_details.addr = to_start.addr
            chatroom_thread = threading.Thread(target=self._run_chatroom, args=[to_start])
            chatroom_thread.start()

        print(f"Chatroom to connect to: {chatroom_details.addr}")
        response = AdministrationMessage("connect_to_chatroom", chatroom_details)
        response.send(client_socket)


    def _create_chatroom(self, client_socket, args):
        # create the chatroom
        chatroom = self._create_and_return_chat_room(args)

        # start the chatroom on a new thread
        chatroom_thread = threading.Thread(target=self._run_chatroom, args=[chatroom])
        chatroom_thread.start()

        # send the success message
        confirm_message = Message(-2, 0, self.details, f"[SERVER] ChatRoom created successfully! ID: {chatroom.id}")
        confirm_message.send(client_socket)

        # send the message to make the user connect to the chatroom
        chatroom_details = ChatRoomDetails(chatroom.id, chatroom.name, chatroom.subscribed_users,
                                           chatroom.addr, chatroom.messages, chatroom.active_users)
        response = AdministrationMessage("connect_to_chatroom", chatroom_details)
        response.send(client_socket)


    def _get_chatroom_by_id(self, id: ObjectId):
        # TODO: if chatroom is suspended (no one was in it for 3 minutes [STILL TO ADD]) activate it in _get_chatroom_by_id
        for chatroom in self.chat_rooms_created:
            if chatroom.id == id:
                return chatroom
        raise Exception(f"Chatroom {id} doesn't exist")

    def _create_and_return_chat_room(self, args):

        #creating the chatroom
        chatroom_id = ObjectId()

        to_create = ChatRoom(chatroom_id, args.name, self.addr[0])
        to_add = ChatRoomDetails(chatroom_id, args.name, None, to_create.addr)

        new_chatroom = {
            '_id': chatroom_id,
            'name': args.name,
            'subscribed_users': [], #TODO: should decide how to manage this filed, whether or not to set a limit of subscribed users
            'active_users': [],
            'is_active': True,
        }
        self.chat_rooms_created.add(to_add)
        self.active_chat_rooms.add(to_add)
        #adding the new chatroom to the db
        prova = mdb_chatrooms.insert_one(new_chatroom)
        print(f'ciao: {prova.inserted_id}')
        return to_create

    def _run_chatroom(self, chatroom):
        chatroom.start()

    def _delete_chat_room(self):
        pass #check for permits
