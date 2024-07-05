from dotenv import dotenv_values

from model.User import User
from model.Message import Message
from model.Auth import Auth

from pymongo import MongoClient
from bson import ObjectId


config = dotenv_values(".env")

SERVER_HOST = config["SERVER_HOST"]
SERVER_PORT = int(config["SERVER_PORT"])

#do not hard code this
ADDR = (SERVER_HOST, SERVER_PORT)

ENCODING_FORMAT = 'utf-8'
HEADER_LENGTH = 64
DISCONNECT_MESSAGE = "DO_NOT_TYPE_THIS"
MONGODB_CONNECT = config["MONGODB_CONNECT"]


client = MongoClient(MONGODB_CONNECT)
mdb_db = client['chat_rooms']
mdb_users = mdb_db['user']


def main():
    id = ObjectId()
    client = User(id)

    i = 0
    while True:
        msg = input("New message: ")
        msg_to_send = Message(i, client.open_chat.id, client.details, msg)
        client.send_msg(msg_to_send)
        i += 1
    client.socket.close()



if __name__ == "__main__":
    main()
