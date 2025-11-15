"""
LLM 提示词构造模块

集中管理所有与 DeepSeek 交互的提示词构造逻辑，确保：
- 代码清晰、集中、易于修改
- 所有提示词相关的修改只需在此处进行
- 包含完整的 JSON schema 说明和注释
"""
from __future__ import annotations
from typing import List, Tuple
from core.memory.types import SearchResult
from core.memory.classifier import MemoryStoreDecision

# ============================================================================
# 系统提示词（BASE_SYSTEM_PROMPT）
# ============================================================================
# 
# 用途：定义 Jarvis 的核心行为规范，要求 LLM 返回结构化 JSON
# 
# JSON Schema 要求：
# {
#   "reply": "<自然语言回复>",
#   "memories_to_store": [
#     {
#       "content": "<适合写入记忆库的单句事实>",
#       "tags": ["可选的标签数组"],
#       "metadata": {
#         "importance": 0.1~1.0,        // 重要性评分（可选）
#         "event_date": "YYYY-MM-DD",   // 事件日期（可选）
#         "valid_from": "ISO 时间字符串", // 有效期开始（可选）
#         "valid_to": "ISO 时间字符串或 null", // 有效期结束（可选）
#         "...": "其他有用字段"
#       }
#     }
#   ]
# }
#
# 稳定字段：
# - reply: 始终存在，自然语言回复
# - memories_to_store: 始终存在，数组（可能为空）
# - memories_to_store[].content: 始终存在，字符串
#
# 可扩展字段：
# - memories_to_store[].tags: 未来可能扩展为分类体系
# - memories_to_store[].metadata: 未来可能添加更多元数据字段
#
# ============================================================================

BASE_SYSTEM_PROMPT = """
你是 Jarvis 的对话与记忆助手。每次对话你要同时完成两件事：

1. 回复用户（字段：reply）
2. 如果本次对话中出现了值得长期记忆的内容，帮用户提炼成若干条“记忆项”（字段：memories_to_store）

你必须返回一个【严格的 JSON 对象】，格式如下：

{
  "reply": "<你要回复给用户的话>",
  "memories_to_store": [
    {
      "content": "<适合写入记忆库的单句事实>",
      "tags": ["可选的标签数组"],
      "metadata": {
        "importance": 0.1~1.0,
        "event_date": "YYYY-MM-DD，可选",
        "valid_from": "ISO 时间字符串，可选",
        "valid_to": "ISO 时间字符串或 null，可选",
        "...": "你认为有用的其他字段"
      }
    }
  ]
}

要求说明：

- 一定要返回合法 JSON：
  - 不能包含注释、额外说明文字或多余的 key。
  - 不要在 JSON 外再包一层自然语言解释。
- reply：
  - 是给用户看的自然语言完整回复，可以包含多句。
  - 语言风格保持自然、礼貌，默认用用户使用的语言（如果用户中文，就用中文回复）。
- memories_to_store：
  - 只在“确实值得长期记忆”的时候才添加，例如：
    - 用户的长期事实（住址、家庭成员、宠物、工作经历等）；
    - 用户的重要偏好（饮食、作息、工作习惯等）；
    - 重要的计划、约定、决策（手术日期、会议时间、出差安排等）。
  - content：
    - 必须是单句、清晰、独立的事实陈述，方便以后单独检索。
    - 避免冗长段落或把多个事实塞进一条。
  - tags：
    - 用于分类和检索，可以是你自己判断的标签。
    - 目前不限制标签内容，但建议选择 1~5 个简短、稳定的标签，例如：
      - "type:profile", "type:health", "type:plan", "type:work", "type:family", "type:pet" 等。
  - metadata：
    - importance：这条记忆的重要性（0.1=很低，1.0=非常重要），你根据语义打分。
    - event_date / valid_from / valid_to：
      - 当用户提到明确的事件时间（例如某天开会、手术、出差），尽量填上；
      - 如果只有一天的事件，可以只填 event_date；
      - 如果有起止时间，可以用 valid_from / valid_to。
    - 你可以在 metadata 里加入其他你认为有用的键值，但要保证整体仍是合法 JSON。

关于“当前记忆策略（policy）”：

- 系统会告诉你当前 policy 的值，可能是：
  - EXPLICIT_STORE：用户显式说“帮我记一下”、“为了记录：……”。在这种情况下，你【至少】应该返回一条 memories_to_store。
  - NEVER_STORE：这是明显的一次性命令、调试信息或纯粹的问题。通常你应该让 memories_to_store 为空数组。
  - CANDIDATE：不确定是否要记，你需要自行判断。如果是长期事实、重要偏好或关键计划，就提炼为记忆项；否则可以不记。

请严格遵守以上 JSON 格式和行为约束。
""".strip()


