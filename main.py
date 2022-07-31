# -*- coding: utf-8 -*-
# @Name    : main
# @Author  : Malei
# @Email   : malei@anban.tech
# @Time    : 2022-07-14 上午10:20

import os
import typing

from configparser import ConfigParser

from transfer.reader import TransferReader, ManagerReader
from transfer.client import TransferClient
from transfer.server import Server, TransferServer


class Manager(object):
    def __init__(
            self,
            edst_host: typing.Optional[str],
            edst_port: typing.Optional[int],
            host: typing.Optional[str] = "0.0.0.0",
            port: typing.Optional[int] = 7000,
            transfer_port: typing.Optional[int] = 7001,
    ) -> typing.NoReturn:
        self.host = host
        self.port = port
        self.transfer_client = TransferClient(host=edst_host, port=edst_port)
        self.transfer_server = TransferServer(host=self.host, port=transfer_port, reader=TransferReader)
        self.init_transfer()

    def init_transfer(self) -> typing.NoReturn:
        self.transfer_client.start()
        self.transfer_server.start()

    def run(self) -> typing.NoReturn:
        with Server(port=self.port, reader=ManagerReader) as service:
            service.serve_forever()


if __name__ == '__main__':
    Parser = ConfigParser()
    Parser.readfp(open('./config.ini'))
    host = Parser.get("Server", "LocalHost")
    port = Parser.get("Server", "ServerPort")
    transfer_port = Parser.get("Server", "TransferPort")
    edst_host = Parser.get("EDST", "Host")
    edst_port = Parser.get("EDST", "Port")
    os.environ["localhost"] = host
    os.environ["transfer_port"] = transfer_port

    manager = Manager(
        host=host,
        port=int(port),
        transfer_port=int(transfer_port),
        edst_host=edst_host,
        edst_port=int(edst_port)
    )

    manager.run()
