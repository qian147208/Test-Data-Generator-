# Test-Data-Generator

一款强大的测试数据生成工具，支持 MySQL、PostgreSQL、SQLite 数据库，自动分析表结构并生成高质量的测试数据。

## 功能特性

- 🔗 **多数据库支持** - 支持 MySQL、PostgreSQL、SQLite 的连接和管理
- 📊 **智能表分析** - 自动解析表结构、字段类型、外键关系
- 🎯 **多样化生成策略** - 支持正常值、边界值、异常值、混合模式
- 🔗 **外键关系处理** - 自动识别并维护表间依赖关系
- 💾 **批量数据生成** - 支持单表和批量多表数据生成
- 📤 **多格式导出** - 支持 SQL、CSV、JSON 等导出格式
- 🎨 **友好的 Web 界面** - 基于 Vue 3 + Element Plus 的现代化 UI
- 🔌 **完整的 REST API** - 基于 FastAPI 的后端服务

## 技术栈

### 前端
- Vue 3 (Composition API)
- Pinia (状态管理)
- Element Plus (UI 组件库)
- Vite (构建工具)

### 后端
- Python 3.8+
- FastAPI (Web 框架)
- SQLAlchemy (ORM)
- Faker (数据生成)

## 快速开始

### 环境要求

- Python 3.8+
- Node.js 16+
- MySQL / PostgreSQL / SQLite

### 安装

```bash
# 克隆项目
git clone https://github.com/qian147208/Test-Data-Generator-.git
cd Test-Data-Generator

# 安装后端依赖
pip install -r requirements.txt

# 安装前端依赖
cd frontend
npm install
```

### 运行

```bash
# 启动后端服务 (默认端口 8001)
python main.py

# 或使用 uvicorn
uvicorn src.api.app:app --host 0.0.0.0 --port 8001 --reload

# 前端开发模式 (新终端)
cd frontend
npm run dev
```

访问 `http://localhost:5173` 打开 Web 界面。

### 构建生产版本

```bash
cd frontend
npm run build
```

构建后的文件将自动集成到后端服务中。

## 使用流程

### 1. 连接数据库

在 Web 界面填写数据库连接信息：
- 数据库类型 (MySQL/PostgreSQL/SQLite)
- 主机地址和端口
- 数据库名称
- 用户名和密码

### 2. 查看表结构

连接成功后，自动加载数据库中的所有表，可以查看：
- 表字段信息
- 主键和外键
- 索引结构
- 表依赖关系

### 3. 生成测试数据

- 选择目标表
- 设置生成数量 (1-10000)
- 选择生成策略
- 可选：自定义字段生成规则

### 4. 导出数据

支持多种导出格式：
- SQL INSERT 语句
- CSV 文件
- JSON 文件

## API 文档

启动服务后访问：
- Swagger UI: `http://localhost:8001/docs`
- ReDoc: `http://localhost:8001/redoc`

### 主要接口

| 方法 | 路径 | 描述 |
|------|------|------|
| POST | `/api/connect` | 连接数据库 |
| POST | `/api/disconnect` | 断开连接 |
| GET | `/api/status` | 获取连接状态 |
| GET | `/api/tables` | 获取表列表 |
| GET | `/api/tables/{name}` | 获取表详情 |
| POST | `/api/generate` | 生成测试数据 |
| POST | `/api/generate/batch` | 批量生成 |
| POST | `/api/export/sql` | 导出 SQL |

## 项目结构

```
Test-Data-Generator/
├── frontend/                 # 前端项目
│   └── src/
│       ├── api/             # API 调用
│       ├── stores/          # Pinia 状态管理
│       └── components/      # Vue 组件
├── src/                     # 后端项目
│   ├── api/                 # API 路由
│   │   └── routes/          # 路由模块
│   ├── db_connector/        # 数据库连接
│   ├── data_generator/      # 数据生成引擎
│   ├── schema_parser/       # 表结构解析
│   └── relation_handler/    # 关系处理
├── main.py                  # 应用入口
└── requirements.txt         # Python 依赖
```

## 配置说明

### 环境变量

| 变量名 | 描述 | 默认值 |
|--------|------|--------|
| DB_HOST | 数据库主机 | localhost |
| DB_PORT | 数据库端口 | 3306/5432 |
| DB_DATABASE | 数据库名称 | - |
| DB_USERNAME | 用户名 | - |
| DB_PASSWORD | 密码 | - |
| DB_TYPE | 数据库类型 | mysql |

### CORS 配置

生产环境建议在 `create_app()` 时指定允许的域名：

```python
app = create_app(
    cors_origins=["https://yourdomain.com"]
)
```

## 数据生成策略

| 策略 | 描述 | 适用场景 |
|------|------|----------|
| normal | 正常值 | 常规测试数据 |
| boundary | 边界值 | 边界条件测试 |
| abnormal | 异常值 | 错误处理测试 |
| mixed | 混合模式 | 综合测试 |

## 安全建议

1. **数据库安全**
   - 生产环境使用强密码
   - 限制数据库用户权限
   - 避免将密码提交到代码仓库

2. **API 安全**
   - 生产环境配置正确的 CORS 策略
   - 建议添加认证机制 (JWT/API Key)

3. **敏感信息**
   - 不要在前端存储数据库密码
   - 使用环境变量管理配置

## 许可证

本项目基于 MIT 许可证开源。

## 贡献

欢迎提交 Issue 和 Pull Request！
