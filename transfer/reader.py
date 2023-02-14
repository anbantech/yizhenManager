# -*- coding: utf-8 -*-
# @Name    : reader
# @Author  : Malei
# @Email   : malei@anban.tech
# @Time    : 2022-07-15 下午1:39


import binascii
import os
import socket
import struct
import threading
import time
import typing
import constants

from logger import logger, crash_logger

from constants import rwlock
from transfer.client import YZOrYFClient, YFCoreClient
from transfer.utils import notify_platform, read_cache, write_cache


class ManagerReader(threading.Thread):

    def __init__(self, client: socket.socket) -> typing.NoReturn:
        threading.Thread.__init__(self)
        self.client = client
        self.fd_key = None
        self.YF_Core_SOF = b"\x79\x66"
        self.YZ_SOF = b"\x79\x7a"
        self.YF_SOF = b"\x79\x2a"

    def load_info(self, product, cache, client_id, ip, port, sender_id, task_id):
        if product == self.YF_Core_SOF:
            logger.info("易复core注册信息===>client_id: %s, ip:%s, port:%s" % (str(client_id), ip, port))
            cli = YFCoreClient(host=ip, port=port)
        else:
            logger.info("平台注册信息===>client_id: %s, ip:%s, port:%s" % (str(client_id), ip, port))
            cli = YZOrYFClient(host=ip, port=port, sock=self.client)
            os.environ.setdefault("callback_serv", str({"ip": ip, "port": port}))
            cache["callback_serv"] = ["callback_serv", ip, port, int(time.time()), sender_id, task_id]
        cache[str(client_id)] = [product.decode(), ip, port, int(time.time()), sender_id, task_id]
        rwlock.writer_lock.acquire()
        if constants.ClientMap.get(self.fd_key):
            del constants.ClientMap[self.fd_key]
        constants.ClientMap[self.fd_key] = (product.decode(), cli)
        constants.TaskMap[self.fd_key] = [sender_id, task_id]
        rwlock.writer_lock.release()
        logger.info("client_id: %s 注册完成" % str(client_id))
        write_cache(cache)

    def gen_client(self, sender_id: int, task_id: int, product: bytes) -> bytes:
        """
        生成client_id
        :return:
        """
        flag = 0x02 if product == self.YZ_SOF else 0x01
        return struct.pack("<L", sender_id << 24 | (task_id & 0x3FFFFF) << 2 | flag)

    def gen_register_resp(self, product, payload):
        """
        生成注册信息的resp报文
        :param product:
        :param payload:
        :return:
        """
        data = product + payload + b"\x0d\x0a"
        pro = struct.pack("<L", len(data)) + data
        constants.RespMsgQueue.put(pro)

    def register_serv(self, packet: typing.Union[bytes]) -> bool:
        """
        :param packet:
        :return: 该报文后续是否发送
        """
        product = packet[4:6]
        if product in [self.YF_SOF, self.YZ_SOF, self.YF_Core_SOF]:
            cache = read_cache()
            ip = "%s.%s.%s.%s" % struct.unpack("<BBBB", packet[6:10][::-1])
            port = struct.unpack("<H", packet[10:12])[0]
            sender_id = packet[12]
            task_id = struct.unpack("<L", packet[13:17])[0]
            self.fd_key = client_id = self.gen_client(sender_id, task_id, product)
            self.load_info(product, cache, client_id, ip, port, sender_id, task_id)
            self.gen_register_resp(product, client_id)
        else:
            self.fd_key = client_id = packet[6:10]
            if not constants.ClientMap.get(client_id, None):
                logger.info("系统环境中未找到core注册信息或core服务已经被删除, 尝试从本地存档获取!")
                cache = read_cache()
                register_info = cache.get(str(client_id))
                if register_info:
                    logger.info("本地存档中找到相关注册信息,准备加载服务信息")
                    prod, ip, port, _, sender_id, task_id = register_info
                    self.load_info(prod.encode(), cache, client_id, ip, port, sender_id, task_id)
                    return True
                else:
                    logger.info("未找到本地存档到--%s--注册信息,开始通知上游平台" % client_id)
                    notify_platform(client_id)
                    return False
            return True

    def run(self):
        logger.info("有新的平台客户端连接")
        while True:
            try:
                packet = self.recv()
                if packet:
                    logger.info("接收到平台的新消息报文：%s" % packet)
                    try:
                        if self.register_serv(packet):
                            self.message_handler(packet)
                    except Exception as e:
                        logger.error(e)
            except ConnectionResetError as e:
                logger.error("平台客户端断开连接了：%s" % self.fd_key)
                self.delete_fd(self.fd_key, close=True)
                break

    def message_handler(self, packet: bytes) -> typing.NoReturn:
        logger.info("fd_key:%s" % self.fd_key)
        logger.info("平台节点标识：%s, 仿真节点标识:%s, 任务id：%s" % (hex(packet[4]), hex(packet[5]), hex(packet[18])))
        constants.MsgQueue.put(packet)
        logger.info("新消息放入发送队列,当前队列容量： %s" % constants.MsgQueue.qsize())

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
                    if received[14:15] == b"\x08":
                        # 上游08报文丢弃
                        return None
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
        return data[2:6]

    def delete_fd(sel, key: bytes, close: bool) -> typing.NoReturn:
        """
        删除句柄
        :param key:
        :param close:
        :return:
        """
        rwlock.writer_lock.acquire()
        try:
            cli = constants.ClientMap.get(key)
            if not cli:
                return
            product, fd = cli
            if product == "yf":
                logger.info("易复core客户端断开连接，不删除句柄")
                return
            if close:
                fd.close()
            del constants.ClientMap[key]
            del constants.TaskMap[key]
            logger.info("删除句柄成功%s" % key)
        except Exception as e:
            logger.error(e)
            logger.info("删除句柄失败%s" % key)
        finally:
            rwlock.writer_lock.release()


class TransferReader(ManagerReader):
    def run(self):
        logger.info("有新的仿真客户端连接")
        self.client.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, constants.BufSize)
        self.client.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, True)
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
        logger.info("接收到仿真的新消息,协议头: %s, 任务标识:%s " % (header, packet[18:19]))
        if packet[18] == 0x32:
            crash_logger.info(
                "\n[ KIND ]:[%s]"
                "\n[  PC  ]:[%s]"
                "\n[ VALUE]:[%s]"
                "\n[ INFO ]:[%s]" %
                (
                    binascii.b2a_hex(packet[27:29]),
                    binascii.b2a_hex(packet[29:33][::-1]),
                    binascii.b2a_hex(packet[33:41][::-1]),
                    packet
                )
            )
        if packet[18] == 0x07:
            logger.info("心跳报文丢弃")
            return
        elif packet[18] == 0xf2 and packet[-2:] != b"\r\n":
            constants.F2RespQueue.put(packet)
            logger.info("新消息放入F2响应队列,当前队列容量： %s" % constants.F2RespQueue.qsize())
        else:
            constants.RespMsgQueue.put(packet)
            logger.info("新消息放入响应队列,当前队列容量： %s" % constants.RespMsgQueue.qsize())
