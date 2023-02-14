# -*- coding: utf-8 -*-
# @Name    : client
# @Author  : Malei
# @Email   : malei@anban.tech
# @Time    : 2022-07-14 上午11:30


import os
import binascii
import math
import socket
import struct
import threading
import typing
import constants

from logger import logger

from constants import rwlock
from transfer.utils import socket_abort_callback


class YZOrYFClient(object):
    """
    报文向易复业务或易侦发送，原socketclient返回
    """

    def __init__(
            self,
            host: str,
            port: int,
            sock=None,
            *args: typing.Any,
            **kwargs: typing.Any
    ) -> typing.NoReturn:
        self.host = host
        self.port = port
        self._sock = sock
        if self._sock:
            self._sock.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, constants.BufSize)
            self._sock.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, True)

    def is_connected(self) -> bool:
        return True

    def sendall(self, data: typing.Union[bytes]) -> int:
        return self._sock.sendall(data)

    def clear(self):
        pass

    def close(self):
        pass


class YFCoreClient(YZOrYFClient):
    """
    报文向易复Core发送，连接core serv 返回
    """

    def seconds_to_sockopt_format(self, seconds):
        if os.name == "nt":
            return int(seconds * 1000)
        else:
            microseconds_per_second = 1000000
            whole_seconds = int(math.floor(seconds))
            whole_microseconds = int(math.floor((seconds % 1) * microseconds_per_second))
            return struct.pack("ll", whole_seconds, whole_microseconds)

    def open(self):
        self._sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._sock.connect((self.host, self.port))
        self._sock.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, constants.BufSize)
        self._sock.setsockopt(socket.SOL_SOCKET, socket.SO_RCVTIMEO, self.seconds_to_sockopt_format(0.01))
        self._sock.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, True)

    def reopen(self):
        try:
            self._sock.close()
            self.open()
        except Exception as e:
            logger.error(e)
            return False
        return True

    def is_connected(self):
        try:
            if self._sock:
                resp = self._sock.recv(1, socket.MSG_DONTWAIT)
                if not resp:
                    logger.info("收到空数据，core服务断开, Mgr尝试重新创建新的句柄连接到core服务器")
                    return self.reopen()
            else:
                self.open()
                return True
        except socket.timeout:
            return True
        except BlockingIOError:
            return True
        except OSError as e:
            logger.error(e)
            if e.errno == 107:
                logger.info("Mgr重复读取,core服务器断开,Mgr尝试重新创建新的句柄连接到core服务器")
                return self.reopen()
        except Exception as e:
            logger.error(e)
            logger.error("socket服务连接失败")
            return False

    def close(self):
        logger.info("准备关闭core服务的客户端")
        self._sock.close()


class TransferClient2Simu(threading.Thread):

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
            packet = constants.MsgQueue.get(block=True)
            fd_key = packet[6:10]
            if constants.BADFD.get(fd_key, ""):
                logger.info("该数据对应的服务不存在，将保存到本地文件")
                sid, task = constants.TaskMap.get(fd_key)
                if not os.path.exists(constants.DataPath):
                    os.mkdir(constants.DataPath)
                with open(constants.DataPath + "/%02d_%d_write" % (sid, task), "a") as f:
                    f.write(str(packet) + "\r\n")
                continue
            while True:
                try:
                    logger.info("发送队列中获取到新的消息:%s" % packet)
                    logger.info("Mgr开始向仿真发送报文")
                    if not self.notify:
                        self.send_ident(packet)
                    self._sock.sendall(packet)
                    logger.info("Mgr向仿真发送完成")
                    break
                except Exception:
                    logger.error("仿真服务可能不存在发送失败，重新连接")
                    self.close()
                    self.open()
                    logger.info("准备重新发送08报文")
                    self.send_ident(packet)

    def get_product_id(self, client_id=typing.Optional[bytes]) -> bytes:
        """
        获取产品标识
        :param client_id:
        :return:
        """
        flags = client_id[0] & 3
        return struct.pack("B", flags)


