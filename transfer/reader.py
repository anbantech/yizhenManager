# -*- coding: utf-8 -*-
# @Name    : tainer
# @Author  : Malei
# @Email   : malei@anban.tech
# @Time    : 2022-07-15 下午1:39


import binascii
import socket
import struct
import threading
import typing
import constants

from logger import logger

from rwlock import RWLock

rwlock = RWLock()


class ManagerReader(threading.Thread):

    def __init__(self, client: socket.socket) -> typing.NoReturn:
        threading.Thread.__init__(self)
        self.client = client
        self.fd_key = None

    def run(self):
        logger.info("有新的易侦客户端连接")
        while True:
            try:
                packet = self.recv()
                logger.info("接收到易侦的新消息====报文：%s" % packet)
                self.message_handler(packet)
            except ConnectionResetError as e:
                logger.error("易侦客户端断开连接了：%s" % self.fd_key)
                self.delete_fd(self.fd_key, close=True)
                break

    def message_handler(self, packet: bytes) -> typing.NoReturn:
        logger.info("fd_key:%s" % self.fd_key)
        logger.info("易侦节点标识：%s, 仿真节点标识:%s, 任务id：%s" % (hex(packet[4]), hex(packet[5]), hex(packet[18])))
        rwlock.writer_lock.acquire()
        constants.ClientMap[self.fd_key] = self.client
        rwlock.writer_lock.release()
        constants.MsgQueue.put(packet)
        logger.info("新消息放入队列,当前队列容量： %s" % constants.MsgQueue.qsize())

    def recv(self) -> typing.Optional[bytes]:
        """
        获取缓冲区数据
        :return:
        """

        length = 0
        received = b""
        while True:
            if not length:
                _length = self.client.recv(4)
                if not _length:
                    raise ConnectionResetError
                length = struct.unpack("<L", _length)[0]
            else:
                buf = self.client.recv(length - len(received))
                if not buf:
                    raise ConnectionResetError
                received += buf
                if length == len(received):
                    self.fd_key = self.gen_fd_key(received[:18])
                    if not self.check_client():
                        continue
                    return _length + received

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

    def delete_fd(sel, key: bytes, close: bool) -> typing.NoReturn:
        """
        删除句柄
        :param key:
        :param close:
        :return:
        """
        rwlock.writer_lock.acquire()
        try:
            if close:
                fd = constants.ClientMap[key]
                fd.close()
            constants.ClientMap[key] = None
            del constants.ClientMap[key]
            logger.info("删除句柄成功%s" % key)
        except Exception:
            logger.info("删除句柄失败%s" % key)
        finally:
            rwlock.writer_lock.release()

    def get_fd(self, key: bytes) -> typing.Optional[socket.socket]:
        """
        获取句柄
        :param key:
        :return:
        """
        rwlock.reader_lock.acquire()
        try:
            fd = constants.ClientMap[key]
            return fd
        except Exception:
            return None
        finally:
            rwlock.reader_lock.release()


class TransferReader(ManagerReader):
    def run(self):
        logger.info("有新的仿真客户端连接")
        while True:
            try:
                packet = self.recv()
                self.message_handler(packet)
            except ConnectionResetError as e:
                self.client.close()
                logger.error(e)
                logger.error("仿真测可能断开连接")
                break

    def message_handler(self, packet: bytes) -> typing.NoReturn:
        header = binascii.b2a_hex(packet[:18])
        logger.info("接收到仿真的新消息,协议头：%s" % header)
        if packet[18] == 0x07:
            logger.info("心跳报文丢弃")
            return
        fd = self.get_fd(self.fd_key)
        if fd:
            logger.info("找到易侦的客户端句柄:%s" % self.fd_key)
            logger.info("开始向易侦返回数据，协议头:%s" % header)
            fd.sendall(packet)
            logger.info("向易侦返回成功")
            self.delete_fd(self.fd_key, close=False)
        else:
            logger.error("未找易侦的客户端句柄:%s" % self.fd_key)
