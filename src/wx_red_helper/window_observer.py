from typing import Protocol

from wx_red_helper.models import ClientRect, WindowSnapshot


class ForegroundWindowApi(Protocol):
    def foreground_handle(self) -> int: ...

    def is_visible(self, handle: int) -> bool: ...

    def is_minimized(self, handle: int) -> bool: ...

    def title(self, handle: int) -> str: ...

    def client_rect_on_screen(self, handle: int) -> ClientRect: ...


class WechatWindowObserver:
    def __init__(self, api: ForegroundWindowApi, title_tokens: tuple[str, ...]) -> None:
        self._api = api
        self._title_tokens = tuple(token.casefold() for token in title_tokens if token.strip())

    def observe(self) -> WindowSnapshot | None:
        handle = self._api.foreground_handle()
        if not handle or not self._api.is_visible(handle) or self._api.is_minimized(handle):
            return None

        title = self._api.title(handle)
        if not title or not any(token in title.casefold() for token in self._title_tokens):
            return None

        try:
            client_rect = self._api.client_rect_on_screen(handle)
        except OSError:
            return None

        revision = hash((handle, title, client_rect))
        return WindowSnapshot(handle, title, client_rect, revision)
