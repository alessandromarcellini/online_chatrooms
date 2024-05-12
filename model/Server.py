import socket
import pickle
import threading
import argparse
from itertools import chain

from dotenv import dotenv_values

from .Message import Message
from .ChatRoomDetails import ChatRoomDetails
from .AdministrationMessage import AdministrationMessage
from .ChatRoom import ChatRoom
from .UserDetails import UserDetails

config = dotenv_values(".env")

ENCODING_FORMAT = config["ENCODING_FORMAT"]
HEADER_LENGTH = int(config["HEADER_LENGTH"])
DISCONNECT_MESSAGE = config["DISCONNECT_MESSAGE"]
SERVER_HOST = config["SERVER_HOST"]

class Server:
    addr: tuple
    chat_rooms_created: set
    chat_rooms_active: set #they're active if at least one user is connected
    socket: socket.socket #socket to handle requests to the server like creating chatrooms, deleting them, opening them or
    parser: argparse.ArgumentParser
    greatest_chatroom_id: int   #WON'T NEED THIS ONCE WE HAVE A DB

    details: UserDetails

    def __init__(self, port: int):
        print("[STARTING] Server is starting")
        self.details = UserDetails(0, "server")
        self._set_parser()
        self._load_from_db()
        self.greatest_chatroom_id = 0
        self.chat_rooms_created = set()
        self.chat_rooms_active = set()
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.addr = (SERVER_HOST, port) #socket.gethostbyname(socket.gethostname())
        self.socket.bind(self.addr)
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
        pass

    def _retreive_messages_from_chatroom(self):
        pass

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
                #create the chatroom
                chatroom = self._create_and_return_chat_room(args)

                # start the chatroom on a new thread
                chatroom_thread = threading.Thread(target=self._run_chatroom, args=[chatroom])
                chatroom_thread.start()

                #send the success message
                confirm_message = Message(-2, 0, self.details, f"[SERVER] ChatRoom created successfully! ID: {chatroom.id}")
                confirm_message.send(client_socket)

                #send the message to make the user connect to the chatroom
                chatroom_details = ChatRoomDetails(chatroom.id, chatroom.name, chatroom.subscribed_users,
                                                   chatroom.addr, chatroom.messages, chatroom.active_users)
                response = AdministrationMessage("connect_to_chatroom", chatroom_details)
                response.send(client_socket)

            elif args.command == "delete_chatroom":
                self._delete_chat_room()
                #MAKE THE USER DISCONNECT
            elif args.command == "open_chatroom":
                chatroom_details = self._get_chatroom_by_id(int(args.id))
                print(f"Chatroom to connect to: {chatroom_details.addr}")
                if not chatroom_details: #TODO: Handle it
                    raise Exception("Bad ChatRoom id")

                response = AdministrationMessage("connect_to_chatroom", chatroom_details)
                response.send(client_socket)

        except Exception as e:
            print(e)
            response = Message(-2, 0, self.details, f"'{command}' is not a command. You can only send commands to the main server!")
            response.send(client_socket)

    def _get_chatroom_by_id(self, id: int):
        for chatroom in self.chat_rooms_created:
            if chatroom.id == id:
                return chatroom
        return None

    def _create_and_return_chat_room(self, args):
        self.greatest_chatroom_id += 1
        to_create = ChatRoom(self.greatest_chatroom_id, args.name, self.addr[0])   #TODO: MAKE ID AUTOMATIC RETREIVING FROM THE DB THE GREATEST ID EXISTING AND ADDING 1 TO IT
        to_add = ChatRoomDetails(1, args.name, None, to_create.addr)
        self.chat_rooms_created.add(to_add)
        self.chat_rooms_active.add(to_add)
        return to_create

    def _run_chatroom(self, chatroom):
        chatroom.start()

    def _delete_chat_room(self):
        pass #check for permits
