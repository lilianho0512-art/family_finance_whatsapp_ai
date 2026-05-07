# Family Finance WhatsApp AI Assistant

[![CI](https://github.com/lilianho0512-art/family_finance_whatsapp_ai/actions/workflows/ci.yml/badge.svg)](https://github.com/lilianho0512-art/family_finance_whatsapp_ai/actions/workflows/ci.yml)

生产级 WhatsApp 家庭财务 AI 助理：
- WhatsApp Cloud API 接入（GET 验证 + POST 接收）
- send "Hi" 自动回复 自我介绍 + 功能目录
- 文字 / 图片 / PDF 都支持，OCR 自动识别
- AI（Ollama / Gemini）+ 规则解析双层 fallback
- 自动 A/B/C/D 提问，记住每位用户当前记录哪一笔
- 自动记录：开销、储蓄、收入、转账
- WhatsApp 内置查询：本月开销 / 储蓄 / 收入 / 储蓄率 / 类别 / 商家
- Bootstrap Dashboard / Records / Reports
- Excel 月报导出（Summary / Expenses / Savings / Income / Category / Cashflow / Need Review）
- APScheduler 每日 22:00、月初 01:00 自动任务
- 自我修复：缺失文件夹自动创建、AI 离线 → rule_parser、JSON 修复、WhatsApp send 重试 3 次、所有错误写 logs + bug_logs

---

## 1. 快速运行

### 1.1 Windows 一键

```bat
run.bat
```

会自动：建虚拟环境 → 安装依赖 → health_check → 启动 uvicorn 在 8000 端口。

### 1.2 手工

```bash
python -m venv venv
venv\Scripts\activate           # macOS/Linux: source venv/bin/activate
pip install -r requirements.txt
copy .env.example .env          # macOS/Linux: cp .env.example .env
python health_check.py
uvicorn app.main:app --reload --port 8000
```

### 1.3 Docker

```bash
docker compose up -d --build
```

### 1.4 OCR 依赖（识别图片 / 截图）

- **Windows**：下载 https://github.com/UB-Mannheim/tesseract/wiki 安装，然后在 `.env` 设：
  ```
  TESSERACT_CMD=C:\Program Files\Tesseract-OCR\tesseract.exe
  ```
- **macOS**：`brew install tesseract tesseract-lang`
- **Linux**：`sudo apt install tesseract-ocr tesseract-ocr-chi-sim`

> 没装 Tesseract 也能跑——图片会落入 `need_review` 等待人工补录。

---

## 2. 接入 WhatsApp（两种 provider 任选）

`.env` 设 `WHATSAPP_PROVIDER=meta` 或 `WHATSAPP_PROVIDER=greenapi` 切换。

### 2A. Green API（推荐：注册简单，扫 QR 即可，不用 Meta 后台）

1. 去 https://green-api.com 注册（邮箱即可，免费 Developer 实例）
2. Console 创建 Instance → 拿 `idInstance` + `apiTokenInstance`
3. 用你 WhatsApp app 扫 QR 把账号挂上去（这个号会成为 bot 的 sender）
4. `.env` 填：
   ```
   WHATSAPP_PROVIDER=greenapi
   GREENAPI_INSTANCE_ID=<idInstance>
   GREENAPI_TOKEN=<apiTokenInstance>
   ```
5. 启服务：`run.bat` → 起 ngrok：`ngrok http 8000`
6. 一键注册 webhook URL：
   ```
   python setup_greenapi_webhook.py https://<your-ngrok>.ngrok-free.app
   ```
7. WhatsApp 发 "Hi" 给那个挂上 Green API 的号 → 应回菜单

> 注意：Green API 走 WhatsApp Web 协议（非官方），违反 Meta ToS，号有被封风险。**建议用备用号**，不要用主号。

### 2B. Meta WhatsApp Cloud API

1. 进入 [Meta for Developers](https://developers.facebook.com/) → 创建 Business App
2. 添加产品 **WhatsApp** → 进入 **API Setup**
3. 拿到 3 样：
   - `Phone Number ID` → 填入 `.env` 的 `WHATSAPP_PHONE_NUMBER_ID`
   - `Temporary access token`（24 小时）或 System User long-lived token → `WHATSAPP_TOKEN`
   - 自己定义一个 `WHATSAPP_VERIFY_TOKEN`（任意字符串，例：`my_verify_token`）
4. **Add recipient phone number**：把你自己测试用的手机号添加进 Allowed list
5. **Configuration → Webhook**：
   - Callback URL：`https://<你的公网域名>/webhook`
   - Verify Token：与 `.env` 一致
   - 点 **Verify and save**（应用启动后才能验证成功）
6. **Webhook Fields** 勾选：`messages`

### 2.1 用 ngrok 把本地 8000 端口暴露到公网

```bash
ngrok http 8000
```

ngrok 会给你一个类似 `https://xxxx-xx-xx.ngrok-free.app` 的公网地址。
把它填到 Meta 后台 Webhook Callback URL：
```
https://xxxx-xx-xx.ngrok-free.app/webhook
```

---

## 3. 测试步骤

### 3.1 测试 Hi 菜单
WhatsApp 直接发：
```
Hi
```
预期回复：
```
你好，我是你的家庭财务 AI 助理 👋
我可以帮你记录：
A. 家庭开销
B. 家庭储蓄
...
```

### 3.2 测试文字账单
WhatsApp 发：
```
今天 Tesco RM88
```
预期：
```
我识别到：
商家：Tesco
金额：MYR 88.00
日期：YYYY-MM-DD

请选择这笔记录类型：
A. 家庭开销
...
```
回 `A` → 提示选择分类 → 回 `A` → 提示付款方式 → 回 `D` → 自动确认 ✅

### 3.3 测试储蓄
```
今天存钱 RM500
```
→ 自动判定 savings → 询问储蓄账户 → 选 `A`（Maybank）→ ✅

### 3.4 测试收入
```
工资 RM3800
```
→ 自动判定 income + Salary → ✅（无需补充）

### 3.5 测试查询
- `这个月花了多少？`
- `这个月储蓄多少？`
- `这个月收入多少？`
- `本月储蓄率多少？`
- `今天花了多少？`
- `Baby 类别花多少？`
- `这个月 Tesco 花多少？`
- `导出` → 生成 Excel 月报

### 3.6 测试图片 / PDF
直接在 WhatsApp 把收据图片发过来，会自动 OCR + AI 解析 + 提问。

### 3.7 用 curl 模拟 webhook（不连 WhatsApp 也能测）

```bash
curl -X POST http://localhost:8000/webhook \
  -H "Content-Type: application/json" \
  -d "{\"entry\":[{\"changes\":[{\"value\":{\"messages\":[{\"from\":\"60123456789\",\"id\":\"test1\",\"type\":\"text\",\"text\":{\"body\":\"Hi\"}}]}}]}]}"
```

---

## 4. Dashboard / 报表

启动后浏览器打开：

| 页面 | URL |
|---|---|
| Dashboard | http://localhost:8000/ |
| Records | http://localhost:8000/records |
| Reports | http://localhost:8000/reports |
| Excel 月报 | http://localhost:8000/export/monthly |
| Health | http://localhost:8000/health |

---

## 5. 自动 Bug 修复 / Self-Healing

| 场景 | 处理 |
|---|---|
| AI 输出含 markdown ` ```json ` | `extract_json` 自动剥离 |
| AI JSON 含尾逗号 / 单引号 | 自动清洗后再 parse |
| Ollama 离线 | 自动 fallback 到 `rule_parser` |
| Gemini 未配置 | 跳过，仅用 Ollama / rule |
| OCR Tesseract 未装 / 失败 | 记录 `need_review` |
| WhatsApp send 失败 | 退避 3 次（2/4/8 秒） |
| webhook 解析异常 | 写入 `bug_logs`，仍返回 200，避免 Meta 重试雪崩 |
| 文件夹丢失 | 启动时 `ensure_folders()` 自动创建 |
| 金额识别失败 | 后续追问（A/B/C 流程兜底） |
| 日期识别失败 | fallback 到 `today` |
| 全部错误 | 写 `logs/app.log` + `bug_logs` 表 |

---

## 6. 项目结构

```
family_finance_whatsapp_ai/
├── app/
│   ├── main.py                  # FastAPI 入口
│   ├── config.py
│   ├── database.py
│   ├── models.py                # FinancialRecord / Conversation / BugLog
│   ├── schemas.py
│   ├── routers/
│   │   ├── whatsapp.py          # GET 验证 + POST 接收
│   │   ├── dashboard.py
│   │   ├── records.py
│   │   ├── reports.py
│   │   └── export.py
│   ├── services/
│   │   ├── whatsapp_service.py  # 发文字 + 下载 media + 重试
│   │   ├── ai_parser.py         # Ollama → Gemini → rule
│   │   ├── rule_parser.py
│   │   ├── ocr_service.py
│   │   ├── record_service.py
│   │   ├── question_engine.py   # A/B/C 题库 + 答案解析
│   │   ├── conversation_memory.py
│   │   ├── report_service.py
│   │   ├── excel_export.py
│   │   ├── scheduler_service.py
│   │   ├── auto_bug_checker.py  # @safe 装饰器 + log_bug
│   │   ├── self_healing_service.py
│   │   └── menu_service.py
│   ├── templates/   (Jinja2 + Bootstrap)
│   ├── static/
│   └── utils/
│       ├── logger.py
│       ├── json_tools.py
│       ├── date_tools.py
│       └── money_tools.py
├── tests/test_smoke.py
├── uploads/  output/  logs/  data/
├── .env.example
├── requirements.txt
├── Dockerfile
├── docker-compose.yml
├── run.bat
├── health_check.py
└── README.md
```

---

## 7. 数据库 + Alembic 迁移

### 7.1 SQLite（默认 / 开发）

```
DATABASE_URL=sqlite:///./data/family_finance.db
```

无需额外步骤 —— 启动应用时会自动 `alembic upgrade head`。

### 7.2 PostgreSQL（推荐生产用）

**1) 起一个 Postgres 实例**

用 docker-compose 自带的 profile：

```bash
docker compose --profile postgres up -d db
```

或自己装 Postgres，建库：

```sql
CREATE DATABASE family_finance;
CREATE USER family WITH ENCRYPTED PASSWORD 'family_secret';
GRANT ALL PRIVILEGES ON DATABASE family_finance TO family;
```

**2) 在 `.env` 切换 URL**

```
DATABASE_URL=postgresql+psycopg2://family:family_secret@localhost:5432/family_finance
```
（容器内连容器：把 `localhost` 改成 `db`）

**3) 跑迁移**

```bash
alembic upgrade head
```

或一并启动 app + db：

```bash
docker compose --profile postgres up -d --build
```

### 7.3 Alembic 常用命令

```bash
alembic upgrade head                                # 升级到最新
alembic current                                     # 查看当前版本
alembic history --verbose                           # 看所有迁移
alembic revision --autogenerate -m "add family_id"  # 改了 models.py 后生成迁移
alembic downgrade -1                                # 回滚一步
```

迁移文件在 `alembic/versions/`。`alembic/env.py` 已自动从 `.env` 的 `DATABASE_URL` 读连接串，不需改 `alembic.ini`。

### 7.4 Multi-family SaaS（已开启）

系统已开启多家庭隔离 + JWT 登录：

| 表 | 作用 |
|---|---|
| `families` | 家庭账户 |
| `users` | 邮箱 + bcrypt 密码 + `family_id` |
| `whatsapp_enrollments` | WhatsApp 号 → family 映射，全局唯一 |
| `financial_records.family_id` | 每条账目都属于某个家庭 |
| `conversations.family_id` | 对话状态也按家庭隔离 |

**首次使用：**

1. 启动后访问 http://localhost:8000/ 自动跳到 `/register`
2. 填家庭名 + 邮箱 + 密码 + 你的 WhatsApp 号（会自动绑定到此家庭）
3. 登录后在 dashboard 可继续添加更多 WhatsApp 号（家人）

**WhatsApp 路由逻辑：**
- 收到消息 → 查 `whatsapp_enrollments` → 找到 family_id → 所有记账/查询都 scope 到这个家庭
- 没绑定的号码发消息 → 收到 onboarding 提示，引导去 `/register`

**Auth 端点：**

| 方法 + 路径 | 用途 |
|---|---|
| `GET /login`、`POST /login` | HTML 表单登录（设 cookie） |
| `GET /register`、`POST /register` | 创建家庭 + 管理员 |
| `GET/POST /auth/logout` | 清 cookie |
| `POST /auth/login` (form) | 返回 JSON `{access_token}` 给 API/CLI |
| `GET /auth/me` | 当前用户 + family 信息（需 cookie 或 Bearer） |
| `POST /auth/whatsapp` | 给当前家庭加号码 |
| `DELETE /auth/whatsapp/{id}` | 移除当前家庭的号码（不能跨家庭） |

**JWT 配置（在 `.env`）：**
```
JWT_SECRET=<32+ 字符随机串>      # 生产必须改！
JWT_ALGORITHM=HS256
JWT_EXPIRE_MINUTES=10080         # 7 天
```

生成强随机 secret：
```bash
python -c "import secrets; print(secrets.token_urlsafe(48))"
```

**支持两种身份方式：**
- 浏览器 → httponly cookie `ff_token`（登录后自动设置）
- API 客户端 → `Authorization: Bearer <jwt>`（从 `POST /auth/login` 取）

**安全防御：**
- 密码 bcrypt 哈希
- WhatsApp 号全局 unique（不能两家庭共用同号）
- 跨家庭操作全部 404/409（已端到端测试）
- Webhook 永远先按 `from_number` 查家庭 → 没绑定的号码无法写入数据

### 7.5 Admin 面板（跨家庭）

`users.is_superadmin = True` 的用户可访问 `/admin`，看所有家庭、所有 WhatsApp 号、bug logs。
普通家庭管理员（family admin role）只能看自己家。

**提升 superadmin（CLI）：**

```bash
python make_superadmin.py alice@example.com           # 提升
python make_superadmin.py alice@example.com --revoke  # 撤销
python make_superadmin.py --list                      # 列出
```

**Admin 路由：**

| 路径 | 内容 |
|---|---|
| `GET /admin` | 总览：家庭数 / 用户数 / 号码数 / 记录数 / bug 数 + 最近错误 |
| `GET /admin/family/{id}` | 任意家庭详情：成员、号码、最近 200 笔记录 |
| `GET /admin/bugs` | 全局 bug logs（最近 200 条） |

非 superadmin 访问 `/admin*` → 已登录用户重定向到 `/`，未登录重定向到 `/login`。

---

## 8. 单元测试

```bash
pip install pytest
pytest tests/ -v
```

---

## 9. 常见错误

| 报错 | 解决 |
|---|---|
| `Webhook verification failed` | `.env` 的 `WHATSAPP_VERIFY_TOKEN` 必须和 Meta 后台填的一致 |
| WhatsApp 回复发不出 | 检查 `WHATSAPP_TOKEN`（System User token 不会过期）、`WHATSAPP_PHONE_NUMBER_ID`、对方号码是否已加入 Allowed |
| 图片识别空 | Tesseract 未装；或 `TESSERACT_CMD` 路径错 |
| Ollama 慢 / 不可用 | 系统会自动 fallback 到 rule_parser，不影响使用 |
| 中文 OCR 不准 | 安装语言包：`tesseract-ocr-chi-sim` |
| 看不到 logs | 检查 `logs/app.log`，或在 SQLite 查 `bug_logs` 表 |
