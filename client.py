from dotenv import dotenv_values

from model.ChatRoomDetails import ChatRoomDetails

from model.User import User
from model.Message import Message
from model.Auth import Auth
#-----------------------------------------MONGODB IMPORTS----------------------------------------------------------
from pymongo import MongoClient
from bson import ObjectId
#------------------------------------------------------------------------------------------------------------------

#-------------------------------------PROMPT TOOLKIT IMPORTS-------------------------------------------------------
from prompt_toolkit.shortcuts.dialogs import input_dialog
from prompt_toolkit.layout.controls import FormattedTextControl
from prompt_toolkit import Application
from prompt_toolkit.layout import ScrollablePane
from prompt_toolkit.layout.layout import Layout
from prompt_toolkit.layout.containers import HSplit, VSplit, Window
from prompt_toolkit.keys import Keys
#from prompt_toolkit.filters import Condition
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.styles import Style
from prompt_toolkit.widgets import TextArea
from prompt_toolkit.shortcuts.dialogs import radiolist_dialog
#------------------------------------------------------------------------------------------------------------------
from typing import List
import asyncio
#-----------------------------------ENV VARIABLES AND CONSTANTS----------------------------------------------------
config = dotenv_values(".env")

SERVER_HOST = config["SERVER_HOST"]
SERVER_PORT = int(config["SERVER_PORT"])
SERVER_CHAT_ROOM_ID = int(config["SERVER_CHAT_ROOM_ID"])

#do not hard code this
ADDR = (SERVER_HOST, SERVER_PORT)

ENCODING_FORMAT = 'utf-8'
HEADER_LENGTH = 64
DISCONNECT_MESSAGE = "DO_NOT_TYPE_THIS"
MONGODB_CONNECT = config["MONGODB_CONNECT"]

server = ChatRoomDetails(SERVER_CHAT_ROOM_ID, None, "SERVER", None, (SERVER_HOST, SERVER_PORT), None, None)
#------------------------------------------------------------------------------------------------------------------


mongo_client = MongoClient(MONGODB_CONNECT)
mdb_db = mongo_client['chat_rooms']
mdb_users = mdb_db['user']

def tui_login():
    username = input_dialog(
        title='Username',
        text='Please enter your username:'
    ).run()

    password = input_dialog(
        title='Password',
        text='Please enter your password:',
        password=True
    ).run()
    return username, password

def tui_register():
    username = input_dialog(
        title='Username',
        text='Please enter your username:'
    ).run()

    password = input_dialog(
        title='Password',
        text='Please enter your password:',
        password=True
    ).run()

    confirm_password = input_dialog(
        title='Confirm Password',
        text='Please confirm your password:',
        password=True
    ).run()
    return username, password, confirm_password



id = ObjectId()
client = User(id)

def main():
    L_R = input("Register/Login (R/l): ").lower()
    global subscribed_chatrooms
    global chatroom_number

    if L_R == "l":
        nickname, pwd = tui_login()
        client.login(nickname, pwd)

        subscribed_chatrooms = list(client.subscribed_chats)
        chatroom_number = len(subscribed_chatrooms)
        global loaded_messages
    else:
        nickname, pwd, confirm_pwd = tui_register()
        client.register(nickname, pwd, confirm_pwd)
        subscribed_chatrooms = list(client.subscribed_chats)
        chatroom_number = len(subscribed_chatrooms)

    client.register_callback(refresh_message_box)

    tui_app()


    # i = 0
    # while True:
    #     msg = input("New message: ")
    #     if msg == "EXIT":
    #         break
    #     msg_to_send = Message(i, client.open_chat.id, client.details, msg)
    #     client.send_msg(msg_to_send)
    #     i += 1
    # client.socket.close()

#------------------------------------------------------------------------------------------------------------------
#------------------------------------------------------------------------------------------------------------------
#------------------------------------------------------------------------------------------------------------------
#------------------------------------------------------------------------------------------------------------------
#------------------------------------------------------------------------------------------------------------------
#------------------------------------------------------------------------------------------------------------------


kb = KeyBindings()
#subscribed_chatrooms = list(client.subscribed_chats)
loaded_messages = []
message_number = len(loaded_messages)

chatroom_index = 0
message_index = message_number - 1

#---------------------------------------------UTILITIES----------------------------------------------------
def increment_chatroom_index():
    global chatroom_index
    if chatroom_index < chatroom_number - 1:
        chatroom_index += 1
        highlight_selected_chatroom(DOWN)

def decrement_chatroom_index():
    global chatroom_index
    if chatroom_index > 0:
        chatroom_index -= 1
        highlight_selected_chatroom(UP)

def increment_message_index():
    global message_index
    if message_index < message_number - 1:
        message_index += 1

def decrement_message_index():
    global message_index
    if message_index > 0:
        message_index -= 1

def get_focused_pane():
    focus = app.layout.current_window
    if focus in chatrooms_to_display.children:
        return "chatrooms_to_display"
    elif focus in messages_to_display.children:
        return "messages_to_display"
    return None

UP = 1
DOWN = -1

def highlight_selected_chatroom(direction: int):
    #chatrooms_to_display = HSplit(children=[Window(FormattedTextControl(text=f"Chatroom {x}")) for x in range(chatroom_number)])
    chatrooms_to_display.children[chatroom_index].content.style = "bg:white fg:black"
    if chatroom_index + direction >= 0:
        chatrooms_to_display.children[chatroom_index + direction].content.style = ""

#------------------------------------------------------------------------------------------------------------------

