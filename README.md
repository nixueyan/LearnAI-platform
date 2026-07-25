# LearnAI

面向大学生的个性化学习平台，基于 FastAPI + SQLite。支持学科、章节、AI 生成教学资源、题库练习、笔记、AI 问答和每日打卡。

## 快速启动

```bash
# 1. 虚拟环境
python -m venv venv
venv\Scripts\activate        # Windows
# source venv/bin/activate   # Mac/Linux

# 2. 安装依赖
pip install -r requirements.txt

# 3. 配置 DeepSeek API Key（可选，不配则 AI 功能用模拟模式）
cp .env.example .env
# 编辑 .env 填入 DEEPSEEK_API_KEY

# 4. 初始化数据库
python -m app.init_db

# 5. 启动
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

打开 http://localhost:8000

## 项目结构

```
├── app/
│   ├── main.py          # FastAPI 路由
│   ├── models.py        # 数据库模型
│   ├── schemas.py       # Pydantic 校验
│   ├── crud.py          # 数据库操作
│   ├── ai_provider.py   # DeepSeek API 封装
│   ├── database.py      # SQLAlchemy 配置
│   └── init_db.py       # 种子数据
├── static/
│   ├── index.html       # 首页（课程+资源库+打卡）
│   ├── subject.html     # 学科详情（4 个 Tab）
│   ├── profile.html     # 个人画像（雷达图+统计）
│   ├── login.html       # 登录/注册
│   ├── onboarding.html  # 新手引导
│   ├── css/style.css    # 全局样式
│   └── js/
│       ├── app.js       # 公共逻辑
│       └── subject.js   # 学科页逻辑
└── requirements.txt
```

## 功能

- **课程学习**：8 章节高等数学，26 个 AI 生成教学小节（含知识框架+例题+小结）
- **题库练习**：96 道题（4 种题型 × 3 难度），提交后逐题解析+错题回顾
- **AI 资源生成**：讲解文档/思维导图/视频脚本，存入公共库全员共享
- **AI 问答**：3 种智能体角色（答疑/画像分析/路径规划），附带章节上下文
- **笔记系统**：Markdown 渲染，全局浮窗聚合+搜索，一键从资源摘录
- **个人画像**：六维雷达图（根据答题数据动态计算）+ 学习统计 + 进度追踪
- **每日打卡**：28 天日历视图 + 连续天数
- **公共资源库**：首页分类筛选 + 搜索 + 弹窗阅读

## 默认测试账号

- 用户名：`test`
- 密码：`123456`

（也可自行注册新账号）
