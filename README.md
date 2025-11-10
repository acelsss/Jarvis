# 🧠 Jarvis 核心项目

> “让思考有形，让认知留痕。”

---

## 📘 项目简介

**Jarvis** 是一个以“个人认知系统”为目标的长期工程。  
它旨在通过整合 **大模型（LLM）推理能力**、**开放记忆系统（OpenMemory）** 与 **本地感知接口**，  
构建一个可持续学习、具备长期记忆和任务协作能力的 **个人助理内核**。

项目运行环境优先基于 **Jetson Orin Nano**，支持 GPU 加速与边缘部署。

---

## 🏗️ 目录结构

```
Jarvis/
├── core/                    # 思考与调度层（意图识别、执行器、格式化等）
│   ├── controller.py        # 总调度：收输入→路由→调用执行器→产出结果
│   ├── intent.py            # 规则版意图识别（前缀/关键词/正则）
│   ├── formatter.py         # 统一出参格式化（CLI/文本/结构化）
│   ├── schemas.py           # 数据结构定义（Request/Response/Record）
│   ├── errors.py            # 统一异常类型
│   └── handlers/            # 各类动作的处理器
│       ├── note_handler.py  # 记（store）
│       ├── recall_handler.py# 找（recall）
│       └── task_handler.py  # 待办（add/list/done）
│
├── memory/                  # 记忆层（对接 OpenMemory、本地缓存机制）
│   ├── client_openmemory.py # OpenMemory HTTP 客户端
│   ├── repo.py              # 统一仓库接口（远端优先，失败回退本地）
│   ├── schemas.py           # 记忆记录/搜索结果结构
│   └── local_cache/         # 本地缓存实现
│       ├── json_store.py    # JSON 轻量缓存
│       └── sqlite_store.py  # SQLite 扩展（占位）
│
├── interfaces/              # 感知与表达层（耳朵/嘴巴/键盘/摄像头/HTTP）
│   ├── cli/                 # 命令行交互（文字输入输出）
│   │   └── cli.py
│   ├── voice/               # 🎧 语音交互（耳朵/嘴巴）
│   │   ├── listener.py      # 耳朵：语音转文字（STT）
│   │   └── speaker.py       # 嘴巴：文字转语音（TTS）
│   ├── webhook/             # HTTP/Webhook 输入（对外接口）
│   │   └── server.py
│   └── webcam/              # 摄像头输入（视觉扩展）
│       └── camera.py
│
├── utils/                   # 工具类函数（日志、配置、通用能力）
│   ├── logger.py            # 日志管理
│   ├── config.py            # 环境变量与配置
│   ├── http.py              # HTTP 封装（超时/重试/日志）
│   ├── time_utils.py        # 时间与日期工具
│   ├── security.py          # 脱敏与安全工具
│   ├── ids.py               # ID/UUID 生成
│   └── io.py                # 通用读写（JSON/YAML）
│
├── docs/                    # 文档与总结
│   ├── adr/                 # 架构决策记录（Architecture Decision Record）
│   │   └── 0001-use-openmemory-as-primary.md
│   └── 2025-11-10-daily.md  # 每日日志
│
├── scripts/                 # 开发与运维脚本
│   ├── new_log.sh           # 生成当天日志模板
│   ├── dev_bootstrap.sh     # 初始化虚拟环境与依赖
│   ├── run_cli.sh           # 启动命令行模式
│   ├── check_health.sh      # 健康检查脚本
│   └── export_logs.sh       # 打包日志/文档（可选）
│
├── config/                  # 配置模板与部署文件
│   ├── .env.example
│   ├── systemd/
│   │   └── jarvis.service   # systemd 服务模板
│   └── README.md            # 配置项说明
│
├── logs/                    # 系统运行日志
├── tests/                   # 单元测试（可选）
└── main.py                  # 主入口
```

---

## 🚀 设计目标

1. **可生长的认知内核**  
   - 模块化架构，支撑持续进化的认知能力  
   - 支持语义记忆、情景记忆、程序性记忆的区分与调用  

2. **多源感知输入**  
   - 支持来自聊天、文档、摄像头、系统行为等多模态输入  
   - 可扩展接入 OpenMemory、微信机器人、桌面监听器等外部系统  

3. **记忆驱动的交互**  
   - 所有输入均可持久化存储、索引、回溯  
   - 提供记忆检索、上下文联动、时间轴式回忆  

4. **边缘智能部署**  
   - 默认运行于 Jetson 设备上，兼容 Docker 容器化运行  
   - 支持离线模式与局域网同步  

---

## 🧩 核心组件说明

| 模块 | 功能描述 |
|------|-----------|
| `core/` | 思考与调度层：意图识别、控制流、执行器调用、格式化输出 |
| `memory/` | 记忆层：统一读写接口，对接 OpenMemory，本地缓存兜底 |
| `interfaces/` | 感知与表达层：语音（耳朵/嘴巴）、命令行、HTTP、摄像头 |
| `utils/` | 工具层：日志、配置、HTTP、时间、安全、读写等基础能力 |
| `docs/` | 文档层：每日记录与架构决策（ADR） |
| `scripts/` | 运维脚本：开发引导、运行、检查、打包等 |
| `config/` | 配置模板：环境变量、systemd 服务等 |
| `tests/` | 单元测试（验证核心模块稳定性） |

