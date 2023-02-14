# -*- coding: utf-8 -*-
# @Name    : main
# @Author  : Malei
# @Email   : malei@anban.tech
# @Time    : 2022-07-14 上午10:20

import os
import typing

from configparser import ConfigParser

import constants
from moniter.bad_fd import MonitorBadFd
from transfer.reader import TransferReader, ManagerReader
from transfer.client import TransferClient2Simu, TransferClient2Platform, YFCoreClient, TransferClient2PlatformF2
from transfer.server import Server, TransferServer
from logger import crash_logger, logger
from transfer.utils import read_cache


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
        self.transfer_client_to_simu = TransferClient2Simu(host=edst_host, port=edst_port)
        self.transfer_client_to_platform = TransferClient2Platform()
        self.transfer_client_to_platform_f2 = TransferClient2PlatformF2()
        self.transfer_server = TransferServer(host=self.host, port=transfer_port, reader=TransferReader)
        self.init_transfer()

    def init_transfer(self) -> typing.NoReturn:
        self.transfer_client_to_simu.start()
        self.transfer_client_to_platform.start()
        self.transfer_client_to_platform_f2.start()
        self.transfer_server.start()
        MonitorBadFd().start()

    def run(self) -> typing.NoReturn:
        self.init_cache()
        with Server(port=self.port, reader=ManagerReader) as service:
            service.serve_forever()

    @staticmethod
    def init_cache():
        logger.info("加载本地缓存")
        cache = read_cache()
        for client, value in cache.items():
            prod, ip, port, _, sender_id, task_id = value
            if prod == "callback_serv":
                os.environ.setdefault("callback_serv", str({"ip": ip, "port": port}))
            elif prod == "yf":
                cli = YFCoreClient(host=ip, port=port)
                constants.ClientMap[eval(client)] = ("yf", cli)
                constants.TaskMap[eval(client)] = [sender_id, task_id]


if __name__ == '__main__':
    Parser = ConfigParser()
    Parser.readfp(open('./config.ini'))
    host = Parser.get("Server", "LocalHost")
    port = Parser.get("Server", "ServerPort")
    level = 10 if Parser.get("Server", "Debug") in [True, 1, "1", "TRUE", "True", "true", "t",
                                                    "T"] else 20
    logger.level = level
    crash_logger.level = level
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
