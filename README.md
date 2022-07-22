### 易侦Manager

- build
```shell
docker build -f Dockerfile -t yizhen-manager:latest .
```
- run
```shell
docker run -itd --name=yizhen-manager --net=host --restart=always -v /var:/var yizhen-manager:latest
```

- 修改配置
```shell
docker cp config.ini yizhen-manager:/root/yizhenManager/config.ini
```
