# -*- coding: utf-8 -*-
# @Name    : bad_fd
# @Author  : Malei
# @Email   : malei@anban.tech
# @Time    : 2023-02-20 上午10:50


from threading import Thread
import time

import constants

from logger import logger


class MonitorBadFd(Thread):
    """
    监控错误fd
    """

    def run(self):
        logger.info("错误句柄监控服务启动")
        cnt = 1
        while True:
            if cnt == 256:
                cnt = 1
            logger.info("错误句柄监控服务第%s次执行" % cnt)
            fd_list = list(constants.BADFD.keys())
            for fd in fd_list:
                _, client = constants.ClientMap.get(fd, (0, 0))
                if client and client.is_connected():
                    logger.info("%s 已经重新连接，删除badfd" % fd)
                    del constants.BADFD[fd]
                else:
                    ts = constants.BADFD.get(fd)
                    if time.time() - ts >= constants.BADExpire:
                        logger.info("%s 已经超过 %s 秒，删除badfd" % (fd, constants.BADExpire))
                        del constants.BADFD[fd]
            time.sleep(5)
            cnt += 1
