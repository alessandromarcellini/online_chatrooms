from dotenv import dotenv_values

from model.User import User
from model.Message import Message

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
    nickname = input("Enter your nickname: ")
    pwd = input("Enter your password: ")

    id = ObjectId()

    client = User(id, nickname, pwd)

    temporary_save_client(client)


    i = 0
    while True:
        msg = input("New message: ")
        msg_to_send = Message(i, client.open_chat.id, client.details, msg)
        client.send_msg(msg_to_send)
        i += 1
    client.socket.close()


def temporary_save_client(client):
    user = {
        '_id': client.id,
        'nickname': client.nickname,
        'subscribed_chats': []
    }

    mdb_users.insert_one(user)


if __name__ == "__main__":
    main()
