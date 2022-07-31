# -*- coding: utf-8 -*-
# @Name    : transfer
# @Author  : Malei
# @Email   : malei@anban.tech
# @Time    : 2022-07-14 上午11:30


import os
import socket
import struct
import threading
import typing

import constants

from logger import logger


class TransferClient(threading.Thread):

    def __init__(
            self,
            host: str,
            port: int,
            daemon: typing.Optional[bool] = True,
            *args: typing.Any,
            **kwargs: typing.Any
    ) -> typing.NoReturn:
        threading.Thread.__init__(self, daemon=daemon, *args, **kwargs)
        self.host = host
        self.port = port
        self._sock = None
        self.notify = False
        self.open()

    def send_ident(self, data: bytes) -> typing.NoReturn:
        """
        发送08报文
        :param data:
        :return:
        """
        header = data[4:27]
        replace = bytearray(header)
        replace[1] = 0x0
        replace[6:14] = bytes(8)
        replace[14] = 0x08
        new_header = bytes(replace)
        localhost = os.environ.get("localhost")
        transfer_port = os.environ.get("transfer_port")
        ip = bytes(list(map(int, localhost.split(".")))[::-1])
        port = struct.pack("<H", int(transfer_port))
        product = self.get_product_id(header[2:6])
        body = product + b'\x00' + ip + port + b"\r\n"
        task_08 = new_header + body
        packet = struct.pack("<L", len(task_08)) + task_08
        logger.info("初始化，开始下发给仿真08指令，Mgrserver->%s:%s" % (localhost, transfer_port))
        logger.info("初始化，开始下发给仿真08指令，报文->%s" % packet)
        self._sock.sendall(packet)
        self.notify = True

    def open(self) -> typing.NoReturn:
        while True:
            try:
                self._sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                self._sock.connect((self.host, self.port))
            except Exception:
                logger.error("仿真连接失败，重试中！")
                continue
            else:
                logger.info("仿真连接成功")
                break

    def close(self) -> typing.NoReturn:
        self._sock.close()

    def run(self) -> typing.NoReturn:
        while True:
            try:
                packet = constants.MsgQueue.get(block=False)
            except Exception:
                continue
            if not self.notify:
                self.send_ident(packet)
            while True:
                try:
                    logger.info("获取到新的消息:%s" % packet)
                    logger.info("Mgr开始向仿真发送报文")
                    self._sock.sendall(packet)
                    logger.info("Mgr向仿真发送完成")
                    break
                except Exception:
                    logger.error("仿真服务可能不存在发送失败，重新连接")
                    self.close()
                    self.open()
                    logger.info("准备重新发送08报文")
                    self.send_ident(packet)

    def get_product_id(self, client_id=typing.Optional[None]) -> bytes:
        """
        获取产品标识
        :param client_id:
        :return:
        """
        flags = client_id[0] | 0

        return b"\x02" if flags else b"\x01"
