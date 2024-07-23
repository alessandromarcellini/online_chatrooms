from dotenv import dotenv_values
from model.ChatRoomDetails import ChatRoomDetails
from model.Message import Message
from model.User import User
#---------------------------------------PROMPT TOOLKIT IMPORTS-------------------------------------------------------
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
#-----------------------------------
from bson import ObjectId

from typing import List

config = dotenv_values(".env")

MONGODB_CONNECT = config["MONGODB_CONNECT"]

UP = 1
DOWN = -1

class TUI:
    client: User

    subscribed_chatrooms: List[ChatRoomDetails]
    chatroom_index: int

    loaded_messages: List[Message]
    message_index: int

    #---------------------------
    kb: KeyBindings
    messages_to_display: HSplit
    messages_with_prompt: HSplit
    prompt_bar: TextArea
    app: Application

    def __init__(self, client: User):
        #INITIALIZATION
        self.client = client
        self.kb = KeyBindings()
        # subscribed_chatrooms = list(client.subscribed_chats)
        self.loaded_messages = []

        self.chatroom_index = 0
        self.message_index = len(self.loaded_messages) - 1
        client.register_callback(self._refresh_message_box)
        #--------------------------------------------------
        self.kb.add(Keys.Up)(lambda event: self.scroll_up(event))
        self.kb.add(Keys.Down)(lambda event: self.scroll_down(event))
        self.kb.add(Keys.Enter)(lambda event: self._enter_chatroom(event))
        self.kb.add(Keys.Right)(lambda event: self._enter_messages_pane(event))
        self.kb.add('c-c')(lambda event: self.back_to_chatrooms(event))
        self.kb.add('c-t')(lambda event: self.focus_prompt(event))
        self.kb.add('c-q')(lambda event: self.i_quit(event))

#-------------------------------------------PRIVATE FUNCTIONS---------------------------------------------
    def _refresh_message_box(self, msg: Message): #callback function
        self.loaded_messages.append(msg)
        self.messages_to_display.children.append(Window(FormattedTextControl(f"[{msg.sender.nickname}] {msg.msg}")))
        self.app.invalidate()

    def _is_chatrooms_focused(self, event):
        """Returns True if the chatrooms_to_display panel is currently focused"""
        current_focus = event.app.layout.current_window
        return current_focus in self.chatrooms_to_display.children

    def _is_messages_focused(self, event):
        """Returns True if the messages_to_display panel is currently focused"""
        current_focus = event.app.layout.current_window
        return current_focus in self.messages_to_display.children

    def _is_message_command(self):
        text = str(self.prompt_bar.text)
        return text.startswith("create_chatroom") or text.startswith("delete_chatroom")  # TODO: Add new commands

    def _scroll_down_chatroom(self, event):
        if self._is_chatrooms_focused(event):
            self._increment_chatroom_index()
            event.app.layout.focus(self.chatrooms_to_display.children[self.chatroom_index])

    def _scroll_up_chatroom(self, event):
        self._decrement_chatroom_index()
        event.app.layout.focus(self.chatrooms_to_display.children[self.chatroom_index])

    def _scroll_up_message(self, event):
        if self._is_messages_focused(event):
            self._decrement_message_index()
            event.app.layout.focus(self.messages_to_display.children[self.message_index])

    def _scroll_down_message(self, event):
        if self._is_messages_focused(event):
            self._increment_message_index()
            event.app.layout.focus(self.messages_to_display.children[self.message_index])

    def _increment_chatroom_index(self):
        if self.chatroom_index < len(self.subscribed_chatrooms) - 1:
            self.chatroom_index += 1
            self.highlight_selected_chatroom(DOWN)

    def _decrement_chatroom_index(self):
        if self.chatroom_index > 0:
            self.chatroom_index -= 1
            self.highlight_selected_chatroom(UP)

    def _increment_message_index(self):
        if self.message_index < len(self.loaded_messages) - 1:
            self.message_index += 1

    def _decrement_message_index(self):
        if self.message_index > 0:
            self.message_index -= 1

    # def get_focused_pane(self):
    #     focus = self.app.layout.current_window
    #     if focus in self.chatrooms_to_display.children:
    #         return "chatrooms_to_display"
    #     elif focus in self.messages_to_display.children:
    #         return "messages_to_display"
    #     return None



    def highlight_selected_chatroom(self, direction: int):
        self.chatrooms_to_display.children[self.chatroom_index].content.style = "bg:white fg:black"
        if self.chatroom_index + direction >= 0:
            self.chatrooms_to_display.children[self.chatroom_index + direction].content.style = ""



