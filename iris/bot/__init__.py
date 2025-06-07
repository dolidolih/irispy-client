import json
import time
from dataclasses import dataclass
import typing as t

from websockets.sync.client import connect
from iris.bot._internal.emitter import EventEmitter
from iris.bot._internal.iris import IrisAPI, IrisRequest
from iris.bot.models import ChatContext, Message, Room, User

class Bot:
    def __init__(self, iris_url: str, *, max_workers=None):
        self.emitter = EventEmitter(max_workers=max_workers)

        self.iris_url = iris_url.replace(
                "http://",
                "",
            ).replace(
                "https://",
                "",
            ).replace(
                "ws://",
                "",
            ).replace(
                "wss://",
                "",
            )
        if self.iris_url.endswith("/"):
            self.iris_url = self.iris_url[:-1]

        url_split = self.iris_url.split(":")
        if len(url_split) != 2 or len(url_split[0].split(".")) != 4:
            raise ValueError("Iris endpoint 주소는 IP:PORT 형식이어야 합니다. ex) 172.30.10.66:3000")

        self.iris_ws_endpoint = f"ws://{self.iris_url}/ws"
        self.api = IrisAPI(f"http://{self.iris_url}")

    def __process_chat(self, chat: ChatContext):
        self.emitter.emit("chat", [chat])

        origin = chat.message.v.get("origin")
        if origin == "MSG":
            self.emitter.emit("message", [chat])
        elif origin == "NEWMEM":
            self.emitter.emit("new_member", [chat])
        elif origin == "DELMEM":
            self.emitter.emit("del_member", [chat])
        else:
            self.emitter.emit("unknown", [chat])

    def __process_iris_request(self, req: IrisRequest):
        v = {}
        try:
            v = json.loads(req.raw["v"])
        except Exception:
            pass

        room = Room(
            id=int(req.raw["chat_id"]),
            name=req.room,
            api=self.api,
        )
        sender = User(
            id=int(req.raw["user_id"]),
            chat_id=room.id,
            api=self.api,
            name=req.sender,
            bot_id=self.bot_id,
        )
        message = Message(
            id=int(req.raw["id"]),
            type=int(req.raw["type"]),
            msg=req.raw["message"],
            attachment=req.raw["attachment"],
            v=v,
        )

        chat = ChatContext(
            room=room, sender=sender, message=message, raw=req.raw, api=self.api, _bot_id=self.bot_id
        )
        self.__process_chat(chat)

    def run(self):
        while True:
            try:
                with connect(self.iris_ws_endpoint, close_timeout=0) as ws:
                    print("웹소켓에 연결되었습니다")
                    self.bot_id = self.api.get_info()["bot_id"]
                    while True:
                        recv = ws.recv()
                        try:
                            data: dict = json.loads(recv)
                            data["raw"] = data.get("json")
                            del data["json"]

                            self.__process_iris_request(IrisRequest(**data))
                        except Exception as e:
                            print(
                                "Iris 이벤트를 처리 중 오류가 발생했습니다: {}", e
                            )
            except KeyboardInterrupt:
                print("웹소켓 연결을 종료합니다")
                break
            
            except Exception as e:
                print("웹소켓 연결 오류: {}", e)
                print("3초 후 재연결합니다")

            time.sleep(3)

    def on_event(self, name: str):
        def decorator(func: t.Callable):
            self.emitter.register(name, func)

            def wrapper(*args, **kwargs):
                return func(*args, **kwargs)

            return wrapper

        return decorator

