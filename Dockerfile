FROM python:3.8-alpine
ENV TIME_ZONE=Asia/Shanghai
WORKDIR /root/yzMgr
ADD . /root/yzMgr
CMD /root/yzMgr/run.sh