#-----------------------------------------------KB CONDITIONS------------------------------------------------------
def is_chatrooms_focused(event):
    """Returns True if the chatrooms_to_display panel is currently focused"""
    global chatrooms_to_display
    current_focus = event.app.layout.current_window
    return current_focus in chatrooms_to_display.children

def is_messages_focused(event):
    """Returns True if the messages_to_display panel is currently focused"""
    global messages_to_display
    current_focus = event.app.layout.current_window
    return current_focus in messages_to_display.children

#-----------------------------------------------KB----------------------------------------------------------------


@kb.add(Keys.Up)
def scroll_up(event):
    if is_chatrooms_focused(event):
        scroll_up_chatroom(event)
    elif is_messages_focused(event):
        scroll_up_message(event)

@kb.add(Keys.Down)
def scroll_down(event):
    if is_chatrooms_focused(event):
        scroll_down_chatroom(event)
    elif is_messages_focused(event):
        scroll_down_message(event)


def scroll_down_chatroom(event):
    if is_chatrooms_focused(event):
        global chatrooms_to_display
        increment_chatroom_index()
        event.app.layout.focus(chatrooms_to_display.children[chatroom_index])

def scroll_up_chatroom(event):
    global chatrooms_to_display
    decrement_chatroom_index()
    event.app.layout.focus(chatrooms_to_display.children[chatroom_index])

def scroll_up_message(event):
    if is_messages_focused(event):
        global messages_to_display
        decrement_message_index()
        event.app.layout.focus(messages_to_display.children[message_index])

def scroll_down_message(event):
    if is_messages_focused(event):
        global messages_to_display
        increment_message_index()
        event.app.layout.focus(messages_to_display.children[message_index])

def refresh_message_box(msg: Message): #callback function
    global messages_to_display
    loaded_messages.append(msg)
    messages_to_display.children.append(Window(FormattedTextControl(f"[{msg.sender.nickname}] {msg.msg}")))
    global message_number

    message_number = len(loaded_messages)
    global app
    app.invalidate() #refreshes the UI immediately


def is_message_command():
    global prompt_bar
    text = str(prompt_bar.text)
    return text.startswith("create_chatroom") or text.startswith("delete_chatroom") #TODO: Add new commands

@kb.add(Keys.Enter)
def enter_chatroom(event):
    #TODO: logic to connect to the selected chatroom and load the messages
    if is_chatrooms_focused(event):
        global messages_to_display
        global chatrooms_to_display
        global loaded_messages
        global message_number
        global prompt_bar
        global messages_to_display
        if is_chatrooms_focused(event):
            #LOAD STUFF
            if client.open_chat.id != "0": #if it isn't connected to the server
                loaded_messages = []
                message_number = 0
                client._connect_to_server()

            chatroom_to_connect_to = subscribed_chatrooms[chatroom_index]
            if chatroom_to_connect_to.id != "0":
                loaded_messages = []
                message_number = 0
                messages_to_display.children = []

                connect_request = Message(-1, client.open_chat.id, client.details, f"open_chatroom {chatroom_to_connect_to.id}")
                client.send_msg(connect_request)
            else:
                messages_to_display.children = []
    elif is_messages_focused(event):
        event.app.layout.focus(prompt_bar)
    else:
        text_msg = prompt_bar.text
        if len(text_msg) > 0 and client.open_chat.id != '0' or (client.open_chat.id == '0' and is_message_command()):
            id = ObjectId()
            msg = Message(id, client.open_chat.id, client.details, text_msg) #TODO: make sending passing only the string message
            client.send_msg(msg)
        prompt_bar.text = ""

@kb.add(Keys.Right)
def enter_messages_pane(event):
    global message_index
    global message_number
    if message_number > 0 and is_chatrooms_focused(event):
        message_index = message_number - 1
        event.app.layout.focus(messages_to_display.children[message_index])


@kb.add('c-c')
def back_to_chatrooms(event):
    global chatrooms_to_display
    event.app.layout.focus(chatrooms_to_display.children[chatroom_index])
    #if is_messages_focused(event):

@kb.add('c-t')
def focus_prompt(event):
    global prompt_bar
    if is_chatrooms_focused(event) or is_messages_focused(event):
        event.app.layout.focus(prompt_bar)


@kb.add('c-q')
def i_quit(event):
    client.disconnect()
    event.app.exit()

#------------------------------------------------------------------------------------------------------------------
#------------------------------------------------------------------------------------------------------------------
#------------------------------------------------------------------------------------------------------------------


def tui_app():
    global chatrooms_to_display
    chatrooms_to_display = HSplit(children=[Window(FormattedTextControl(f"{chat.name}")) for chat in subscribed_chatrooms])

    global prompt_bar
    prompt_bar = TextArea(
        prompt='> ',
        multiline=True,
        focus_on_click=True,
        wrap_lines=True,
        scrollbar=True,

    )

    global messages_to_display
    messages_to_display = HSplit(children=[])

    messages_with_prompt = HSplit([
        ScrollablePane(content=messages_to_display),
        prompt_bar
    ])


    # Create the outer layout with scrollable panes
    outer = VSplit([
        ScrollablePane(content=chatrooms_to_display),
        messages_with_prompt,
    ])

    # Create the layout
    layout = Layout(outer)

    # Create the application
    global app
    app = Application(mouse_support=True, layout=layout, full_screen=True, key_bindings=kb)

    # Set the initial focus to the first chatroom window
    layout.focus(chatrooms_to_display.children[0])

    # Run the application
    app.run()


if __name__ == "__main__":
    main()


