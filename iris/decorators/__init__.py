from iris import ChatContext, PyKV

def has_param(func):
    def wrapper(*args,**kwargs):
        chat: ChatContext = args[0]
        return func(*args, **kwargs) if chat.message.has_param else None
    return wrapper

def is_reply(func):
    def wrapper(*args,**kwargs):
        chat: ChatContext = args[0]
        if chat.message.type == 26:
            return func(*args, **kwargs)
        else:
            chat.reply("메세지에 답장하여 요청하세요.")
            return None
    return wrapper

def is_admin(func):
    def wrapper(*args,**kwargs):
        chat = args[0]
        return func(*args, **kwargs) if admin_check(chat) else None
    return wrapper

def is_not_banned(func):
    def wrapper(*args,**kwargs):
        chat: ChatContext = args[0]
        return "" if ban_check(chat) else func(*args, **kwargs)
    return wrapper

def admin_check(chat:ChatContext):
    kv = PyKV()
    admins = kv.get('admin')
    if not admins:
        kv.put('admin', [])
        admins = []
    if len(admins) == 0:
        print("관리자 목록이 비어있는 상태에서 admin 체크가 실행되고 있습니다. iris admin add <user_id> 명령어로 관리자를 추가하세요.")
    res = chat.sender.id in admins
    return res

def ban_check(chat:ChatContext):
    kv = PyKV()
    bans = kv.get('ban')
    if not bans:
        kv.put('ban', [])
        bans = []
    res = chat.sender.id in bans
    return res