"""
Jarvis Chat REPL：极简闭环（存储 → 检索 → LLM 回复）
"""
from __future__ import annotations
import sys
import json
from datetime import datetime
from utils.config import Settings
from utils.logger import get_logger
from core.memory.client import MemoryClient
from core.memory.types import make_memory_item
from core.llm.deepseek import chat_completion, LLMDisabledError

log = get_logger(__name__)

SYSTEM_PROMPT = """你是一个智能助手 Jarvis。用户会向你提问或分享信息。
请结合用户的本轮发言和相关记忆（如果有）给出简洁、有用的回复。
如果相关记忆为空，仅基于用户本轮发言作答。"""

def format_memory(result) -> str:
    """格式化记忆为短句"""
    content = result.content[:100]  # 限制长度
    if len(result.content) > 100:
        content += "..."
    
    # 提取日期
    date_str = ""
    if result.timestamp:
        try:
            dt = datetime.fromisoformat(result.timestamp.replace("Z", "+00:00"))
            date_str = dt.strftime("%Y-%m-%d")
        except:
            pass
    
    type_str = f"[{result.type}]" if result.type else ""
    return f"{type_str} {content}（{date_str}）" if date_str else f"{type_str} {content}"

def main():
    """REPL 主循环"""
    settings = Settings.load()
    
    # 初始化 MemoryClient
    mem_client = MemoryClient(settings.om, logger=log)
    
    print("=" * 60)
    print("Jarvis Chat REPL")
    print("=" * 60)
    print("每句话都会：存储 → 检索 → LLM 回复")
    print("输入空行忽略，Ctrl+C 或 Ctrl+D 退出")
    print("=" * 60)
    print()
    
    while True:
        try:
            # 读取用户输入
            try:
                user_input = input("You> ").strip()
            except (EOFError, KeyboardInterrupt):
                print("\n👋 再见")
                break
            
            if not user_input:
                continue
            
            # a. 立即存储
            store_status = "ok"
            try:
                item = make_memory_item(
                    content=user_input,
                    default_type=settings.om.store_default_type,
                    source_app=settings.om.source,
                    channel="chat"
                )
                store_result = mem_client.store(item)
                if store_result.get("queued"):
                    store_status = "queued"
            except Exception as e:
                log.error(f"Store failed: {type(e).__name__}: {e}")
                store_status = "error"
            
            # b. 检索相关记忆
            search_hits = 0
            memories_text = []
            try:
                search_results = mem_client.search(
                    query_text=user_input,
                    limit=settings.om.search_limit,
                    exclude_types=settings.om.exclude_types
                )
                search_hits = len(search_results)
                
                # 调试输出：命中记忆内容和分数
                if search_hits == 0:
                    log.info("[debug][memory] no hits")
                else:
                    log.info(f"[debug][memory] hits={search_hits}")
                    for idx, result in enumerate(search_results, 1):
                        # 安全截断 content（最多 120 字符）
                        content_display = result.content or ""
                        if len(content_display) > 120:
                            content_display = content_display[:120] + "..."
                        
                        # 格式化 score（保留 3 位小数，允许 None）
                        score_str = f"{result.score:.3f}" if result.score is not None else "None"
                        
                        log.info(f"[debug][memory] #{idx} score={score_str} content={content_display}")
                
                # 转换为短句列表
                for result in search_results:
                    memories_text.append(format_memory(result))
            except Exception as e:
                log.error(f"Search failed: {type(e).__name__}: {e}")
            
            # c. 调用 LLM 生成回复
            llm_status = "offline"
            reply = ""
            
            try:
                # 构造 messages（与 chat_completion 内部逻辑一致）
                memories_text_formatted = ""
                if memories_text:
                    memories_text_formatted = "\n相关记忆（可能为0~K条）：\n"
                    for i, mem in enumerate(memories_text, 1):
                        memories_text_formatted += f"{i}) {mem}\n"
                
                user_content = f"用户本轮发言：\n{user_input}\n"
                if memories_text_formatted:
                    user_content += f"\n{memories_text_formatted}\n请基于以上信息简洁作答。"
                else:
                    user_content += "\n请基于以上信息简洁作答。"
                
                messages = [
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": user_content}
                ]
                
                # 调试输出：打印 messages payload
                messages_json = json.dumps(messages, ensure_ascii=False, indent=2)
                log.info(f"[debug][llm] messages payload:\n{messages_json}")
                
                reply = chat_completion(
                    system_prompt=SYSTEM_PROMPT,
                    user_text=user_input,
                    memories=memories_text,
                    api_key=settings.llm.deepseek_api_key,
                    base_url=settings.llm.deepseek_base_url,
                    timeout_s=10
                )
                llm_status = "used"
                print(f"Jarvis> {reply}")
            except LLMDisabledError:
                # 降级模式
                reply = f"已存储本条信息，检索到 {search_hits} 条相关记忆。当前未启用 LLM 生成答复。"
                print(f"Jarvis> {reply}")
            except Exception as e:
                log.error(f"LLM call failed: {type(e).__name__}: {e}")
                reply = f"已存储本条信息，检索到 {search_hits} 条相关记忆。LLM 服务暂时不可用。"
                print(f"Jarvis> {reply}")
            
            # 打印摘要
            print(f"[store: {store_status}] [search: hits={search_hits}] [llm: {llm_status}]")
            print()
        
        except Exception as e:
            # 任何异常都不退出 REPL
            log.error(f"Unexpected error: {type(e).__name__}: {e}")
            print(f"⚠️  发生错误：{type(e).__name__}，继续下一轮...")
            print()

if __name__ == "__main__":
    main()

