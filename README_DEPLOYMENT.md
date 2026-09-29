# cm-chen-health-platform Windows 部署说明

本项目可从 GitHub 克隆到另一台 Windows 电脑后运行。当前正式 FOOD 运行链为：FOOD_SELECTION_METADATA V1.4、MDT_STANDARD_COMPONENT_EXECUTION V1.4、MDT_INGREDIENT_MASTER V1.4 和 V1.4 nutrition provenance。历史 `outputs/` 下的 V1.7 工作簿不是生产运行依赖，也不应上传。

## 1. GitHub 部署

1. 安装 GitHub Desktop（或 Git）。
2. Clone `cm-chen-health-platform`。
3. 当前稳定分支为 `md-v4-integration`；未来合并到 `main` 后切换到 `main`。
4. 安装 Python 3.11+、Node.js 20 LTS+。
5. 在项目根目录执行：

```powershell
Copy-Item .\env.example .\.env
```

6. 本地演示可保留 SQLite 默认值；使用 MySQL/RDS 时，只在本机 `.env` 填写数据库配置。
7. 运行 `.\setup.ps1`，再运行 `.\verify-installation.ps1`。
8. 运行 `.\start-all.ps1`。

脚本只使用 `$PSScriptRoot`，不依赖原电脑路径。安装脚本不会迁移、删除或清空数据库。

## 2. 地址

- Backend Swagger：<http://127.0.0.1:8000/docs>
- Backend health：<http://127.0.0.1:8000/api/health>
- Frontend：Vite 默认通常为 <http://localhost:5173>

前端默认通过 Vite `/api` 代理访问后端；需要直连时可在 `.env` 设置 `VITE_API_BASE_URL`。

## 3. 数据库配置

SQLite 是默认本地开发模式，数据库文件会在 `backend` 工作目录按需创建，不随仓库提交。MySQL/RDS 需要网络可达、3306 端口放行、白名单允许当前 IP、数据库名 `ai_zxy` 及有效账号。密码只能保存在未跟踪的 `.env`，不得上传 GitHub、ZIP 或聊天记录。

`verify-installation.ps1` 在配置数据库时只做安全连接检查；未配置时显示 `DATABASE = NOT_CONFIGURED`，不影响源码安装验证。

## 4. 常见问题

- PowerShell 阻止脚本：在当前窗口执行 `Set-ExecutionPolicy -Scope Process Bypass`。
- Python 或 npm 找不到：重新安装 Python/Node.js，并确认加入 PATH。
- 8000 端口占用：关闭占用进程后重试后端。
- Vite 端口占用：使用 Vite 输出的替代端口。
- `.env` 缺失：复制 `env.example`；不要把真实凭据写进模板。
- RDS 3306 失败：检查白名单、防火墙、账号权限和医院网络是否阻断出站 3306。
- 依赖安装失败：确认 Python 包索引和 npm registry 可访问，不要复制另一台电脑的 `.venv` 或 `node_modules`。

## 5. 安全边界

仓库包含后端源码、知识库和正式 V1.4 资产、前端源码及测试；不包含 `.env`、真实患者数据、数据库文件、虚拟环境、Node 依赖或 `outputs/` 临时文件。Phase 5D 的 egg-free exact snack 资产与 provenance 已登记在 manifest 中。
