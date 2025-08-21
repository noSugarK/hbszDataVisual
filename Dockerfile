# 使用Python 3.10官方镜像作为基础镜像
FROM python:3.10-slim

# 设置环境变量
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DJANGO_SETTINGS_MODULE=hbszDataVisual.settings

# 设置工作目录
WORKDIR /app

# 创建APT源列表并使用阿里云镜像源
RUN echo "deb http://mirrors.aliyun.com/debian bookworm main contrib non-free non-free-firmware" > /etc/apt/sources.list \
    && echo "deb http://mirrors.aliyun.com/debian-security/ bookworm-security main contrib non-free non-free-firmware" >> /etc/apt/sources.list \
    && echo "deb http://mirrors.aliyun.com/debian bookworm-updates main contrib non-free non-free-firmware" >> /etc/apt/sources.list \
    && echo "deb http://mirrors.aliyun.com/debian bookworm-backports main contrib non-free non-free-firmware" >> /etc/apt/sources.list \
    && apt-get update \
    && apt-get install -y --no-install-recommends \
        default-mysql-client \
        build-essential \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# 复制依赖文件
COPY requirements.txt /app/

# 配置pip国内镜像源并升级pip
RUN pip install --upgrade pip -i https://pypi.tuna.tsinghua.edu.cn/simple/ \
    && pip config set global.index-url https://pypi.tuna.tsinghua.edu.cn/simple/ \
    && pip config set global.trusted-host pypi.tuna.tsinghua.edu.cn

# 安装依赖
RUN pip install --no-cache-dir -r requirements.txt

# 复制项目文件
COPY . /app/

# 安装gunicorn（确保安装在正确位置）
RUN pip install --no-cache-dir gunicorn

# 创建静态文件目录
RUN mkdir -p /app/staticfiles

# 暴露端口
EXPOSE 8000

# 启动命令
CMD ["sh", "-c", "python manage.py collectstatic --noinput --verbosity=0 --clear && gunicorn --bind 0.0.0.0:8000 --workers 2 --timeout 120 hbszDataVisual.wsgi:application"]