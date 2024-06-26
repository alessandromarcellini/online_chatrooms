# Online Chat-room Desktop App

## Overview
A simple chat-room application written in Python allowing users on the same local network to chat with each other. Featuring MongoDB and a practical User Interface (coming soon).


Note: the project is still in the development stage.

This project serves as a practical application of my current studies and anticipated future coursework at university. Although there are no plans to take this project into production, it has been designed with scalability and optimization in mind. Contributions to further enhance the project are welcome (see the "How to Contribute" section).

## Features

- **server.py**: Handles the server-side logic (see the "Server" section).
- **client.py**: Connects to chatrooms and enables communication with other users (clients).
- **MongoDB**: A NoSQL database to store user data, chatrooms, and message details.

### Protocols

.

## Installation and Setup

Follow these steps to install and run the project on your machine:

1. Ensure Python is installed (version 3.11 is recommended).
2. Clone the repository to your local machine.
3. Install the required dependencies specified in `requirements.txt`.
4. Create a `.env` file with the following variables:
    ```env
    SERVER_HOST = '<local_ip_of_the_machine_hosting_the_server>'
    SERVER_PORT = <server_port>
    DISCONNECT_MESSAGE = '<special_message_sent_to_disconnect>'
    SERVER_CHAT_ROOM_ID = 0
    HEADER_LENGTH = 1024
    ENCODING_FORMAT = 'utf-8'
    MONGODB_CONNECT = '<mongodb_connection_string>'
    ```

### Troubleshooting

If you encounter issues connecting the client to the server, it may be due to firewall settings. Ensure that your firewall is configured to allow the necessary connections.

##Server and server commands
The server script runs the server instance, managing all the chatrooms created and active.

For scalability purposes when someone creates a new chat-room or opens an already existing one the server runs the chat-room on a new thread having its own socket.

Server commands:
* create_chatroom <chatroom_name>
* open_chatroom <chatroom_id>
* delete_chatroom <chatroom_id>
* More coming...


## How to Contribute

Contributions to the project are welcome! Follow these steps to contribute:

1. Open a new issue on this project's GitHub page, describing what you want to implement or fix.
2. Fork the repository.
3. Create a new branch on your forked repository for your changes.
4. Commit your changes to the new branch.
5. Create a pull request referencing the issue (add `#<issue_number>` in the PR comments) to merge your changes into the main codebase.

## Future Enhancements

- Handling errors and exceptions that could occur during the connection.
- Handling user's disconnection from a chatroom making him connect back to the server.
- Develop a better "terminal interface" making the application usable even without launching the GUI.
- Developing a user-friendly graphical user interface.
- Optimizing the app and cleaning the code.

Thank you for looking a this project. Your feedback and contributions are highly appreciated.