from __future__ import annotations

from typing import Callable

import httpx
import requests
from openai import OpenAI

try:
    from openai import APIConnectionError, APITimeoutError
except ImportError:  # pragma: no cover
    APIConnectionError = APITimeoutError = Exception

from app.config import AISettings


SECTION_MARKER = "# <<SECTION_BREAK>>"

SYSTEM_PROMPT = (
    "你是一个专业的 manim 动画工程师，负责生成连续的动画场景。\n"
    "请输出可运行的 Python 代码，用 manim 生成一个 Scene\n"
    "要求：\n"
    "1) 代码必须包含: from manim import *\n"
    "2) 必须定义且只定义一个 Scene 子类\n"
    "3) 不要输出任何解释文字，只输出代码\n"
    "4) 代码必须可直接运行，且不包含任何语法错误\n"
    "5) 续写时请在新增动画代码前插入一行标记："
    f"{SECTION_MARKER}，不要写 self.next_section()\n"
    "5.1) 续写时只输出新增片段代码，不要重复输出已有代码或类定义\n"
    "6) 每段动画控制在1-3秒以内\n"
    "7) 动画要保持场景连续性，不要使用 FadeOut 清空画面\n"
    "8) 保证动画结束时场景可见居中"
)


class AIError(RuntimeError):
    pass


def generate_manim_code(
    settings: AISettings,
    mode: str,
    prompt: str,
    previous_code: str,
    debug: Callable[[str], None] | None = None,
    timeout: int = 60,
) -> tuple[str, str]:
    name, provider = _resolve_provider(mode)
    try:
        code = provider(settings, prompt, previous_code, debug, timeout)
        return name, code
    except Exception as exc:  # noqa: BLE001
        if debug:
            debug(f"AI {name} 调用失败：{exc}")
        raise AIError(f"AI {name} 接口调用失败: {exc}") from exc


def _resolve_provider(
    mode: str,
) -> tuple[str, Callable[[AISettings, str, str, Callable[[str], None] | None, int], str]]:
    if mode == "deepseek":
        return "deepseek", _call_deepseek
    if mode == "gemini":
        return "gemini", _call_gemini
    raise AIError("未指定有效的 AI 模式")


def _call_deepseek(
    settings: AISettings,
    prompt: str,
    previous_code: str,
    debug: Callable[[str], None] | None,
    timeout: int,
) -> str:
    if not settings.deepseek_api_key:
        raise AIError("DeepSeek API Key 未配置")
    base = settings.deepseek_base_url.strip().rstrip("/")
    if not base.startswith("http://") and not base.startswith("https://"):
        base = f"https://{base}"
    base_url = f"{base}/v1"
    url = f"{base_url}/chat/completions"
    if debug:
        debug(f"DeepSeek 请求：{url} | model={settings.deepseek_model}")
    if debug:
        debug(f"DeepSeek 请求已发送，超时 {timeout}s")
    timeout_config = httpx.Timeout(float(timeout))
    transport = httpx.HTTPTransport(retries=3)
    with httpx.Client(
        timeout=timeout_config,
        transport=transport,
        follow_redirects=True,
    ) as http_client:
        client = OpenAI(
            api_key=settings.deepseek_api_key,
            base_url=base_url,
            timeout=timeout_config,
            max_retries=2,
            http_client=http_client,
        )
        try:
            response = client.chat.completions.create(
                model=settings.deepseek_model,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": build_prompt(prompt, previous_code)},
                ],
                temperature=0.2,
            )
        except (APIConnectionError, APITimeoutError) as exc:
            raise AIError(
                "DeepSeek 连接失败，请检查网络/代理设置或 base_url 是否可达"
            ) from exc
        except httpx.HTTPError as exc:
            raise AIError(
                "DeepSeek 连接失败，请检查网络/代理设置或 base_url 是否可达"
            ) from exc
    content = response.choices[0].message.content
    if not content:
        raise AIError("DeepSeek 返回内容为空")
    if debug:
        debug("DeepSeek 返回成功")
    return content


def _call_gemini(
    settings: AISettings,
    prompt: str,
    previous_code: str,
    debug: Callable[[str], None] | None,
    timeout: int,
) -> str:
    if not settings.gemini_api_key:
        raise AIError("Gemini API Key 未配置")
    url = (
        "https://generativelanguage.googleapis.com/v1beta/models/"
        f"{settings.gemini_model}:generateContent"
    )
    if debug:
        debug(f"Gemini 请求：{url} | model={settings.gemini_model}")
    params = {"key": settings.gemini_api_key}
    payload = {
        "contents": [
            {
                "role": "user",
                "parts": [{"text": f"{SYSTEM_PROMPT}\n{build_prompt(prompt, previous_code)}"}],
            }
        ],
        "generationConfig": {"temperature": 0.2},
    }
    if debug:
        debug(f"Gemini 请求已发送，超时 {timeout}s")
    response = requests.post(
        url,
        params=params,
        json=payload,
        timeout=timeout,
    )
    response.raise_for_status()
    data = response.json()
    candidates = data.get("candidates", [])
    if not candidates:
        raise AIError("Gemini 返回为空")
    parts = candidates[0].get("content", {}).get("parts", [])
    text_parts = [part.get("text", "") for part in parts]
    content = "\n".join(text_parts).strip()
    if not content:
        raise AIError("Gemini 返回内容为空")
    if debug:
        debug("Gemini 返回成功")
    return content


