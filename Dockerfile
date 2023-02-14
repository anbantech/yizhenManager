FROM python:3.8-alpine
ENV TIME_ZONE=Asia/Shanghai
WORKDIR /root/yf
ADD . /root/yf
CMD /root/yf/run.sh
