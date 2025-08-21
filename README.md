## 技术栈

- 前端：bootstrap ，chart.js ，jquery
- 后端：Django
- 数据库：MySQL

## 项目进度

- [x] 完成用户管理模块
- [x] 完成项目数据管理模块
- [x] 完成品牌管理模块
- [x] 完成物资类别管理模块
- [x] 完成地区管理模块
- [x] 完成规格管理模块
- [x] 完成供应商管理模块
- [x] 完成公共模块
- [x] 完成数据可视化模块
- [ ] 完成数据处理模块
- [ ] 完成数据预测模块
- [ ] 完成前端界面设计
- [ ] 完成项目文档编写

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
│   ├── brand/                          # 品牌管理应用
│   ├── category/                       # 物资类别管理应用
│   ├── region/                         # 地区管理应用
│   ├── specification/                  # 规格管理应用
│   ├── supplier/                       # 供应商管理应用
│   ├── visual/                         # 数据可视化应用
│   ├── data_processing/                # 数据处理应用（未实现）
│   ├── data_prediction/                # 数据预测应用（未实现）
│   └── common/                         # 公共模块
├── static/                             # 静态文件目录
│   ├── bootstrap/                      # bootstrap
│   ├── fontawesome/                    # fontawesome
│   ├── css/                            # CSS样式文件
│   ├── js/                             # JavaScript脚本文件
│   ├── images/                         # 图片资源文件
│   └── vendor/                         # 第三方库文件
├── templates/                          # 模板文件目录
│   ├── base.html                       # 基础模板
│   ├── header.html                     # 导航栏模板
│   └── footer.html                     # 页脚模板
├── media/                              # 媒体文件目录（用户上传文件）
│   └── uploads/                        # 上传文件存储目录
└── tests/                              # 测试文件目录
    ├── __init__.py
    ├── test_users.py
    ├── test_projects.py
    ├── test_visualization.py
    └── test_data_processing.py
```