class TransferClient2Platform(threading.Thread):
    def run(self) -> typing.NoReturn:
        while True:
            try:
                packet = constants.RespMsgQueue.get(block=True)
                logger.info("接收队列中获取到仿真反馈的消息:%s" % packet)
                logger.info("Mgr准备向平台发送报文")
                self.message_handler(packet)
            except Exception as e:
                logger.error(e)

    def message_handler(self, packet: bytes) -> typing.NoReturn:
        header = binascii.b2a_hex(packet[:18])
        fd_key = packet[6:10]
        client = self.get_fd(fd_key)
        if client:
            logger.info("找到平台的客户端句柄:%s" % fd_key)
            if client.is_connected():
                logger.info("平台连接成功，开始向平台返回数据，协议头:%s" % header)
                try:
                    rwlock.sender_lock.acquire()
                    client.sendall(packet)
                    rwlock.sender_lock.release()
                except Exception as e:
                    logger.error(f"Mgr向平台发送失败，原因：{e}")
                    socket_abort_callback(fd_key=fd_key, packet=packet, obj=self, filename_format="/%02d_%d_read")
                else:
                    logger.info("Mgr向平台发送完成")
            else:
                socket_abort_callback(fd_key=fd_key, packet=packet, obj=self, filename_format="/%02d_%d_read")
        else:
            logger.error("未找平台的客户端句柄:%s,Mgr丢弃该消息" % fd_key)

    def get_fd(self, key: bytes) -> typing.Union[socket.socket, YZOrYFClient, None]:
        """
        获取句柄
        :param key:
        :return:
        """
        rwlock.reader_lock.acquire()
        try:
            _, fd = constants.ClientMap[key]
            return fd
        except Exception:
            return None
        finally:
            rwlock.reader_lock.release()

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
                _, fd = constants.ClientMap[key]
                fd.close()
            del constants.ClientMap[key]
            del constants.TaskMap[key]
            logger.info("删除句柄成功%s" % key)
        except Exception as e:
            logger.error(e)
            logger.info("删除句柄失败%s" % key)
        finally:
            rwlock.writer_lock.release()


class TransferClient2PlatformF2(TransferClient2Platform):
    def run(self) -> typing.NoReturn:
        while True:
            try:
                packet = constants.F2RespQueue.get(block=True)
                logger.info("接收队列中获取到仿真F2消息，总长度:%s, 轮次id:%s, 状态:%s, 结束符：%s" % (
                    len(packet), packet[10:14], packet[31:32], packet[-2:]))
                logger.debug("接收队列中获取到仿真F2消息，内容:%s" % packet)
                self.message_handler(packet)
            except Exception as e:
                logger.error(e)

    def message_handler(self, packet: bytes) -> typing.NoReturn:
        header = binascii.b2a_hex(packet[:18])
        fd_key = packet[6:10]
        client = self.get_fd(fd_key)
        if client:
            logger.info("找到平台的客户端句柄:%s" % fd_key)
            if client.is_connected():
                logger.info("平台连接成功，开始向平台返回F2数据，协议头:%s" % header)
                try:
                    rwlock.sender_lock.acquire()
                    client.sendall(packet)
                    rwlock.sender_lock.release()
                except Exception as e:
                    logger.error(f"Mgr向平台发送F2失败，原因：{e}")
                    socket_abort_callback(fd_key=fd_key, packet=packet, obj=self, filename_format="/%02d_%d_read_f2")
                else:
                    logger.info("Mgr向平台发送F2完成")
            else:
                socket_abort_callback(fd_key=fd_key, packet=packet, obj=self, filename_format="/%02d_%d_read_f2")
        else:
            logger.error("未找平台的客户端句柄:%s,Mgr丢弃该F2消息" % fd_key)
