import asyncio
from .KakaoLinkModule import KakaoLink
import os
import typing as t
from iris.util.pykv import PyKV

class IrisLink:
    def __init__(
        self,
        iris_url: str,
    ):
        try:
            self.kv = PyKV()
            self.iris_url = iris_url
            config = self.kv.get("kakaolink_config")
            if type(config) != dict or "app_key" not in config.keys() or "origin" not in config.keys():
                raise ValueError("KakaoLink app key or origin not found in PyKV. iris kakaolink <app_key> <origin> 명령어로 설정해주세요.")
            self.client = KakaoLink(
                iris_url=iris_url,
                default_app_key=config["app_key"],
                default_origin=config["origin"],
            )
            asyncio.run(self.client.init())
        except Exception as e:
            print(f"Error initializing KakaoLink: {e}")
        
    def send(
        self,
        receiver_name: str,
        template_id: int,
        template_args: dict,
        app_key: str | None = None,
        origin: str | None = None,
        search_exact: bool = True,
        search_from: t.Union[
            t.Literal["ALL"], t.Literal["FRIENDS"], t.Literal["CHATROOMS"]
        ] = "ALL",
        search_room_type: t.Union[
            t.Literal["ALL"],
            t.Literal["OpenMultiChat"],
            t.Literal["MultiChat"],
            t.Literal["DirectChat"],
        ] = "ALL"
    ):
        asyncio.run(
            self.client.send(
                receiver_name=receiver_name,
                template_id=template_id,
                template_args=template_args,
                app_key=app_key,
                origin=origin,
                search_exact=search_exact,
                search_from=search_from,
                search_room_type=search_room_type,
            )
        )
    
    def __repr__(self):
        return f"<IrisLink(iris_url={self.iris_url})>"
        
    