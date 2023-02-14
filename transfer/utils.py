# -*- coding: utf-8 -*-
# @Name    : utils
# @Author  : Malei
# @Email   : malei@anban.tech
# @Time    : 2023-02-14 下午5:52


import json
import os
import time
import urllib.request
from urllib import parse
import constants
from logger import logger
from constants import rwlock

# rwlock = RWLock()


def notify_platform(*args, **kwargs):
    """
    core出现错误通知平台
    :return:
    """
    client_id = args[0]
    sid, task_ins_id = constants.TaskMap.get(client_id, [0, 0])
    callback_serv = eval(os.environ.get("callback_serv", '{}'))
    if not callback_serv:
        logger.info("平台回调服务未找到注册信息， 尝试从本地存档获取!")
        cache = read_cache()
        serv_info = cache.get("callback_serv")
        if serv_info:
            logger.info("本地存档中找到callback_serv相关注册信息,准备加载服务信息")
            prod, ip, port, _ = serv_info
            os.environ.setdefault("callback_serv", str({"ip": ip, "port": port}))
            cache["callback_serv"] = [prod, ip, port, int(time.time()), 0, 0]
            write_cache(cache)
        else:
            logger.info("未找到本地存档到callback_serv注册信息")
            return
    else:
        ip = callback_serv.get("ip")
        port = callback_serv.get("port")
    for i in range(5):
        try:
            url = f"http://{ip}:{port}{constants.YFCallBack}"
            data = {
                "msg_type": 1,
                "task_instances_id": task_ins_id,
                "data": ""
            }
            logger.info("准备第<%s>次通知平台" % i)
            req = urllib.request.Request(url=url,  data=parse.urlencode(data).encode("utf-8"))
            response = urllib.request.urlopen(req, timeout=3)
            resp = json.loads(response.read().decode('utf-8'))
            if resp.get("code") == constants.RespCode:
                logger.info("平台通知成功")
                return
            else:
                logger.info("平台回调第<%s>次通知失败, 响应code码为:%s, msg为: %s" % (i, resp.get("code"), resp.get("msg")))
        except Exception as e:
            logger.error(e)
            logger.info("平台回调第<%s>次通知失败, 通知出现异常" % i)


def read_cache():
    if not os.path.exists("./cache"):
        return dict()
    rwlock.reader_lock.acquire()
    with open("./cache", "r") as fd:
        try:
            data = json.load(fd)
        except Exception:
            data = dict()
    rwlock.reader_lock.release()
    return data


def write_cache(data):
    rwlock.writer_lock.acquire()
    with open("./cache", "w") as fd:
        json.dump(data, fd)
    rwlock.writer_lock.release()


def socket_abort_callback(fd_key, packet, obj, filename_format):
    logger.info("平台连接失败，准备断开客户端连接：%s" % fd_key)
    logger.info("准备通知平台core服务异常,clientid==>:%s" % fd_key)
    notify_platform(fd_key)
    sid, task = constants.TaskMap.get(fd_key)
    if not os.path.exists(constants.DataPath):
        os.mkdir(constants.DataPath)
    with open(constants.DataPath + filename_format % (sid, task), "a") as f:
        f.write(str(packet) + "\r\n")
    obj.delete_fd(fd_key, close=True)
    constants.BADFD[fd_key] = int(time.time())
