#https://github.com/ye-seola/kakaolink-py
import abc
import asyncio
import base64
import json
import logging
from uuid import uuid4
from urllib.parse import quote
import typing as t
import httpx
import requests

logger = logging.getLogger("KakaoLink")

KAKAOTALK_VERSION = "25.2.1"
ANDROID_SDK_VER = 33
ANDROID_WEBVIEW_UA = "Mozilla/5.0 (Linux; Android 13; SM-G998B Build/TP1A.220624.014; wv) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/114.0.5735.60 Mobile Safari/537.36"


class KakaoLinkException(Exception):
    pass


class KakaoLinkReceiverNotFoundExcepetion(KakaoLinkException):
    pass


class KakaoLinkLoginExcepetion(KakaoLinkException):
    pass


class KakaoLink2FAExcepetion(KakaoLinkException):
    pass


class KakaoLinkSendExcepetion(KakaoLinkException):
    pass


class KakaoLinkCookieStorage:
    def __init__(self):
        self.local_storage = {}

    async def save(self, cookies):
        self.local_storage = cookies

    async def load(self):
        return self.local_storage
    
    def clear(self):
        self.local_storage = {}

class KakaoLinkAuthorizationProvider:
    def __init__(self, iris_url: str):
        self.iris_url = f"http://{iris_url}"
        
    async def get_authorization(self) -> str:
        aot = requests.get(f"{self.iris_url}/aot").json()["aot"]
        access_token = f"{aot['access_token']}-{aot['d_id']}"
        return access_token


