# 快递取件系统镜像
FROM python:3.12-slim

# 工作目录
WORKDIR /app

# 先复制依赖清单，利用 Docker 层缓存：依赖不变时该层直接复用
COPY requirements.txt .

# 安装依赖（清华 PyPI 镜像加速）
RUN pip install --no-cache-dir -r requirements.txt \
    -i https://pypi.tuna.tsinghua.edu.cn/simple

# 再复制应用代码：代码改动只影响最后几层
COPY app.py .

# 声明服务端口
EXPOSE 5000

# 容器启动命令
CMD ["python", "app.py"]
