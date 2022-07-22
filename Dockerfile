FROM python:3.8-alpine
ENV TIME_ZONE=Asia/Shanghai
WORKDIR /root/yizhenManager
ADD . /root/yizhenManager
CMD /root/yizhenManager/run.sh
