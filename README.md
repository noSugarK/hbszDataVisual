## 技术栈

- 前端：bootstrap ，chart.js ，jquery
- 后端：Django
- 数据库：MySQL


## 项目结构

```
hbszDataVisual/                          # 项目根目录
├── manage.py                           # Django命令行工具
├── requirements.txt                    # Python依赖包列表
├── README.md                           # 项目说明文档
├── .gitignore                          # Git忽略文件配置
├── .env                                # 环境变量配置文件
├── docker-compose.yml                  # Docker容器编排配置
├── Dockerfile                          # Docker镜像构建文件
├── nginx.conf                          # Nginx服务器配置
├── project_docs/                       # 项目文档目录
│   ├── 项目文档.md
│   └── 开发计划.md
├── hbszDataVisual/                     # Django项目配置目录
│   ├── __init__.py                     # Python包标识文件
│   ├── settings.py                     # 项目设置文件
│   ├── urls.py                         # 项目根URL配置
│   ├── wsgi.py                         # WSGI部署配置
│   └── asgi.py                         # ASGI部署配置
├── apps/                               # Django应用目录
│   ├── __init__.py
│   ├── users/                          # 用户管理应用
│   │   ├── migrations/                 # 数据库迁移文件
│   │   ├── __init__.py
│   │   ├── admin.py                    # Django管理后台配置
│   │   ├── apps.py                     # 应用配置
│   │   ├── models.py                   # 数据模型定义
│   │   ├── views.py                    # 视图函数
│   │   ├── urls.py                     # URL路由配置
│   │   ├── forms.py                    # 表单定义
│   │   └── tests.py                    # 单元测试
│   ├── projects/                       # 项目数据管理应用
│   │   ├── migrations/
│   │   ├── __init__.py
│   │   ├── admin.py
│   │   ├── apps.py
│   │   ├── models.py
│   │   ├── views.py
│   │   ├── urls.py
│   │   ├── forms.py
│   │   └── tests.py
│   ├── visual/                         # 数据可视化应用
│   │   ├── migrations/
│   │   ├── __init__.py
│   │   ├── admin.py
│   │   ├── apps.py
│   │   ├── models.py
│   │   ├── views.py
│   │   ├── urls.py
│   │   ├── forms.py
│   │   └── tests.py
│   ├── data_processing/                # 数据处理应用
│   │   ├── migrations/
│   │   ├── __init__.py
│   │   ├── admin.py
│   │   ├── apps.py
│   │   ├── models.py
│   │   ├── views.py
│   │   ├── urls.py
│   │   ├── forms.py
│   │   └── tests.py
│   ├── data_prediction/                # 数据预测应用
│   │   ├── migrations/
│   │   ├── __init__.py
│   │   ├── admin.py
│   │   ├── apps.py
│   │   ├── models.py
│   │   ├── views.py
│   │   ├── urls.py
│   │   ├── forms.py
│   │   └── tests.py
│   └── common/                         # 公共功能应用
│       ├── migrations/
│       ├── __init__.py
│       ├── admin.py
│       ├── apps.py
│       ├── models.py
│       ├── views.py
│       ├── urls.py
│       ├── forms.py
│       └── tests.py
├── static/                             # 静态文件目录
│   ├── css/                            # CSS样式文件
│   ├── js/                             # JavaScript脚本文件
│   ├── images/                         # 图片资源文件
│   └── vendor/                         # 第三方库文件
├── templates/                          # 模板文件目录
│   ├── base.html                       # 基础模板
│   ├── home.html                       # 首页模板
│   ├── about.html                      # 关于页面模板
│   ├── help.html                       # 帮助页面模板
│   ├── users/                          # 用户模块模板
│   ├── projects/                       # 项目模块模板
│   ├── visualization/                  # 可视化模块模板
│   └── common/                         # 公共模板
├── media/                              # 媒体文件目录（用户上传文件）
│   └── uploads/                        # 上传文件存储目录
└── tests/                              # 测试文件目录
    ├── __init__.py
    ├── test_users.py
    ├── test_projects.py
    ├── test_visualization.py
    └── test_data_processing.py

```