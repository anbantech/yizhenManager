# -*- coding: utf-8 -*-
# @Name    : main
# @Author  : Malei
# @Email   : malei@anban.tech
# @Time    : 2022-07-14 上午10:20


import logging
import selectors
import socket
import threading
import typing

from transfer.reader import ManagerReader

if hasattr(selectors, 'EpollSelector'):
    Selector = selectors.EpollSelector
elif hasattr(selectors, "PollSelector"):
    Selector = selectors.PollSelector
else:
    Selector = selectors.SelectSelector

logger = logging.getLogger("Logger")


class Server(threading.Thread):
    request_queue_size = 500

    def __init__(
            self,
            host: typing.Optional[str] = "0.0.0.0",
            port: typing.Optional[int] = 7000,
            reader: typing.Type[ManagerReader] = None,
            daemon: typing.Optional[bool] = True,
            *args: typing.Optional[typing.Any],
            **kwargs: typing.Optional[typing.Any]
    ) -> typing.NoReturn:
        threading.Thread.__init__(self, daemon=daemon, *args, **kwargs)
        self.server_address = (host, port)
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self._shutdown = False
        self._reader = reader
        try:
            self.server_bind()
        except:
            self.server_close()
            raise

    def server_bind(self) -> typing.NoReturn:
        self.socket.bind(self.server_address)
        self.socket.listen(self.request_queue_size)

    def server_close(self) -> typing.NoReturn:
        self.socket.close()

    def fileno(self) -> int:
        return self.socket.fileno()

    def serve_forever(self, poll_interval: typing.Optional[float] = 0.5) -> typing.NoReturn:
        try:
            with Selector() as selector:
                selector.register(self, selectors.EVENT_READ)
                while not self._shutdown:
                    ready = selector.select(poll_interval)
                    if self._shutdown:
                        break
                    if ready:
                        client, addr = self.socket.accept()
                        self._reader(client).start()
        finally:
            self._shutdown = False

    def run(self) -> typing.NoReturn:
        self.serve_forever(poll_interval=0.5)

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.server_close()


class TransferServer(Server):
    pass
