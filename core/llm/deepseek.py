"""
DeepSeek LLM 客户端
"""
from __future__ import annotations
from typing import Optional, List, Dict, Any
from utils.http import request_json
from utils.logger import get_logger

log = get_logger(__name__)

class LLMDisabledError(Exception):
    """LLM 未启用异常（API Key 缺失）"""
    pass

DEFAULT_DEEPSEEK_BASE_URL = "https://api.deepseek.com"

def chat_completion(
    system_prompt: str,
    user_prompt: str,
    api_key: Optional[str] = None,
    base_url: Optional[str] = None,
    timeout_s: int = 10
) -> str:
    """
    DeepSeek Chat 完成
    
    Args:
        system_prompt: 系统提示词
        user_prompt: 用户提示词（已格式化好的完整内容）
        api_key: API 密钥（若为空则抛出 LLMDisabledError）
        base_url: API 基础地址（默认使用官方地址）
        timeout_s: 超时时间（秒）
    
    Returns:
        模型回复文本（原始 JSON 字符串）
    
    Raises:
        LLMDisabledError: API Key 缺失时抛出
        Exception: 网络或 HTTP 错误时抛出
    """
    if not api_key:
        raise LLMDisabledError("DEEPSEEK_API_KEY is not set")
    
    base = base_url or DEFAULT_DEEPSEEK_BASE_URL
    url = f"{base.rstrip('/')}/v1/chat/completions"
    
    # 构建请求体
    payload = {
        "model": "deepseek-chat",
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ],
        "temperature": 0.7,
        "max_tokens": 2000  # 增加 token 限制以支持 JSON 输出
    }
    
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}"
    }
    
    try:
        log.debug(f"Calling DeepSeek API: {url}")
        resp = request_json(
            method="POST",
            url=url,
            headers=headers,
            json=payload,
            timeout=timeout_s
        )
        
        # 提取回复文本（返回原始内容，由调用方解析 JSON）
        if "choices" in resp and len(resp["choices"]) > 0:
            message = resp["choices"][0].get("message", {})
            content = message.get("content", "")
            return content.strip()
        else:
            raise Exception(f"Unexpected response format: {resp}")
    
    except Exception as e:
        log.error(f"DeepSeek API call failed: {type(e).__name__}: {e}")
        raise

