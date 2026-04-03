# kindle-dashboard

🧾 Make your Kindle more than a instant noodles lid 🫵

> 将 Kindle 电子书阅读器变成常显仪表盘 — 显示天气、日历、新闻等实时信息。

## 架构

```
dashboard-server/
├── config/          # 配置层 (dataclass 化的配置对象)
│   ├── __init__.py  #   load_config() + Config 兼容类 + AppConfig 聚合类
│   ├── settings.py  #   ServerConfig, ScreenConfig, LocationConfig
│   ├── ink.py       #   InkDisplayConfig
│   ├── cache.py     #   CacheTTLConfig
│   └── pages.py     #   PageItem, PageRepository
├── services/        # 服务层 (独立数据服务 + 统一缓存)
│   ├── __init__.py  #   ServiceRegistry + build_registry()
│   ├── base.py      #   SimpleCache, ServiceProtocol
│   ├── weather.py   #   WeatherService (Open-Meteo)
│   ├── calendar.py  #   CalendarService (农历 + 节假日)
│   ├── news.py      #   HackerNewsService + GitHubTrendingService
│   └── finance.py   #   FinanceService (yfinance + sparkline)
├── renderer/        # 渲染层 (Playwright + PIL 图像处理)
│   ├── __init__.py  #   render_dashboard_to_bytes 入口
│   ├── browser.py   #   DashboardRenderer (浏览器截图)
│   └── processing.py#   ImageProcessor (灰度量化 + 防抖)
├── app/             # 应用层 (Flask 工厂 + 路由)
│   ├── __init__.py  #   create_app() 工厂函数
│   ├── routes.py    #   所有 HTTP 路由
│   ├── dashboard.py #   fetch_dashboard_data() 数据聚合
│   ├── cache.py     #   RenderCache (页面截图缓存)
│   └── workers.py   #   BackgroundTaskScheduler + FailureTracker
├── templates/       #   Jinja2 模板
├── app.py           #   Gunicorn 入口 (app:app)
├── main.py          #   开发模式入口
├── test_render.py   #   渲染测试
├── start.sh         #   Docker 启动脚本
├── Dockerfile       #   容器镜像
├── pyproject.toml   #   依赖管理 (uv)
├── config.yaml.example # 配置模板
└── pages_default.json  # 默认页面布局
```

## 快速开始

### 开发环境

```bash
cd dashboard-server
uv sync
playwright install chromium
uv run python main.py
```

### Docker

```bash
cd dashboard-server
docker build -t kindle-dashboard .
docker run -d -p 15000:15000 kindle-dashboard
```

### 配置

复制并编辑配置文件：

```bash
cp config.yaml.example config.yaml
```

主要配置项：

| 配置项 | 说明 | 默认值 |
|---|---|---|
| `dashboard.server.port` | 服务端口 | `15000` |
| `dashboard.location` | 地理位置和时区 | 深圳 / Asia/Shanghai |
| `dashboard.screen` | 屏幕分辨率 | `800x600` |
| `dashboard.locale.language` | 语言 (`CN` / `EN`) | `CN` |
| `dashboard.cache_ttl` | 各数据源缓存时间 | 天气 600s, 新闻 300s |
| `dashboard.finance.tickers` | 股票/加密货币 | SGD/CNY, USD/CNY, BTC/USD |
| `ink_setting.img_url` | Kindle 拉取图片的 URL | `http://127.0.0.1:15000/render` |

## API

| 端点 | 说明 |
|---|---|
| `GET /dashboard/<page_id>` | 渲染仪表盘 HTML 页面 |
| `GET /api/data?page=<page_id>` | 返回 JSON 格式的数据 |
| `GET /api/settings` | 返回所有配置项 |
| `GET /api/ink_setting` | 返回 Kindle Ink 屏幕配置 |
| `GET /render` | 返回渲染后的 PNG 图片 (e-ink 优化) |
| `GET /health` | 健康检查 |

## Kindle 端

Kindle 设备通过 KUAL (Kindle Unified Application Launcher) 扩展运行脚本，定时从服务器拉取 `/render` 返回的图片并显示。

`kual-extension/` 目录为 KUAL 扩展预留，目前为空。

## 技术栈

- **Python 3.12+** / **Flask** / **Gunicorn** (gthread worker)
- **Playwright** — 无头浏览器渲染
- **Pillow** — 16 色灰度量化 + Floyd-Steinberg 防抖
- **Open-Meteo** — 天气 + 空气质量 API
- **yfinance** / **matplotlib** — 金融数据 + 走势图
- **holidays** / **lunardate** — 节假日 + 农历
- **uv** — 包管理和虚拟环境

## License

MIT