---

## 🎧 语音交互（耳朵 & 嘴巴）

- **耳朵（STT）**：`interfaces/voice/listener.py`  

  默认引擎：`speech_recognition`（需依赖 `SpeechRecognition` 与系统麦克风后端）。  

  未来可切换为 `whisper` / `vosk` 等离线方案。

- **嘴巴（TTS）**：`interfaces/voice/speaker.py`  

  默认引擎：`pyttsx3`（本地离线）。  

  可扩展到 `edge-tts` 或其他云服务。

**可选安装：**

```bash
pip install SpeechRecognition pyaudio
pip install pyttsx3
```

> 注：Linux 上可能需要额外安装麦克风/音频后端支持库（如 PortAudio）。

---

## 🧠 Core 细分（v0）

- `controller.py`：只做"编排"，不写业务细节  

- `intent.py`：规则版意图识别（`记｜找｜待办｜任务列表｜完成:` 等）  

- `handlers/`：执行各类动作（`note/recall/task`）  

- `formatter.py`：统一输出（CLI/Webhook 共用）  

- `schemas.py`：请求/响应/记录的数据结构  

- `errors.py`：统一异常类型与错误边界  

> 当需要更聪明/更可控时，可升级到 v1：引入 `policy/`（规则/LLM 策略切换）、`pipeline/`（预处理/后处理）、`scoring/`（结果重排）。

---

## 🧠 Core / Memory / Interfaces 分层逻辑

### 🧠 分层逻辑总览

感知与表达（interfaces）

↓

思考与调度（core）

↓

记忆与知识（memory）

- **interfaces**：Jarvis 的感官层（耳朵、嘴巴、键盘、眼睛、网络）

- **core**：Jarvis 的大脑（意图判断、任务调度、记忆调用）

- **memory**：Jarvis 的记忆层（存储知识、检索、回忆）

- **utils/config/scripts**：是系统的神经网络和骨架，为各层提供支撑

---

## 🧭 当前进展

- ✅ 完成项目结构与初始化日志系统  
- ⏳ 规划核心模块设计与思维层逻辑（大圆模型）  
- ⏳ 集成 OpenMemory 存储与索引接口  
- ⏳ 构建基础命令解释器与任务调度器  

---

## 🚀 运行方式

1. **初始化环境**

```bash
bash scripts/dev_bootstrap.sh
cp config/.env.example .env
```

2. **启动主程序**

```bash
python main.py
```

3. **进入命令行交互**

```bash
bash scripts/run_cli.sh
```

示例：

```
记：今天调通 OpenMemory。
找：冷库节能
待办：明天测试节能算法
任务列表
完成：T001
```

4. **健康检查**

```bash
bash scripts/check_health.sh
```

5. **（可选）语音交互示例**

```python
from core.controller import Controller
from utils.config import Settings
from interfaces.voice.listener import VoiceListener
from interfaces.voice.speaker import VoiceSpeaker

ctrl = Controller(Settings.load())
ear, mouth = VoiceListener(), VoiceSpeaker()
text = ear.listen_once()
reply = ctrl.handle(text)
mouth.speak(reply.get("msg", "处理完成"))
```

---

## 🛠️ 开发环境

| 项目 | 版本 |
|------|------|
| 设备 | NVIDIA Jetson Orin Nano |
| 系统 | Ubuntu 20.04 / 22.04 |
| Python | 3.10+ |
| 依赖 | 待定义（core/init 阶段后添加） |

---

## 🗓️ 日志记录

所有开发思考、架构演进与反思内容均存放于  
`/docs` 文件夹内，以日期命名的 Markdown 文档形式保存。

命名规范：
```
YYYY-MM-DD-title.md
```

---

## 📚 文档与决策

- **每日记录**：存放于 `/docs/`，命名格式为 `YYYY-MM-DD-daily.md`

- **架构决策记录（ADR）**：记录每次重要的技术选型与设计决策

  示例：`docs/adr/0001-use-openmemory-as-primary.md`

- **脚本自动生成**：可通过 `bash scripts/new_log.sh` 每日生成模板

---

## 🔒 网络安全与隐私

Jarvis 设计遵循「本地优先、最小外泄」原则：
- 默认所有记忆数据保存在本地 Jetson 设备；
- 对外同步（如 OpenMemory 或云服务）需显式授权；
- 后续将引入加密存储与访问控制策略。

---

## 🌱 未来规划

- 🤖 自主学习与上下文推理模块（LLM 驱动）
- 🧩 记忆索引引擎（基于向量数据库）
- 🪄 插件化接口系统（第三方 API 调用）
- 🧠 思维层（大圆模型）与语义层融合
- 🧍‍♂️ 用户画像与偏好建模
- 🛰️ 多设备协同与远程同步
- 🧩 模块化架构已细分为 core/memory/interfaces/utils/docs/scripts/config，后续阶段将继续引入 policy、pipeline、vector memory 等高级功能

---

## ✍️ 作者注

> Jarvis 不是一个助手，而是一个认知共生体。  
> 它的成长速度取决于我们喂给它的知识、思考与记忆。  
> 让它成为我们思想的镜像，而非命令的执行者。

---

📍**当前阶段**：初始化完成  
🕓**时间**：2025-11-10