def build_deepseek_prompt(
    user_input: str,
    policy: MemoryStoreDecision,
    related_memories: List[SearchResult]
) -> Tuple[str, str]:
    """
    根据当前用户输入、记忆策略和检索到的相关记忆，构造：
    - system_prompt: 传给 DeepSeek 的系统提示
    - user_prompt:   传给 DeepSeek 的用户内容
    
    Args:
        user_input: 用户输入的文本
        policy: 记忆存储决策（EXPLICIT_STORE / NEVER_STORE / CANDIDATE）
        related_memories: 检索到的相关记忆列表
        
    Returns:
        (system_prompt, user_prompt) 元组
    """
    # 1. 构建系统提示词（基础 + 策略说明）
    system_prompt = BASE_SYSTEM_PROMPT
    
    # 根据 policy 添加策略说明
    policy_instruction = ""
    if policy == MemoryStoreDecision.EXPLICIT_STORE:
        policy_instruction = """

当前 policy = EXPLICIT_STORE：用户显式要求你"帮忙记录"。
在这种情况下，你至少应该在 memories_to_store 中给出一条记忆。
"""
    elif policy == MemoryStoreDecision.NEVER_STORE:
        policy_instruction = """

当前 policy = NEVER_STORE：这是一条调试/命令/一次性问句。
一般情况下，你应该返回空的 memories_to_store 数组。
"""
    else:  # CANDIDATE
        policy_instruction = """

当前 policy = CANDIDATE：你自行判断是否需要记忆。
如果是长期事实、重要偏好或关键决定，就提炼并加入 memories_to_store。
"""
    
    system_prompt += policy_instruction
    
    # 2. 构建用户提示词
    user_prompt_parts = []
    
    # 2.1 相关历史记忆部分
    if related_memories:
        user_prompt_parts.append("下面是与用户本次发言相关的一些历史记忆（可能为空）：")
        user_prompt_parts.append("")
        
        for idx, mem in enumerate(related_memories, 1):
            # 格式化时间戳
            time_str = ""
            if mem.timestamp:
                try:
                    from datetime import datetime
                    # 尝试解析时间戳（可能是 ISO 格式或毫秒时间戳）
                    if mem.timestamp.isdigit():
                        # 毫秒时间戳
                        ts_ms = int(mem.timestamp)
                        dt = datetime.fromtimestamp(ts_ms / 1000.0)
                        time_str = dt.strftime("%Y-%m-%d %H:%M")
                    else:
                        # ISO 格式
                        dt = datetime.fromisoformat(mem.timestamp.replace("Z", "+00:00"))
                        time_str = dt.strftime("%Y-%m-%d %H:%M")
                except:
                    # 解析失败，使用原始值的前16个字符
                    time_str = mem.timestamp[:16] if len(mem.timestamp) > 16 else mem.timestamp
            
            # 构建记忆条目
            type_str = f"[{mem.type}]" if mem.type else ""
            if time_str:
                mem_line = f"{idx}) {type_str} {mem.content}（时间：{time_str}）"
            else:
                mem_line = f"{idx}) {type_str} {mem.content}"
            
            user_prompt_parts.append(mem_line)
        
        user_prompt_parts.append("")
        user_prompt_parts.append("---")
        user_prompt_parts.append("")
    
    # 2.2 用户本次发言
    user_prompt_parts.append("用户本次发言：")
    user_prompt_parts.append(user_input)
    user_prompt_parts.append("")
    user_prompt_parts.append("请基于以上信息，返回 JSON 格式的回复。")
    
    user_prompt = "\n".join(user_prompt_parts)
    
    return system_prompt, user_prompt

