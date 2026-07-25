import json
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


class AIProviderError(Exception):
    pass


def _post_json(url: str, payload: dict, headers: dict | None = None) -> dict:
    if headers is None:
        headers = {"Content-Type": "application/json"}
    request = Request(url, data=json.dumps(payload).encode("utf-8"), headers=headers, method="POST")
    try:
        with urlopen(request, timeout=30) as response:
            raw = response.read().decode("utf-8")
            return json.loads(raw)
    except HTTPError as exc:
        raise AIProviderError(f"HTTP error {exc.code}: {exc.reason}")
    except URLError as exc:
        raise AIProviderError(f"请求失败: {exc.reason}")
    except ValueError:
        raise AIProviderError("返回内容不是有效 JSON")


def _stub_answer(provider: str, prompt: str) -> str:
    return (
        f"[{provider}] 当前为模拟模式，未配置真实 API。\n"
        f"请求提示：{prompt}\n"
        "请在 app/config.py 中设置相关环境变量以启用真实调用。"
    )


def _build_system_prompt(user_context: dict | None = None) -> str:
    system_content = "你是一个大学数学学习助手。直接输出内容，不要任何开场白或客套话，直接给出答案。"
    if user_context:
        system_content += f" 当前上下文：{user_context}"
    return system_content


def _iter_sse_lines(resp):
    """按行迭代 SSE 响应，处理跨 chunk 截断问题。"""
    buf = ""
    while True:
        chunk = resp.read(4096)
        if not chunk:
            break
        buf += chunk.decode("utf-8")
        while "\n" in buf:
            line, buf = buf.split("\n", 1)
            yield line.strip()


# ===== DeepSeek =====
def call_deepseek(prompt: str, user_context: dict | None = None) -> str:
    from .config import DEEPSEEK_API_KEY, DEEPSEEK_API_URL
    if not DEEPSEEK_API_KEY:
        return _stub_answer("DeepSeek", prompt)
    url = DEEPSEEK_API_URL or "https://api.deepseek.com/v1/chat/completions"
    headers = {"Content-Type": "application/json", "Authorization": f"Bearer {DEEPSEEK_API_KEY}"}
    payload = {
        "model": "deepseek-chat",
        "messages": [
            {"role": "system", "content": _build_system_prompt(user_context)},
            {"role": "user", "content": prompt},
        ],
        "temperature": 0.7,
        "max_tokens": 2048,
    }
    response = _post_json(url, payload, headers)
    if isinstance(response, dict) and "choices" in response:
        return response["choices"][0]["message"]["content"]
    return json.dumps(response, ensure_ascii=False)


def call_deepseek_stream(prompt: str, user_context: dict | None = None):
    from .config import DEEPSEEK_API_KEY, DEEPSEEK_API_URL
    if not DEEPSEEK_API_KEY:
        yield _stub_answer("DeepSeek", prompt)
        return
    import http.client
    from urllib.parse import urlparse
    api_url = DEEPSEEK_API_URL or "https://api.deepseek.com/v1/chat/completions"
    parsed = urlparse(api_url)
    payload = {
        "model": "deepseek-chat",
        "messages": [
            {"role": "system", "content": _build_system_prompt(user_context)},
            {"role": "user", "content": prompt},
        ],
        "temperature": 0.7, "max_tokens": 2048, "stream": True,
    }
    body = json.dumps(payload).encode("utf-8")
    conn = None
    try:
        conn = http.client.HTTPSConnection(parsed.netloc, timeout=60) if parsed.scheme == "https" else http.client.HTTPConnection(parsed.netloc, timeout=60)
        conn.request("POST", parsed.path, body=body, headers={"Content-Type": "application/json", "Authorization": f"Bearer {DEEPSEEK_API_KEY}"})
        resp = conn.getresponse()
        for line in _iter_sse_lines(resp):
            if line.startswith("data: ") and not line.startswith("data: [DONE]"):
                try:
                    d = json.loads(line[6:])
                    c = d.get("choices", [{}])[0].get("delta", {}).get("content", "")
                    if c:
                        yield c
                except json.JSONDecodeError:
                    pass
    except Exception as exc:
        yield f"[错误: {exc}]"
    finally:
        if conn:
            conn.close()


