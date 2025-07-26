# irispy-client

## `iris.Bot`

Iris 봇을 생성하고 관리하기 위한 메인 클래스입니다.

**초기화:**

```python
Bot(iris_url: str, *, max_workers: int = None)
```

- `iris_url` (str): Iris 서버의 URL (예: "127.0.0.1:3000").
- `max_workers` (int, optional): 이벤트를 처리하는 데 사용할 최대 스레드 수.

**메서드:**

- `run()`: 봇을 시작하고 Iris 서버에 연결합니다. 이 메서드는 블로킹 방식입니다.
- `on_event(name: str)`: 이벤트 핸들러를 등록하기 위한 데코레이터입니다.

**이벤트:**

- `chat`: 수신된 모든 메시지에 대해 트리거됩니다.
- `message`: 표준 메시지에 대해 트리거됩니다.
- `new_member`: 새 멤버가 채팅방에 참여할 때 트리거됩니다.
- `del_member`: 멤버가 채팅방을 나갈 때 트리거됩니다.
- `unknown`: 알 수 없는 이벤트 유형에 대해 트리거됩니다.
- `error`: 이벤트 핸들러에서 오류가 발생할 때 트리거됩니다.

---

## `iris.bot.models.Message`

채팅방의 메시지를 나타냅니다.

**속성:**

- `id` (int): 메시지 ID.
- `type` (int): 메시지 유형.
- `msg` (str): 메시지 내용.
- `attachment` (dict): 메시지 첨부 파일.
- `v` (dict): 추가 메시지 데이터.
- `command` (str): 메시지의 명령어 부분 (첫 번째 단어).
- `param` (str): 메시지의 매개변수 부분 (나머지 메시지).
- `has_param` (bool): 메시지에 매개변수가 있는지 여부.
- `image` (ChatImage): 메시지가 이미지인 경우 `ChatImage` 객체, 그렇지 않으면 `None`.

---

## `iris.bot.models.Room`

채팅방을 나타냅니다.

**속성:**

- `id` (int): 방 ID.
- `name` (str): 방 이름.
- `type` (str): 방 유형 (예: "MultiChat", "DirectChat"). 이 속성은 캐시됩니다.

---

## `iris.bot.models.User`

사용자를 나타냅니다.

**속성:**

- `id` (int): 사용자 ID.
- `name` (str): 사용자 이름. 이 속성은 캐시됩니다.
- `avatar` (Avatar): 사용자의 `Avatar` 객체.
- `type` (str): 채팅방에서의 사용자 유형 (예: "HOST", "MANAGER", "NORMAL"). 이 속성은 캐시됩니다.

---

## `iris.bot.models.Avatar`

사용자의 아바타를 나타냅니다.

**속성:**

- `url` (str): 아바타 이미지의 URL. 이 속성은 캐시됩니다.
- `img` (bytes): 아바타 이미지 데이터 (바이트). 이 속성은 캐시됩니다.

---

## `iris.bot.models.ChatImage`

채팅 메시지의 이미지를 나타냅니다.

**속성:**

- `url` (list[str]): 이미지의 URL 목록.
- `img` (list[Image.Image]): 이미지의 `PIL.Image.Image` 객체 목록. 이 속성은 캐시됩니다.

---

## `iris.bot.models.ChatContext`

채팅 이벤트의 컨텍스트를 나타냅니다.

**속성:**

- `room` (Room): 이벤트가 발생한 `Room`.
- `sender` (User): 메시지를 보낸 `User`.
- `message` (Message): `Message` 객체.
- `raw` (dict): 원시 이벤트 데이터.
- `api` (IrisAPI): Iris 서버와 상호 작용하기 위한 `IrisAPI` 인스턴스.

**메서드:**

- `reply(message: str, room_id: int = None)`: 채팅방에 답장을 보냅니다.
- `reply_media(files: list, room_id: int = None)`: 채팅방에 미디어 파일을 보냅니다.
- `get_source()`: 답장하는 메시지의 `ChatContext`를 반환합니다.
- `get_next_chat(n: int = 1)`: 채팅 기록에서 다음 메시지의 `ChatContext`를 반환합니다.
- `get_previous_chat(n: int = 1)`: 채팅 기록에서 이전 메시지의 `ChatContext`를 반환합니다.

---

## `iris.bot.models.ErrorContext`

오류 이벤트의 컨텍스트를 나타냅니다.

**속성:**

- `event` (str): 오류가 발생한 이벤트의 이름.
- `func` (Callable): 오류를 발생시킨 이벤트 핸들러 함수.
- `exception` (Exception): 예외 객체.
- `args` (list): 이벤트 핸들러에 전달된 인수.

---

## `iris.kakaolink.IrisLink`

카카오링크 메시지를 보내기 위한 클래스입니다.

**초기화:**

```python
IrisLink(iris_url: str)
```

- `iris_url` (str): Iris 서버의 URL.

**메서드:**

- `send(receiver_name: str, template_id: int, template_args: dict, **kwargs)`: 카카오링크 메시지를 보냅니다.

**예제:**

```python
from iris import IrisLink

link = IrisLink("127.0.0.1:3000")
link.send(
    receiver_name="내 채팅방",
    template_id=12345,
    template_args={"key": "value"}
)
```

---

## `iris.util.PyKV`

SQLite를 사용하는 간단한 키-값 저장소입니다. 이 클래스는 싱글톤입니다.

**메서드:**

- `get(key: str)`: 저장소에서 값을 검색합니다.
- `put(key: str, value: any)`: 키-값 쌍을 저장합니다.
- `delete(key: str)`: 키-값 쌍을 삭제합니다.
- `search(searchString: str)`: 값에서 문자열을 검색합니다.
- `search_json(valueKey: str, searchString: str)`: JSON 객체의 값에서 문자열을 검색합니다.
- `search_key(searchString: str)`: 키에서 문자열을 검색합니다.
- `list_keys()`: 모든 키의 목록을 반환합니다.
- `close()`: 데이터베이스 연결을 닫습니다.

## `iris.decorators`

함수에 추가적인 기능을 제공하는 데코레이터입니다.

- `@has_param`: 메시지에 파라미터가 있는 경우에만 함수를 실행합니다.
- `@is_reply`: 메시지가 답장일 경우에만 함수를 실행합니다. 답장이 아닐 경우 "메세지에 답장하여 요청하세요."라는 메시지를 자동으로 보냅니다.
- `@is_admin`: 메시지를 보낸 사용자가 관리자인 경우에만 함수를 실행합니다.
- `@is_not_banned`: 메시지를 보낸 사용자가 차단되지 않은 경우에만 함수를 실행합니다.

## Special Thanks
Irispy2 and Kakaolink by @ye-seola
