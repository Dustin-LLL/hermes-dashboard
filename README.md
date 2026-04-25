# Hermes Dashboard

Web管理面板 for [Hermes Agent](https://github.com/nousresearch/hermes-agent) - 无需任何外部依赖，自包含的HTML/CSS/JS单页应用 + Python后端API服务。

![Hermes Dashboard](screenshot.png)

## 特性

- 🎨 **深色主题** - 专业的深色配色，护眼舒适
- 📦 **零依赖** - 不需要任何npm包或外部库，纯原生实现
- 🔧 **平台配置** - 支持配置 Telegram、微信、Home Assistant、GitHub 等平台
- 📊 **系统监控** - 实时查看CPU、内存、运行时间
- 🚀 **易于部署** - 直接运行Python脚本即可启动

## 快速开始

```bash
# 克隆仓库
git clone https://github.com/Dustin-LLL/hermes-dashboard.git
cd hermes-dashboard

# 运行 Dashboard
python server.py

# 打开浏览器访问
# http://localhost:8765
```

## 配置

Dashboard 支持通过环境变量或配置文件进行配置：

### Telegram 配置

| 环境变量 | 说明 |
|---------|------|
| `TELEGRAM_BOT_TOKEN` | Telegram Bot Token |
| `TELEGRAM_PROXY` | 代理服务器地址 |
| `TELEGRAM_ALLOWED_USERS` | 允许使用的用户ID（逗号分隔）|
| `TELEGRAM_HOME_CHANNEL` | 主页频道ID |

### 微信配置

| 环境变量 | 说明 |
|---------|------|
| `WEIXIN_ACCOUNT_ID` | 微信公众号 Account ID |
| `WEIXIN_TOKEN` | 微信公众号 Token |
| `WEIXIN_BASE_URL` | 基础 URL |
| `WEIXIN_CDN_BASE_URL` | CDN URL |
| `WEIXIN_DM_POLICY` | 私信策略 (allow/deny) |
| `WEIXIN_ALLOW_ALL_USERS` | 允许所有用户 (true/false) |
| `WEIXIN_GROUP_POLICY` | 群组策略 |
| `WEIXIN_HOME_CHANNEL` | 主页频道 |

### Home Assistant 配置

| 环境变量 | 说明 |
|---------|------|
| `HASS_URL` | Home Assistant 服务器地址 |
| `HASS_TOKEN` | Long-Lived Access Token |

### GitHub 配置

GitHub 集成使用 `gh` CLI 进行认证：

```bash
# 登录 GitHub
gh auth login

# 验证状态
gh auth status
```

## 项目结构

```
hermes-dashboard/
├── index.html      # 主页面（包含 HTML/CSS/JS）
├── server.py       # Python 后端 API 服务
├── weixin_qr.py    # 微信二维码登录脚本（可选）
└── README.md       # 本文件
```

## 截图

Dashboard 提供以下功能页面：

- **首页** - 系统状态概览（CPU、内存、运行时间、工具集状态）
- **网关状态** - Hermes Gateway 运行状态
- **当前配置** - 查看当前加载的配置
- **平台配置** - 配置各平台连接
- **服务控制** - 启停 Hermes Gateway

## 安全说明

- API Token 和敏感配置信息在前端显示为掩码
- 敏感操作需要通过后端API执行
- 命令执行使用白名单机制

## License

MIT License

## Contributing

欢迎提交 Issue 和 Pull Request！