# ===== 讯飞星火 =====
def call_xunfei(prompt: str, user_context: dict | None = None) -> str:
    from .config import XUNFEI_API_KEY, XUNFEI_API_URL
    if not XUNFEI_API_KEY:
        return _stub_answer("讯飞星火", prompt)
    url = XUNFEI_API_URL or "https://spark-api-open.xf-yun.com/v1/chat/completions"
    # HTTP 兼容接口只用 API_KEY，不拼接 API_SECRET
    headers = {"Content-Type": "application/json", "Authorization": f"Bearer {XUNFEI_API_KEY}"}
    payload = {
        "model": "generalv3.5",
        "messages": [
            {"role": "system", "content": _build_system_prompt(user_context)},
            {"role": "user", "content": prompt},
        ],
        "temperature": 0.7, "max_tokens": 2048,
    }
    response = _post_json(url, payload, headers)
    if isinstance(response, dict) and "choices" in response:
        return response["choices"][0]["message"]["content"]
    return json.dumps(response, ensure_ascii=False)


def call_xunfei_stream(prompt: str, user_context: dict | None = None):
    from .config import XUNFEI_API_KEY, XUNFEI_API_URL
    if not XUNFEI_API_KEY:
        yield _stub_answer("讯飞星火", prompt)
        return
    import http.client
    from urllib.parse import urlparse
    api_url = XUNFEI_API_URL or "https://spark-api-open.xf-yun.com/v1/chat/completions"
    parsed = urlparse(api_url)
    payload = {
        "model": "generalv3.5",
        "messages": [
            {"role": "system", "content": _build_system_prompt(user_context)},
            {"role": "user", "content": prompt},
        ],
        "temperature": 0.7, "max_tokens": 2048, "stream": True,
    }
    body = json.dumps(payload).encode("utf-8")
    conn = None
    try:
        conn = http.client.HTTPSConnection(parsed.netloc, timeout=60) if parsed.scheme == "https" else http.client.HTTPConnection(parsed.netloc, timeout=60)
        conn.request("POST", parsed.path, body=body, headers={
            "Content-Type": "application/json",
            # HTTP 兼容接口只用 API_KEY，不拼接 API_SECRET
            "Authorization": f"Bearer {XUNFEI_API_KEY}",
        })
        resp = conn.getresponse()
        for line in _iter_sse_lines(resp):
            if line.startswith("data: ") and not line.startswith("data: [DONE]"):
                try:
                    d = json.loads(line[6:])
                    c = d.get("choices", [{}])[0].get("delta", {}).get("content", "")
                    if c:
                        yield c
                except json.JSONDecodeError:
                    pass
    except Exception as exc:
        yield f"[错误: {exc}]"
    finally:
        if conn:
            conn.close()


# ===== 统一接口 =====
def generate_answer(provider: str, prompt: str, user_context: dict | None = None) -> str:
    provider_key = provider.strip().lower()
    if provider_key in {"deepseek", "deepseekai"}:
        return call_deepseek(prompt, user_context)
    if provider_key in {"xunfei", "xunfeistar", "讯飞", "star"}:
        return call_xunfei(prompt, user_context)
    raise AIProviderError(f"不支持的 AI 供应商：{provider}")


def generate_answer_stream(provider: str, prompt: str, user_context: dict | None = None):
    provider_key = provider.strip().lower()
    if provider_key in {"deepseek", "deepseekai"}:
        yield from call_deepseek_stream(prompt, user_context)
    elif provider_key in {"xunfei", "xunfeistar", "讯飞", "star"}:
        yield from call_xunfei_stream(prompt, user_context)
    else:
        yield f"[不支持的AI供应商：{provider}]"


def generate_resource_content(provider: str, chapter_title: str, chapter_summary: str, resource_type: str) -> str:
    type_prompts = {
        "视频": f"请为章节「{chapter_title}」生成一个教学视频脚本大纲，包含视频分段标题、每段核心知识点、以及对应的板书要点。用 Markdown 格式输出。",
        "讲解文档": f"请为章节「{chapter_title}」生成一份详细的学习讲解文档。章节简介：{chapter_summary}\n\n要求：包含知识框架、核心概念解释、典型例题与解析、学习建议。用 Markdown 格式输出，使用 LaTeX 写数学公式。",
        "思维导图": f"请为章节「{chapter_title}」生成一个思维导图结构。章节简介：{chapter_summary}\n\n要求：用 Markdown 多级列表的格式表示节点层级关系，从中心主题向外辐射，覆盖所有核心知识点和子知识点。",
    }
    prompt = type_prompts.get(resource_type, f"请为章节「{chapter_title}」生成{resource_type}类型的教学资源。章节简介：{chapter_summary}")
    return generate_answer(provider, prompt)