def sanitize_code(code: str, previous_code: str = "") -> str:
    """清理和验证 AI 生成的代码"""
    cleaned = _strip_code_fences(code).strip()
    
    if previous_code.strip():
        # 追加模式：移除开头的 import 语句
        lines = cleaned.splitlines()
        while lines and (lines[0].startswith("from ") or lines[0].startswith("import ")):
            lines.pop(0)
        return "\n".join(lines).strip()

    # 新建模式：确保有 manim 导入
    if "from manim import" not in cleaned:
        cleaned = "from manim import *\n\n" + cleaned
    
    return cleaned + "\n"


def build_prompt(prompt: str, previous_code: str) -> str:
    """构建发送给 AI 的完整提示词"""
    if previous_code.strip():
        return (
            f"以下是当前场景的完整代码：\n\n"
            f"```python\n{previous_code.strip()}\n```\n\n"
            f"需求：{prompt}\n\n"
            f"请在 `construct` 方法的末尾续写代码以实现上述需求。\n"
            f"严格遵守以下规则：\n"
            f"1. 仅返回新增的代码片段，不要重复已有代码\n"
            f"2. 新增代码必须以 `{SECTION_MARKER}` 开头\n"
            f"3. 不要包含 `class` 定义或 `def construct`\n"
            f"4. 保持变量名和场景状态的连贯性\n"
            f"5. 不要使用 `self.next_section()`，使用标记代替"
        )
    
    return f"创建一个新的 manim 场景来实现：{prompt}（不要包含 {SECTION_MARKER} 或 self.next_section()）"


def ensure_section_addition(existing_code: str, ai_response: str, current_prompt: str) -> str:
    """确保 AI 响应正确添加了新分段"""
    cleaned = _strip_code_fences(ai_response).strip()

    if not existing_code.strip():
        return _strip_markers_and_sections(cleaned)

    # 处理包含 SECTION_MARKER 的响应
    if SECTION_MARKER in cleaned:
        parts = cleaned.split(SECTION_MARKER, 1)
        if len(parts) > 1:
            cleaned = _remove_common_indent(parts[1])

    # 找到 construct 方法中的插入位置
    lines = existing_code.split('\n')
    insert_pos = _find_construct_insert_position(lines)
                 
    # 添加新分段
    new_section_lines = [
        "",
        "        # 新分段",
        f"        {SECTION_MARKER}",
        "",
    ]

    # 添加 AI 生成的代码（确保正确缩进）
    for line in (cleaned.split('\n') if cleaned else []):
        if line.strip():
            new_section_lines.append(f"        {line}" if not line.startswith('        ') else line)
        else:
            new_section_lines.append("")

    lines[insert_pos:insert_pos] = new_section_lines
    return _replace_section_marker('\n'.join(lines))


def _remove_common_indent(code: str) -> str:
    """移除代码块的公共缩进"""
    lines = [line for line in code.splitlines() if line.strip()]
    if not lines:
        return ""
    
    # 找到最小缩进
    min_indent = min(len(line) - len(line.lstrip()) for line in lines if line.strip())
    return "\n".join(line[min_indent:] if len(line) > min_indent else line for line in lines).strip()


def _find_construct_insert_position(lines: list[str]) -> int:
    """找到 construct 方法中最后一行代码的位置"""
    found_construct = False
    last_indented_line = -1
    
    for i, line in enumerate(lines):
        if "def construct(self):" in line:
            found_construct = True
        # 找到 construct 方法内的最后一行有效代码
        if found_construct and (line.startswith("    ") or line.startswith("\t")) and line.strip():
            last_indented_line = i
    
    if last_indented_line != -1:
        return last_indented_line + 1
    
    # 如果找不到，返回 construct 定义的下一行
    for i, line in enumerate(lines):
        if "def construct(self):" in line:
            return i + 1
    
    return len(lines)


def _strip_markers_and_sections(code: str) -> str:
    """首轮：移除标记与 self.next_section()，确保只生成一个分段"""
    cleaned_lines: list[str] = []
    for line in code.split('\n'):
        stripped = line.strip()
        if SECTION_MARKER in line:
            continue
        if "self.next_section()" in stripped:
            continue
        cleaned_lines.append(line)
    return "\n".join(cleaned_lines).strip() + "\n"


def _replace_section_marker(code: str) -> str:
    """将标记替换为 self.next_section()，并确保仅保留一个标记"""
    lines = code.split('\n')
    marker_indices = [i for i, line in enumerate(lines) if SECTION_MARKER in line]
    
    if not marker_indices:
        return code
    
    # 替换第一个标记
    first_idx = marker_indices[0]
    indent = lines[first_idx][:len(lines[first_idx]) - len(lines[first_idx].lstrip())]
    lines[first_idx] = f"{indent}self.next_section()"
    
    # 删除其他标记
    for idx in reversed(marker_indices[1:]):
        lines.pop(idx)
    
    return "\n".join(lines)


def _strip_code_fences(code: str) -> str:
    stripped = code.strip()
    if stripped.startswith("```"):
        lines = stripped.splitlines()
        if lines:
            lines = lines[1:]
        if lines and lines[-1].strip().startswith("```"):
            lines = lines[:-1]
        return "\n".join(lines)
    return code


