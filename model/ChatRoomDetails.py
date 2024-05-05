class ChatRoomDetails: #TODO: can make the ChatRoom extend from this one
    """A ChatRoom instance without the socket components so that it can be sent trough a socket.
     It is the one referenced in the User's open_chat and subscribed_chats"""
    #creator: User
    id: int
    name: str
    subscribed_users: set
    active_users: set #User objects, no sockets
    messages: list#[Message]
    addr: tuple

    def __init__(self, id, name, subscribed_users, active_users, addr, messages=[]):
        self.id = id
        self.name = name
        self.subscribed_users = subscribed_users
        self.active_users = active_users
        self.addr = addr
        self.messages = messages