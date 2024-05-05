import socket
import threading

from model.Server import Server
from dotenv import dotenv_values

config = dotenv_values(".env")
SERVER_PORT = int(config["SERVER_PORT"])


def main():
    server = Server(SERVER_PORT)
    server.start()


if __name__ == "__main__":
    main()