#-----------------------------------------KEY BINDING FUNCTIONS-------------------------------------------
    def scroll_up(self, event):
        if self._is_chatrooms_focused(event):
            self._scroll_up_chatroom(event)
        elif self._is_messages_focused(event):
            self._scroll_up_message(event)

    def scroll_down(self, event):
        if self._is_chatrooms_focused(event):
            self._scroll_down_chatroom(event)
        elif self._is_messages_focused(event):
            self._scroll_down_message(event)

    def _enter_chatroom(self, event):
        #TODO: logic to connect to the selected chatroom and load the messages
        if self._is_chatrooms_focused(event):
            if self._is_chatrooms_focused(event):
                #LOAD STUFF
                if self.client.open_chat.id != "0": #if it isn't connected to the server
                    self.loaded_messages = []
                    self.message_number = 0
                    self.client._connect_to_server()

                chatroom_to_connect_to = self.subscribed_chatrooms[self.chatroom_index]
                if chatroom_to_connect_to.id != "0":
                    self.loaded_messages = []
                    self.messages_to_display.children = []

                    connect_request = Message(-1, self.client.open_chat.id, self.client.details, f"open_chatroom {chatroom_to_connect_to.id}")
                    self.client.send_msg(connect_request)
                else:
                    self.messages_to_display.children = []
        elif self._is_messages_focused(event):
            event.app.layout.focus(self.prompt_bar)
        else:
            text_msg = self.prompt_bar.text
            if len(text_msg) > 0 and self.client.open_chat.id != '0' or (self.client.open_chat.id == '0' and self._is_message_command()):
                id = ObjectId()
                msg = Message(id, self.client.open_chat.id, self.client.details, text_msg) #TODO: make sending passing only the string message
                self.client.send_msg(msg)
            self.prompt_bar.text = ""

    def _enter_messages_pane(self, event):
        if len(self.loaded_messages) > 0 and self._is_chatrooms_focused(event):
            self.message_index = len(self.loaded_messages) - 1
            event.app.layout.focus(self.messages_to_display.children[self.message_index])

    def back_to_chatrooms(self, event):
        event.app.layout.focus(self.chatrooms_to_display.children[self.chatroom_index])

    def focus_prompt(self, event):
        if self._is_chatrooms_focused(event) or self._is_messages_focused(event):
            event.app.layout.focus(self.prompt_bar)

    def i_quit(self, event):
        self.client.disconnect()
        event.app.exit()


#--------------------------------------------PUBLIC FUNCTIONS-------------------------------------------
    def tui_login(self):
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

    def tui_register(self):
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

    def run(self):
        L_R = input("Register/Login (R/l): ").lower()

        if L_R == "l":
            nickname, pwd = self.tui_login()
            self.client.login(nickname, pwd)

            self.subscribed_chatrooms = list(self.client.subscribed_chats)
        else:
            nickname, pwd, confirm_pwd = self.tui_register()
            self.client.register(nickname, pwd, confirm_pwd)
        self.subscribed_chatrooms = list(self.client.subscribed_chats)
        self.client.register_callback(self._refresh_message_box)
        # ---------------------------------------------------

        self.chatrooms_to_display = HSplit(
            children=[Window(FormattedTextControl(f"{chat.name}")) for chat in self.subscribed_chatrooms])

        self.prompt_bar = TextArea(
            prompt='> ',
            multiline=True,
            focus_on_click=True,
            wrap_lines=True,
            scrollbar=True,

        )

        self.messages_to_display = HSplit(children=[])

        self.messages_with_prompt = HSplit([
            ScrollablePane(content=self.messages_to_display),
            self.prompt_bar
        ])

        outer = VSplit([
            ScrollablePane(content=self.chatrooms_to_display),
            self.messages_with_prompt,
        ])

        # Create the layout
        layout = Layout(outer)

        self.app = Application(mouse_support=True, layout=layout, full_screen=True, key_bindings=self.kb)
        layout.focus(self.chatrooms_to_display.children[0])
        self.app.run()


