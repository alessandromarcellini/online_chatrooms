from bson import ObjectId

class ChatRoomDetails: #TODO: can make the ChatRoom extend from this one
    """A ChatRoom instance without the socket components so that it can be sent trough a socket.
     It is the one referenced in the User's open_chat and subscribed_chats"""
    #creator: User
    id: ObjectId
    owner: ObjectId
    name: str
    subscribed_users: set
    active_users: set #User objects, no sockets
    messages: list#[Message]
    addr: tuple
    is_active: bool

    def __init__(self, id, owner, name, subscribed_users, addr=None, messages=[], active_users=set(), is_active=True):
        self.id = id
        self.owner = owner
        self.name = name
        self.subscribed_users = subscribed_users
        self.active_users = active_users
        self.addr = addr
        self.messages = messages
        self.is_active = is_active