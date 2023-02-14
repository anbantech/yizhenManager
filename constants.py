# -*- coding: utf-8 -*-
# @Name    : constants
# @Author  : Malei
# @Email   : malei@anban.tech
# @Time    : 2022-07-15 下午1:37


from queue import Queue
from rwlock import RWLock

rwlock = RWLock()
MaxLength = 256 * 1024
BufSize = 1024 * 1024 * 4
ClientMap = {}
TaskMap = {}
MsgQueue = Queue()
RespMsgQueue = Queue()
F2RespQueue = Queue()
BADFD = {}
BADExpire = 30
YFCallBack = "/api/v1.0/tasks/callback"
RespCode = 200
DataPath = "/var/yifu"
