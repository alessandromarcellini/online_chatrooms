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
mdb_users = mdb_db['user']



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

        #subparser for open_chatroom
        argsp = argsubparsers.add_parser("open_chatroom", help="Open an existing chatroom")
        argsp.add_argument("id", help="The id of the ChatRoom to open.")

        #subparser for delete_chatroom
        argsp = argsubparsers.add_parser("delete_chatroom", help="Delete an existing chatroom")
        argsp.add_argument("id", help="The id of the ChatRoom to delete.")

        #fake subparser for disconnect message
        argsp = argsubparsers.add_parser(DISCONNECT_MESSAGE)



    def _load_from_db(self):
        """loads the chatrooms from the db"""
        chatrooms = mdb_chatrooms.find()
        for cht in chatrooms:
            to_add = ChatRoomDetails(cht['_id'], cht['owner'], cht['name'], cht['subscribed_users'])#, to_start.addr)
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
            self._handle_command(msg, client_socket)
            if msg.msg == DISCONNECT_MESSAGE:
                break

        client_socket.close()
        print(f"{addr} disconnected :(")


    def _receive_msg_length(self, client_socket):
        msg = client_socket.recv(HEADER_LENGTH).decode(ENCODING_FORMAT)
        msg_length = int(msg)
        return msg_length

    #PARSING COMMANDS--------------------------------------------------------------------------------------------------
    def _handle_command(self, msg, client_socket):
        #try:
        args = self.parser.parse_args(msg.msg.split())
        if args.command == "create_chatroom":
            self._create_chatroom(client_socket, args, msg.sender.id)
        elif args.command == "delete_chatroom":
            self._delete_chat_room()
            #MAKE THE USER DISCONNECT
        elif args.command == "open_chatroom":
            self._open_chatroom(args, client_socket)
        elif args.command == "delete_chatroom":
            sender_id = msg.sender.id
            self._delete_chatroom(args, sender_id)

        # except Exception as e:
        #     print(msg)
        #     print(e)
        #     response = Message(-2, 0, self.details, f"'{msg.msg}' is not a command. You can only send commands to the main server!")
        #     response.send(client_socket)

    def _open_chatroom(self, args, client_socket):
        chatroom_details = self._get_chatroom_by_id(ObjectId(args.id))
        if args.id not in self.active_chat_rooms: # if chatroom isn't active right now => open it
            print(f"ACTIVATED CHATROOM: {str(chatroom_details.name).upper()}")
            self.active_chat_rooms.add(chatroom_details.id)
            #print(self.active_chat_rooms)
            to_start = ChatRoom(chatroom_details.id, chatroom_details.owner, chatroom_details.name, self.addr[0])
            chatroom_details.addr = to_start.addr
            chatroom_thread = threading.Thread(target=self._run_chatroom, args=[to_start])
            chatroom_thread.start()

        print(f"Chatroom to connect to: {chatroom_details.addr}")
        response = AdministrationMessage("connect_to_chatroom", chatroom_details)
        response.send(client_socket)

    def _delete_chatroom(self, args, sender_id):
        chatroom_details = self._get_chatroom_by_id(ObjectId(args.id))
        if sender_id != chatroom_details.owner: #TODO: made it so that a chatroom can have multiple owners
            raise Exception("You're not the owner of this chatroom.")

        self.active_chat_rooms.discard(chatroom_details)
        self.chat_rooms_created.discard(chatroom_details)
        mdb_chatrooms.delete_one({'_id': ObjectId(args.id)})

        #send disconnect and delete message to all users
        response = AdministrationMessage("delete_chatroom", chatroom_details)
        self._send_to_all_clients_connected(response)


    def _send_to_all_clients_connected(self, msg, sender_info=None, include_sender=False): #TODO test it
        """when receiving a message on the chatroom sends it to all the users except the one that sent it in the first place"""
        if not sender_info and include_sender:
            raise Exception("If you want to include_sender need to pass the sender_info")

        for user in self.active_users:
            if user != sender_info and not include_sender:
                user_socket = self.active_users[user]
                msg.send(user_socket)


    def _create_chatroom(self, client_socket, args, owner):
        # create the chatroom
        chatroom = self._create_and_return_chat_room(args, owner)

        # start the chatroom on a new thread
        chatroom_thread = threading.Thread(target=self._run_chatroom, args=[chatroom])
        chatroom_thread.start()

        # send the success message
        confirm_message = Message(-2, 0, self.details, f"[SERVER] ChatRoom created successfully! ID: {chatroom.id}")
        confirm_message.send(client_socket)



        # send the message to make the user connect to the chatroom #TODO: Make a function to do this
        chatroom_details = ChatRoomDetails(chatroom.id, owner, chatroom.name, chatroom.subscribed_users,
                                           chatroom.addr, chatroom.messages, chatroom.active_users)
        response = AdministrationMessage("connect_to_chatroom", chatroom_details)
        response.send(client_socket)


    def _get_chatroom_by_id(self, id: ObjectId):
        # TODO: if chatroom is suspended (no one was in it for 3 minutes [STILL TO ADD]) activate it in _get_chatroom_by_id
        for chatroom in self.chat_rooms_created:
            if chatroom.id == id:
                return chatroom
        raise Exception(f"Chatroom {id} doesn't exist")

    def _create_and_return_chat_room(self, args, owner):
        #creating the chatroom
        chatroom_id = ObjectId()

        to_create = ChatRoom(chatroom_id, owner, args.name, self.addr[0])
        to_add = ChatRoomDetails(chatroom_id, owner, args.name, None, to_create.addr)

        new_chatroom = {
            '_id': chatroom_id,
            'owner': owner,
            'name': args.name,
            'subscribed_users': [], #TODO: should decide how to manage this filed, whether or not to set a limit of subscribed users
            'active_users': [],
            'is_active': True,
        }

        self.chat_rooms_created.add(to_add)
        self.active_chat_rooms.add(to_add)
        #adding the new chatroom to the db
        prova = mdb_chatrooms.insert_one(new_chatroom)

        result = mdb_users.update_one(
            {'_id': owner},
            {'$push': {'subscribed_chats': new_chatroom}}
        )

        return to_create

    def _run_chatroom(self, chatroom):
        chatroom.start()

    def _delete_chat_room(self):
        pass #check for permits
