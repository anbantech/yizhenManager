### 易侦Manager

- build

```shell
docker build -f Dockerfile -t yf-mgr:latest .
```

- run

```shell
docker run -itd --name=yf-mgr --net=host --restart=always -v /var:/var yf-mgr:latest
```

```shell 加密
docker run -itd --name=yf-mgr --net=host --restart=always -v /var:/var -v /tmp:/tmp yf-mgr:latest
```

- 修改配置

```shell
docker cp config.ini yf-mgr:/root/yf/config.ini
```