class KakaoLink:
    def __init__(
        self,
        iris_url: str,
        default_app_key: str | None = None,
        default_origin: str | None = None,
    ):
        self.default_app_key = default_app_key
        self.default_origin = default_origin

        self._cookies = {}
        self._send_lock = asyncio.Lock()
        self._authorization_provider = KakaoLinkAuthorizationProvider(iris_url)
        self._cookie_storage = KakaoLinkCookieStorage()

    async def send(
        self,
        receiver_name: str,
        template_id: int,
        template_args: dict,
        app_key: str | None = None,
        origin: str | None = None,
        search_exact=True,
        search_from: t.Union[
            t.Literal["ALL"], t.Literal["FRIENDS"], t.Literal["CHATROOMS"]
        ] = "ALL",
        search_room_type: t.Union[
            t.Literal["ALL"],
            t.Literal["OpenMultiChat"],
            t.Literal["MultiChat"],
            t.Literal["DirectChat"],
        ] = "ALL",
    ):
        app_key = app_key or self.default_app_key
        origin = origin or self.default_origin

        if not app_key or not origin:
            raise KakaoLinkException("app_key 또는 origin은 비어있을 수 없습니다")

        ka = self._get_ka(origin)

        async with self._send_lock:
            async with httpx.AsyncClient(cookies=self._cookies) as client:
                picker_data = await self._get_picker_data(
                    client, app_key, ka, template_id, template_args
                )

                try:
                    checksum = picker_data["checksum"]
                    csrf = picker_data["csrfToken"]
                    short_key = picker_data["shortKey"]
                except KeyError:
                    logging.error(
                        "카카오링크 전송: 전송 실패 (%s)", picker_data, exc_info=True
                    )
                    raise KakaoLinkSendExcepetion()

                receiver = self._picker_data_search(
                    receiver_name,
                    picker_data,
                    search_exact,
                    search_from,
                    search_room_type,
                )

                await self._picker_send(
                    client, app_key, short_key, checksum, csrf, receiver
                )

    async def _picker_send(
        self,
        client: httpx.AsyncClient,
        app_key: str,
        short_key: str,
        checksum: str,
        csrf: str,
        receiver: dict,
    ):
        res = await client.post(
            "https://sharer.kakao.com/picker/send",
            data={
                "app_key": app_key,
                "short_key": short_key,
                "checksum": checksum,
                "_csrf": csrf,
                "receiver": base64.urlsafe_b64encode(
                    json.dumps(receiver, ensure_ascii=False).encode()
                ).decode(),
            },
        )

        if res.status_code == 400:
            logger.error(
                "카카오링크 전송: 전송 실패 (%s)", res.status_code, stack_info=True
            )
            raise KakaoLinkSendExcepetion()

    def _picker_data_search(
        self,
        receiver_name: str,
        picker_data: dict,
        search_exact: bool,
        search_from: t.Union[
            t.Literal["ALL"], t.Literal["FRIENDS"], t.Literal["CHATROOMS"]
        ],
        search_room_type: t.Union[
            t.Literal["ALL"],
            t.Literal["OpenMultiChat"],
            t.Literal["MultiChat"],
            t.Literal["DirectChat"],
        ],
    ) -> dict:
        for receiver in [
            *(picker_data["chats"] if search_from in ["ALL", "CHATROOMS"] else []),
            *(picker_data["friends"] if search_from in ["ALL", "FRIENDS"] else []),
        ]:
            receiver: dict

            current_chat_type = receiver.get("chat_room_type")
            current_title = receiver.get("title") or receiver.get(
                "profile_nickname", ""
            )

            # 챗방일 때
            if current_chat_type:
                # 검색할 방 타입이 특정되어있고 현재 타입이랑 다를 떄
                if search_room_type != "ALL" and search_room_type != current_chat_type:
                    continue

            if search_exact:
                if current_title == receiver_name:
                    return receiver
            else:
                if receiver_name in current_title:
                    return receiver

        raise KakaoLinkReceiverNotFoundExcepetion()

    async def _get_picker_data(
        self,
        client: httpx.AsyncClient,
        app_key: str,
        ka: str,
        template_id: int,
        template_args: dict,
    ) -> dict:
        res = await client.post(
            "https://sharer.kakao.com/picker/link",
            headers={**self._get_web_headers()},
            data={
                "app_key": app_key,
                "ka": ka,
                "validation_action": "custom",
                "validation_params": json.dumps(
                    {
                        "link_ver": "4.0",
                        "template_id": template_id,
                        "template_args": template_args,
                    },
                    ensure_ascii=False,
                ),
            },
            follow_redirects=True,
        )

        if res.url.path.startswith("/login"):
            continue_url = res.url.params.get("continue")
            await self._login(client)

            res = await client.get(
                continue_url,
                headers={**self._get_web_headers()},
                follow_redirects=True,
            )

        if res.url.path.startswith("/talk_tms_auth/service"):
            logger.info("카카오링크 전송: 추가인증 해결 중")
            continue_url = await self._solve_two_factor_auth(client, res.text)

            res = await client.get(
                continue_url,
                headers={**self._get_web_headers()},
                follow_redirects=True,
            )

        return json.loads(
            base64.urlsafe_b64decode(
                res.text.split('window.serverData = "')[1].split('"')[0].strip()
                + "===="
            )
        )["data"]

    async def init(self):
        self._cookies = await self._cookie_storage.load()

        async with httpx.AsyncClient(cookies=self._cookies) as client:
            await self._login(client)

    async def _login(self, client: httpx.AsyncClient):
        authorization = await self._authorization_provider.get_authorization()
        self._cookies = {}
        self._cookie_storage.clear()
        client.cookies.clear()

        authorized = await self._check_authorized(client)
        if authorized:
            return

        tgt_token = await self._get_tgt_token(client, authorization)
        await self._submit_tgt_token(client, tgt_token)

        authorized = await self._check_authorized(client)
        if not authorized:
            logger.error(
                "카카오링크 로그인: 알 수 없는 이유로 로그인이 되지 않았습니다 (%s)",
                stack_info=True,
            )
        
        self._cookies = dict(client.cookies)
        await self._cookie_storage.save(self._cookies)

    async def _solve_two_factor_auth(self, client: httpx.AsyncClient, tfa_html: str):
        try:
            props = json.loads(
                tfa_html.split('<script id="__NEXT_DATA__" type="application/json">')[1]
                .split("</script>")[0]
                .strip()
            )

            context = props["props"]["pageProps"]["pageContext"]["context"]
            common_context = props["props"]["pageProps"]["pageContext"]["commonContext"]

            token = context["token"]
            continueUrl = context["continueUrl"]
            csrf = common_context["_csrf"]
        except Exception:
            logger.error(
                "카카오링크 추가인증: 추가인증 토큰 파싱 실패",
                exc_info=True,
            )
            raise KakaoLink2FAExcepetion()

        await self._confirm_token(client, token)

        res = await client.post(
            "https://accounts.kakao.com/api/v2/talk_tms_auth/poll_from_service.json",
            headers={**self._get_web_headers()},
            json={
                "_csrf": csrf,
                "token": token,
            },
        )

        res_json: dict = res.json()
        status = res_json.get("status")
        if status != 0:
            logger.error(
                "카카오링크 추가인증: 알 수 없는 오류 (%s)", status, exc_info=True
            )
            raise KakaoLink2FAExcepetion()

        return continueUrl

    async def _confirm_token(self, client: httpx.AsyncClient, two_factor_token: str):
        res = await client.get(
            "https://auth.kakao.com/fa/main.html",
            params={
                "os": "android",
                "country_iso": "KR",
                "lang": "ko",
                "v": KAKAOTALK_VERSION,
                "os_version": ANDROID_SDK_VER,
                "page": "additional_auth_with_token",
                "additional_auth_token": two_factor_token,
                "close_on_completion": "true",
                "talk_tms_auth_type": "from_service",
            },
        )

        try:
            csrf = (
                res.text.split('<meta name="csrf-token" content="')[1]
                .split('"')[0]
                .strip()
            )

            data = json.loads(
                res.text.split("var options =")[1]
                .split("new PageBuilder()")[0]
                .strip("; \t\n")
            )
        except Exception:
            logger.error(
                "카카오 링크 추가인증: csrf, client_id 데이터 파싱 실패", exc_info=True
            )
            raise KakaoLink2FAExcepetion()

        res = await client.post(
            "https://auth.kakao.com/talk_tms_auth/confirm_token.json",
            data={
                "client_id": data["client_id"],
                "lang": "ko",
                "os": "android",
                "v": KAKAOTALK_VERSION,
                "webview_v": "2",
                "token": data["additionalAuthToken"],
                "talk_tms_auth_type": "from_service",
                "authenticity_token": csrf,
            },
        )

        res_json: dict = res.json()
        status = res_json.get("status")
        if status != 0:
            logger.error(
                "카카오링크 추가인증: 알 수 없는 오류 (%s)", status, exc_info=True
            )
            raise KakaoLink2FAExcepetion()

    async def _check_authorized(self, client: httpx.AsyncClient):
        res = await client.get(
            "https://e.kakao.com/api/v1/users/me",
            headers={
                **self._get_web_headers(),
                "referer": "https://e.kakao.com/",
            },
        )

        res_json: dict = res.json()
        result: dict = res_json.get("result", {})
        
        if result.get("status") == "VALID":
            return True
        else:
            return False

    async def _submit_tgt_token(self, client: httpx.AsyncClient, tgt_token: str):
        res = await client.get(
            "https://e.kakao.com",
            headers={
                **self._get_web_headers(),
                "ka-tgt": tgt_token,
            },
        )

        res.raise_for_status()

    async def _get_tgt_token(self, client: httpx.AsyncClient, token: str):
        res = await client.post(
            "https://api-account.kakao.com/v1/auth/tgt",
            headers={
                **self._get_app_headers(token),
            },
            data={
                "key_type": "talk_session_info",
                "key": token,
                "referer": "talk",
            },
        )

        res_json: dict = res.json()

        if res_json.get("code") != 0:
            logger.error(
                "카카오링크 로그인: tgt 토큰 발급 중 오류가 발생했습니다 (%s)",
                res_json,
                stack_info=True,
            )
            raise KakaoLinkLoginExcepetion()

        return res_json["token"]

    def _get_ka(self, origin: str):
        return f"sdk/1.43.5 os/javascript sdk_type/javascript lang/ko-KR device/Linux armv7l origin/{quote(origin)}"

    def _get_app_headers(self, token: str):
        return {
            "A": f"android/{KAKAOTALK_VERSION}/ko",
            "C": str(uuid4()),
            "User-Agent": f"KT/{KAKAOTALK_VERSION} An/13 ko",
            "Authorization": token,
        }

    def _get_web_headers(self):
        return {
            "User-Agent": f"{ANDROID_WEBVIEW_UA} KAKAOTALK/{KAKAOTALK_VERSION} (INAPP)",
            "X-Requested-With": "com.kakao.talk",
        }