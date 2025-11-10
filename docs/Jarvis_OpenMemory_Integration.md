# 🧠 Jarvis × OpenMemory 集成设计文档  
**版本：v1.0**  
**更新时间：2025-11-10**

---

## 一、总体定位

**OpenMemory 是 Jarvis 的长期记忆系统（Long-term Memory Layer）**，  
负责存储、组织、检索和时间化管理。  
Jarvis 负责理解与决策，LLM 负责语言生成。

整体架构：

```
User → Jarvis Controller → OpenMemory → LLM (DeepSeek / GPT / Claude)
```

- **Jarvis Controller**：解析意图，判断是否要记忆、怎么记。  
- **OpenMemory**：存储语义和时间事实，提供召回和检索。  
- **LLM**：在上下文中生成语言回答。

---

## 二、OpenMemory 存储方式

OpenMemory 提供两种核心写入接口：

| 类型 | 接口路径 | 内容形态 | 是否带时间 | 使用场景 |
|------|-----------|-----------|-------------|-----------|
| 普通记忆 | `/memory/add` | 自然语言文本 | ❌ | 主观偏好、总结、经历 |
| 时序事实 | `/api/temporal/fact` | 三元组 (subject, predicate, object) | ✅ | 状态变化、事实演化、版本追踪 |

### 示例

#### 普通记忆
```bash
curl -X POST http://localhost:8080/memory/add   -H "Content-Type: application/json"   -H "Authorization: Bearer $OM_API_KEY"   -d '{"content": "我家狗叫丁丁，11岁，公狗。", "user_id": "u1", "sector": "semantic"}'
```

#### 时序事实
```bash
curl -X POST http://localhost:8080/api/temporal/fact   -H "Content-Type: application/json"   -H "Authorization: Bearer $OM_API_KEY"   -d '{"subject": "OpenAI", "predicate": "has_CEO", "object": "Sam Altman", "valid_from": "2019-03-01", "confidence": 0.98}'
```

---

## 三、Jarvis 的决策逻辑（何时用哪种方式）

OpenMemory 不会自动判断“这句话该存哪类”，  
Jarvis 控制器负责选择调用 `/memory/add` 或 `/temporal/fact`。

### 决策树

```
输入语句 →
   ├─ 是否包含时间/状态变化？
   │      ├─ 是 → temporal/fact
   │      └─ 否 → memory/add
   │
   └─ 是否为主观语义/偏好/总结？
          → memory/add
```

### 关键词触发参考

| 触发类型 | 示例关键词 | 推荐接口 |
|-----------|--------------|-----------|
| 时间/状态类 | “从…开始”、“截至…”、“生效”、“改为”、“状态为…” | temporal/fact |
| 主观/语义类 | “我喜欢”、“我打算”、“我觉得”、“记录一下” | memory/add |
| 混合型信息 | “出差计划、会议安排、设备状态” | 双写（add + fact） |

---

## 四、内部工作机制

### 1️⃣ 层级记忆分解 HMD（Hierarchical Memory Decomposition）
- 每条记忆 = 一个节点；
- 多个 sector 向量（semantic / episodic / procedural）；
- Top-K 检索后进行一跳扩展；
- 排序逻辑：  
  `0.6×语义相似度 + 0.2×重要性 + 0.1×新近性 + 0.1×关联权重`

### 2️⃣ 时序知识图谱（Temporal Knowledge Graph）
- 每条事实带 `valid_from` / `valid_to` / `confidence`；
- 支持：
  - 按时间点查询（at）
  - 比较两个时间点变化
  - 自动衰减置信度
- 常用接口：
  - `/api/temporal/fact`
  - `/api/temporal/timeline`
  - `/api/temporal/compare`

### 3️⃣ 向量嵌入引擎（Embedding）
- 默认：`synthetic 256D`（轻量离线）
- 可选：OpenAI / DeepSeek / BGE / Ollama / Gemini
- `.env` 示例：
  ```ini
  OM_EMBED_PROVIDER=deepseek
  DEEPSEEK_API_KEY=ds-xxxx
  OM_TIER=hybrid
  ```

---

## 五、Jarvis 工作闭环

```
1️⃣ 用户输入
     ↓
2️⃣ Jarvis 控制层判断：
      - 是否要记忆？
      - 是语义型还是时序型？
     ↓
3️⃣ 调用 OpenMemory 写入接口
     ↓
4️⃣ 调用 OpenMemory 查询接口（召回相关记忆）
     ↓
5️⃣ 将召回记忆 + 当前输入 拼接成 Prompt
     ↓
6️⃣ 调用 LLM（DeepSeek / GPT）
     ↓
7️⃣ 输出回答 & 可选写回记忆
```

---

## 六、职责划分

| 模块 | 功能 | 决策方 |
|------|------|--------|
| 输入解析 | 理解语义、意图 | ✅ Jarvis |
| 写入类型选择 | 选 add / fact | ✅ Jarvis |
| 向量生成 | Embedding 模型 | ❌ OpenMemory |
| 存储与召回 | 向量索引 + SQL | ❌ OpenMemory |
| Prompt 组装 | 将记忆注入上下文 | ✅ Jarvis |
| 语言生成 | 自然语言回复 | ❌ LLM |
| 回写决策 | 是否保存对话结果 | ✅ Jarvis |

---

## 七、Jarvis 内部接口封装建议

```python
class MemoryManager:
    def store_memory(self, content: str, user_id: str, sector: str = "semantic"): ...
    def store_fact(self, subject: str, predicate: str, object: str, valid_from: str): ...
    def recall(self, query: str, user_id: str, k: int = 5): ...
    def timeline(self, subject: str, predicate: str): ...
```
> 对上层屏蔽 API 细节，可自由切换后端。

---

## 八、最佳实践

1. **一事两存**：关键事件同时写入 `/memory/add` 与 `/temporal/fact`。  
2. **始终带 `user_id`**：支持多用户隔离。  
3. **用 PostgreSQL**：数据量上万时比 SQLite 稳定。  
4. **周期衰减机制**：启用 node-cron 自动衰减置信度低的旧记忆。  
5. **测试流程**：先跑 `/health` → `/memory/add` → `/query`，确认健康状态。

---

## 九、扩展与集成方向

| 方向 | 说明 |
|------|------|
| **LangGraph 模式** | memory/query/store 可嵌入 Agent 流程 |
| **MCP 接口** | 支持 Cursor、Claude Desktop 等 IDE 直接连接记忆系统 |
| **DeepSeek / GPT** | Jarvis 主对话 LLM 层 |
| **未来增强** | 图谱衰减、事件聚类、自监督“记忆总结”模块 |

---

## 十、配置参考（示例）

```ini
# === 基础配置 ===
OM_PORT=8080
OM_API_KEY=lu81998693
OM_TIER=hybrid

# === Embedding Provider ===
OM_EMBED_PROVIDER=deepseek
DEEPSEEK_API_KEY=ds-xxxxxxxxxxxxxxxx

# === 数据存储 ===
OM_DB_PATH=data/openmemory.db
OM_DB_TYPE=sqlite

# === 服务模式 ===
OM_MODE=default
OM_CORS=*
```

---

## 十一、总结

- OpenMemory ≈ Jarvis 的「外部长期记忆层」  
- 它本身不回答问题，只负责存储与召回上下文  
- Jarvis 决策“记不记、记什么、怎么记”  
- LLM 负责生成自然语言回复  
- 三者协同后，Jarvis 才真正具备「具身记忆能力」
