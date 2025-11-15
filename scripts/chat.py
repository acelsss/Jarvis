"""
Jarvis Chat REPL：重构后的记忆读写闭环

流程：
1. 用户输入 → 消息分类（EXPLICIT_STORE / NEVER_STORE / CANDIDATE）
2. 检索相关记忆（带时间戳）
3. 构造 LLM 提示词（集中、清晰、易改）
4. 调用 DeepSeek，解析 JSON 返回
5. 根据 LLM 建议写入记忆（支持去重状态显示）
"""
from __future__ import annotations
import sys
import json
from typing import List
from utils.config import Settings
from utils.logger import get_logger
from core.memory.client import MemoryClient
from core.memory.types import make_memory_item
from core.memory.classifier import classify_message_for_memory, MemoryStoreDecision
from core.memory.metadata_builder import build_final_tags_and_metadata
from core.llm.deepseek import chat_completion, LLMDisabledError
from core.llm.prompt_builder import build_deepseek_prompt
from core.llm.response_parser import parse_deepseek_response, LLMMemoryItem

log = get_logger(__name__)


def main():
    """REPL 主循环"""
    settings = Settings.load()
    
    # 初始化 MemoryClient
    mem_client = MemoryClient(settings.om, logger=log)
    user_id = settings.om.user_id or "lushan"
    channel = "repl"
    
    print("=" * 60)
    print("Jarvis Chat REPL")
    print("=" * 60)
    print("流程：分类 → 检索 → LLM → 落盘")
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
            
            # ============================================================
            # 1. 消息分类
            # ============================================================
            policy = classify_message_for_memory(user_input)
            log.info(f"[Jarvis][classify] policy={policy.value}, input_len={len(user_input)}")
            
            # ============================================================
            # 2. 检索相关记忆
            # ============================================================
            search_hits = 0
            related_memories = []
            try:
                search_results = mem_client.search(
                    query_text=user_input,
                    limit=settings.om.search_limit,
                    exclude_types=settings.om.exclude_types
                )
                search_hits = len(search_results)
                related_memories = search_results
                
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
                        
                        # 格式化时间戳
                        ts_str = result.timestamp or "N/A"
                        type_str = result.type or "N/A"
                        
                        log.info(f"[debug][memory] #{idx} (score={score_str}, type={type_str}, ts={ts_str})")
                        log.info(f"[debug][memory]   {content_display}")
            except Exception as e:
                log.error(f"[Jarvis][search] Failed: {type(e).__name__}: {e}")
            
            # ============================================================
            # 3. 构造 LLM 提示词并调用
            # ============================================================
            llm_status = "offline"
            reply = ""
            memories_to_store: List[LLMMemoryItem] = []
            
            try:
                # 构造提示词（集中、清晰、易改）
                system_prompt, user_prompt = build_deepseek_prompt(
                    user_input=user_input,
                    policy=policy,
                    related_memories=related_memories
                )
                
                # 调试输出：打印 messages payload
                messages = [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ]
                messages_json = json.dumps(messages, ensure_ascii=False, indent=2)
                log.info(f"[debug][llm] messages payload:\n{messages_json}")
                
                # 调用 DeepSeek
                raw_response = chat_completion(
                    system_prompt=system_prompt,
                    user_prompt=user_prompt,
                    api_key=settings.llm.deepseek_api_key,
                    base_url=settings.llm.deepseek_base_url,
                    timeout_s=10
                )
                
                # 解析返回的 JSON
                reply, memories_to_store = parse_deepseek_response(raw_response)
                llm_status = "used"
                print(f"Jarvis> {reply}")
                
            except LLMDisabledError:
                # 降级模式
                reply = f"已检索到 {search_hits} 条相关记忆。当前未启用 LLM 生成答复。"
                print(f"Jarvis> {reply}")
            except Exception as e:
                log.error(f"[Jarvis][llm] Failed: {type(e).__name__}: {e}")
                reply = f"已检索到 {search_hits} 条相关记忆。LLM 服务暂时不可用。"
                print(f"Jarvis> {reply}")
            
            # ============================================================
            # 4. 写入记忆（根据 LLM 建议）
            # ============================================================
            store_statuses = []
            
            # 4.1 处理 LLM 返回的 memories_to_store
            if memories_to_store:
                for mem_item in memories_to_store:
                    try:
                        # 合并 tags 和 metadata
                        final_tags, final_metadata = build_final_tags_and_metadata(
                            llm_tags=mem_item.tags,
                            llm_metadata=mem_item.metadata,
                            user_id=user_id,
                            channel=channel,
                            autolog=(policy != MemoryStoreDecision.EXPLICIT_STORE)  # 显式要求记录 → autolog=False
                        )
                        
                        # 创建 MemoryItem
                        memory_item = make_memory_item(
                            content=mem_item.content,
                            default_type=settings.om.store_default_type,
                            source_app=settings.om.source,
                            channel=channel,
                            tags=final_tags,
                            metadata=final_metadata
                        )
                        
                        # 写入 OpenMemory
                        store_result = mem_client.store(memory_item)
                        
                        if store_result.status == "error":
                            store_statuses.append("error")
                            log.warning(f"[Jarvis][store] Failed to store: {mem_item.content[:50]}...")
                        else:
                            store_statuses.append(store_result.status)
                            log.info(f"[Jarvis][store] {store_result.status}: {mem_item.content[:50]}...")
                    
                    except Exception as e:
                        log.error(f"[Jarvis][store] Error storing memory: {type(e).__name__}: {e}")
                        store_statuses.append("error")
            
            # 4.2 EXPLICIT_STORE 的 fallback 处理
            if policy == MemoryStoreDecision.EXPLICIT_STORE:
                # 如果 JSON 解析失败或 memories_to_store 为空，使用 fallback
                if not memories_to_store:
                    log.info("[Jarvis][store] EXPLICIT_STORE fallback: storing user input directly")
                    try:
                        # 从用户输入中去掉显式前缀
                        content = user_input
                        for prefix in ["为了记录：", "为了记录,", "为了记录，", "帮我记一下", "帮我记住", "记一下", "记住这个"]:
                            if content.startswith(prefix):
                                content = content[len(prefix):].strip()
                                break
                        
                        if content:
                            # 使用系统 tags/metadata
                            final_tags, final_metadata = build_final_tags_and_metadata(
                                llm_tags=None,
                                llm_metadata=None,
                                user_id=user_id,
                                channel=channel,
                                autolog=False  # 显式要求记录
                            )
                            
                            memory_item = make_memory_item(
                                content=content,
                                default_type=settings.om.store_default_type,
                                source_app=settings.om.source,
                                channel=channel,
                                tags=final_tags,
                                metadata=final_metadata
                            )
                            
                            store_result = mem_client.store(memory_item)
                            if store_result.status != "error":
                                store_statuses.append("fallback")
                                log.info(f"[Jarvis][store] fallback: {content[:50]}...")
                    except Exception as e:
                        log.error(f"[Jarvis][store] Fallback failed: {type(e).__name__}: {e}")
            
            # 4.3 NEVER_STORE 策略：忽略 LLM 返回的 memories_to_store
            if policy == MemoryStoreDecision.NEVER_STORE:
                # 对于明显 debug/命令类输入，不写入任何记忆
                if memories_to_store:
                    log.info(f"[Jarvis][store] NEVER_STORE: ignoring {len(memories_to_store)} LLM-suggested memories")
            
            # ============================================================
            # 5. 打印摘要
            # ============================================================
            if store_statuses:
                # 统计状态
                status_summary = {}
                for s in store_statuses:
                    status_summary[s] = status_summary.get(s, 0) + 1
                
                status_str = ", ".join([f"{k}={v}" for k, v in status_summary.items()])
                print(f"[store: {status_str}] [search: hits={search_hits}] [llm: {llm_status}]")
            else:
                print(f"[store: none] [search: hits={search_hits}] [llm: {llm_status}]")
            print()
        
        except Exception as e:
            # 任何异常都不退出 REPL
            log.error(f"[Jarvis] Unexpected error: {type(e).__name__}: {e}")
            print(f"⚠️  发生错误：{type(e).__name__}，继续下一轮...")
            print()


if __name__ == "__main__":
    main()
