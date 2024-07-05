from pymongo import MongoClient
from dotenv import dotenv_values
from bson import ObjectId
import bcrypt


config = dotenv_values(".env")
MONGODB_CONNECT = config["MONGODB_CONNECT"]

client = MongoClient(MONGODB_CONNECT)
mdb_db = client['chat_rooms']
mdb_users = mdb_db['user']


class Auth:
    @staticmethod
    def hash(pwd: str):
        pwd = pwd.encode()
        salt = bcrypt.gensalt()
        return bcrypt.hashpw(pwd, salt)

    @staticmethod
    def login(nickname: str, pwd: str):
        """Looks for the user in the db and checks password"""
        user = mdb_users.find_one({'nickname': nickname})
        if not user:
            raise Exception(f"No user named {nickname}.")
        #check passoword

        if not bcrypt.checkpw(pwd.encode('utf-8'), user['password']):
            raise Exception("Incorrect password.")

    @staticmethod
    def register(nickname, pwd, confirm_pwd):
        """Registers the user into the db"""
        if not nickname:
            nickname = input("Nickname: ")
            pwd = input("Password: ")
            confirm_pwd = input("Confirm Password: ")

        if pwd != confirm_pwd:
            raise Exception("Password and Confirm Password don't match.")
        if Auth._user_already_exists(nickname):
            raise Exception("User Already Exists")

        hashed = Auth.hash(pwd)
        print(f"HASHED: {hashed}")
        user = {
            'nickname': nickname,
            'password': hashed,
            'subscribed_chats': []
        }
        mdb_users.insert_one(user)

    @staticmethod
    def _user_already_exists(nickname):
        return bool(mdb_users.find_one({'nickname': nickname}))
