# -*- coding: utf-8 -*-
# @Name    : tainer
# @Author  : Malei
# @Email   : malei@anban.tech
# @Time    : 2022-07-15 下午1:39


import logging
import socket
import struct
import threading
import typing
import constants

logger = logging.getLogger("Logger")


class ManagerReader(threading.Thread):

    def __init__(self, client: socket.socket) -> typing.NoReturn:
        threading.Thread.__init__(self)
        self.client = client
        self.fd_key = None

    def run(self):
        logger.info("有新的易侦客户端连接")
        while True:
            try:
                for packet in self.recv(constants.MaxLength):
                    self.message_handler(packet)
            except ConnectionResetError as e:
                logger.error(e)
                self.delete_fd(self.fd_key)
                break

    def message_handler(self, packet: bytes) -> typing.NoReturn:
        logger.info("接收到易侦的新消息：%s" % packet)
        constants.ClientMap[self.fd_key] = self.client
        constants.MsgQueue.put(packet)
        logger.info("新消息放入队列")

    def recv(self, max_length: int) -> typing.Optional[typing.Generator]:
        """
        获取缓冲区数据
        :param max_length:
        :return:
        """
        data = self.client.recv(max_length)
        if not data:
            raise ConnectionResetError
        while data:
            length = struct.unpack("<L", data[0:4])[0]
            body = data[4:length]
            self.fd_key = self.gen_fd_key(body)
            if not self.check_client():
                continue
            packet = data[0:length + 4]
            data = data[length + 4::]
            yield packet

    def check_client(self) -> bool:
        """
        校验客户端
        :return:
        """
        return True

    def gen_fd_key(self, data: bytes) -> bytes:
        """
        生成fd key
        :param data:
        :return:
        """
        return data[2:6] + data[10:14]

    def delete_fd(sel, key: bytes) -> typing.NoReturn:
        """
        删除句柄
        :param key:
        :return:
        """
        try:
            del constants.ClientMap[key]
            logger.info("删除句柄成功%s" % key)
        except Exception:
            logger.info("删除句柄失败%s" % key)

    def get_fd(self, key: bytes) -> typing.Optional[socket.socket]:
        """
        获取句柄
        :param key:
        :return:
        """
        try:
            return constants.ClientMap[key]
        except Exception:
            return None


class TransferReader(ManagerReader):
    def run(self):
        logger.info("有新的仿真客户端连接")
        while True:
            try:
                for packet in self.recv(constants.MaxLength):
                    self.message_handler(packet)
            except ConnectionResetError as e:
                logger.error(e)
                logger.error("仿真测可能断开连接")
                break

    def message_handler(self, packet: bytes) -> typing.NoReturn:
        logger.info("接收到仿真的新消息：%s" % packet)
        if packet[18] == 0x07:
            logger.info("心跳报文丢弃")
            return
        fd = self.get_fd(self.fd_key)
        if fd:
            logger.info("找到易侦的句柄:%s" % fd)
            logger.info("开始发送数据:%s" % packet)
            fd.sendall(packet)
            self.delete_fd(self.fd_key)
