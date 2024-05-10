class UserDetails:
    id: int #unique =>make it a str and get it from the nickname
    nickname: str
    subscribed_chats: set #list of ChatRoom (Details) which the user is subscribed to

    def __init__(self, id, nickname, subscribed_chats=set()):
        self.id = id
        self.nickname = nickname
        self.subscribed_chats = subscribed_chats