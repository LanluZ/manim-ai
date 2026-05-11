from __future__ import annotations

from dataclasses import dataclass, field
from time import perf_counter
from typing import Any, Protocol

import httpx
import requests
from openai import APIConnectionError, APITimeoutError, AuthenticationError, OpenAI, RateLimitError

from src.services.config import AgentConfig, AISettings

RETRYABLE_ERROR_KINDS = {"timeout", "rate_limit", "server", "invalid_response", "unknown"}


@dataclass(frozen=True)
class ProviderRequest:
    prompt: str
    system_prompt: str = ""
    timeout: int = 60
    stream: bool = False
    max_tokens: int | None = None


@dataclass(frozen=True)
class ProviderUsage:
    input_tokens: int
    output_tokens: int


@dataclass(frozen=True)
class ProviderResponse:
    provider: str
    content: str
    usage: ProviderUsage
    estimated_cost_usd: float
    first_token_seconds: float = 0.0


@dataclass(frozen=True)
class ProviderCallRecord:
    provider: str
    success: bool
    duration_seconds: float
    attempt: int
    error_kind: str = ""
    error_message: str = ""
    input_tokens: int = 0
    output_tokens: int = 0
    output_chars: int = 0
    first_token_seconds: float = 0.0
    estimated_cost_usd: float = 0.0


@dataclass(frozen=True)
class ProviderCompletion:
    content: str
    usage: ProviderUsage | None = None
    first_token_seconds: float = 0.0


class ProviderError(RuntimeError):
    def __init__(self, provider: str, kind: str, message: str) -> None:
        super().__init__(message)
        self.provider = provider
        self.kind = kind


class AIProvider(Protocol):
    name: str

    def complete(self, request: ProviderRequest, settings: AISettings) -> ProviderCompletion:
        ...


@dataclass
class ProviderRegistry:
    _providers: dict[str, AIProvider] = field(default_factory=dict)

    def register(self, provider: AIProvider) -> None:
        self._providers[provider.name] = provider

    def get(self, name: str) -> AIProvider:
        try:
            return self._providers[name]
        except KeyError as exc:
            raise ProviderError(name, "unknown", f"Provider 未注册: {name}") from exc


class StaticProvider:
    def __init__(self, name: str, content: str, usage: ProviderUsage | None = None) -> None:
        self.name = name
        self._content = content
        self._usage = usage

    def complete(self, request: ProviderRequest, settings: AISettings) -> ProviderCompletion:
        return ProviderCompletion(content=self._content, usage=self._usage)


class FaultyProvider:
    def __init__(self, name: str, error_kind: str = "unknown", message: str = "injected failure") -> None:
        self.name = name
        self._error_kind = error_kind
        self._message = message

    def complete(self, request: ProviderRequest, settings: AISettings) -> ProviderCompletion:
        raise ProviderError(self.name, self._error_kind, self._message)


class DeepSeekProvider:
    name = "deepseek"

    def complete(self, request: ProviderRequest, settings: AISettings) -> ProviderCompletion:
        if not settings.deepseek_api_key:
            raise ProviderError(self.name, "auth", "DeepSeek API Key 未配置")

        base = settings.deepseek_base_url.strip().rstrip("/")
        if not base.startswith(("http://", "https://")):
            base = f"https://{base}"
        base_url = f"{base}/v1"
        timeout_config = httpx.Timeout(float(request.timeout))
        transport = httpx.HTTPTransport(retries=0)
        with httpx.Client(timeout=timeout_config, transport=transport, follow_redirects=True) as http_client:
            client = OpenAI(
                api_key=settings.deepseek_api_key,
                base_url=base_url,
                timeout=timeout_config,
                max_retries=0,
                http_client=http_client,
            )
            try:
                messages: Any = (
                    [{"role": "user", "content": request.prompt}]
                    if not request.system_prompt
                    else [
                        {"role": "system", "content": request.system_prompt},
                        {"role": "user", "content": request.prompt},
                    ]
                )
                kwargs: dict[str, Any] = {
                    "model": settings.deepseek_model,
                    "messages": messages,
                    "temperature": 0.2,
                }
                if request.max_tokens is not None:
                    kwargs["max_tokens"] = request.max_tokens

                if request.stream:
                    stream_started = perf_counter()
                    first_token_seconds = 0.0
                    content_parts: list[str] = []
                    reasoning_parts: list[str] = []
                    stream = client.chat.completions.create(**kwargs, stream=True)
                    for chunk in stream:
                        chunk_delta = chunk.choices[0].delta
                        content_delta = getattr(chunk_delta, "content", None)
                        reasoning_delta = getattr(chunk_delta, "reasoning_content", None)
                        delta = content_delta or reasoning_delta
                        if delta and not first_token_seconds:
                            first_token_seconds = perf_counter() - stream_started
                        if content_delta:
                            content_parts.append(content_delta)
                        elif reasoning_delta:
                            reasoning_parts.append(reasoning_delta)
                    content = "".join(content_parts) or "".join(reasoning_parts)
                    if not content:
                        raise ProviderError(self.name, "invalid_response", "DeepSeek 返回内容为空")
                    return ProviderCompletion(
                        content=content,
                        first_token_seconds=first_token_seconds,
                    )

                response = client.chat.completions.create(**kwargs)
            except AuthenticationError as exc:
                raise ProviderError(self.name, "auth", str(exc)) from exc
            except RateLimitError as exc:
                raise ProviderError(self.name, "rate_limit", str(exc)) from exc
            except APITimeoutError as exc:
                raise ProviderError(self.name, "timeout", str(exc)) from exc
            except APIConnectionError as exc:
                raise ProviderError(self.name, "server", str(exc)) from exc
            except httpx.TimeoutException as exc:
                raise ProviderError(self.name, "timeout", str(exc)) from exc
            except httpx.HTTPError as exc:
                raise ProviderError(self.name, "server", str(exc)) from exc

        content = response.choices[0].message.content
        if not content:
            raise ProviderError(self.name, "invalid_response", "DeepSeek 返回内容为空")

        usage = getattr(response, "usage", None)
        if usage is None:
            return ProviderCompletion(content=content)
        return ProviderCompletion(
            content=content,
            usage=ProviderUsage(
                input_tokens=int(getattr(usage, "prompt_tokens", 0) or 0),
                output_tokens=int(getattr(usage, "completion_tokens", 0) or 0),
            ),
        )


class GeminiProvider:
    name = "gemini"

    def complete(self, request: ProviderRequest, settings: AISettings) -> ProviderCompletion:
        if not settings.gemini_api_key:
            raise ProviderError(self.name, "auth", "Gemini API Key 未配置")

        url = (
            "https://generativelanguage.googleapis.com/v1beta/models/"
            f"{settings.gemini_model}:generateContent"
        )
        full_content = request.prompt if not request.system_prompt else f"{request.system_prompt}\n{request.prompt}"
        payload = {
            "contents": [{"role": "user", "parts": [{"text": full_content}]}],
            "generationConfig": {"temperature": 0.2},
        }
        try:
            response = requests.post(
                url,
                params={"key": settings.gemini_api_key},
                json=payload,
                timeout=request.timeout,
            )
            response.raise_for_status()
        except requests.Timeout as exc:
            raise ProviderError(self.name, "timeout", str(exc)) from exc
        except requests.HTTPError as exc:
            status = exc.response.status_code if exc.response is not None else 0
            kind = "rate_limit" if status == 429 else "auth" if status in {401, 403} else "server"
            raise ProviderError(self.name, kind, str(exc)) from exc
        except requests.RequestException as exc:
            raise ProviderError(self.name, "server", str(exc)) from exc

        data = response.json()
        candidates = data.get("candidates", [])
        if not candidates:
            raise ProviderError(self.name, "invalid_response", "Gemini 返回为空")
        parts = candidates[0].get("content", {}).get("parts", [])
        content = "\n".join(part.get("text", "") for part in parts).strip()
        if not content:
            raise ProviderError(self.name, "invalid_response", "Gemini 返回内容为空")

        usage_data = data.get("usageMetadata", {})
        usage = ProviderUsage(
            input_tokens=int(usage_data.get("promptTokenCount", 0) or 0),
            output_tokens=int(usage_data.get("candidatesTokenCount", 0) or 0),
        )
        if usage.input_tokens == 0 and usage.output_tokens == 0:
            return ProviderCompletion(content=content)
        return ProviderCompletion(content=content, usage=usage)


class ProviderRouter:
    def __init__(self, registry: ProviderRegistry | None = None, config: AgentConfig | None = None) -> None:
        self.registry = registry or default_provider_registry()
        self.config = config or AgentConfig()

    def complete(
        self,
        request: ProviderRequest,
        settings: AISettings,
        preferred_provider: str,
        records: list[ProviderCallRecord] | None = None,
    ) -> ProviderResponse:
        last_error: ProviderError | None = None
        for provider_name in self._provider_order(preferred_provider):
            provider = self.registry.get(provider_name)
            attempts = 1 + max(0, self.config.max_provider_retries)
            for attempt in range(1, attempts + 1):
                started = perf_counter()
                try:
                    completion = provider.complete(request, settings)
                    content = completion.content
                    usage = completion.usage
                    final_usage = usage or estimate_usage(request, content)
                    cost = estimate_cost(provider_name, final_usage, self.config)
                    duration = perf_counter() - started
                    record = ProviderCallRecord(
                        provider=provider_name,
                        success=True,
                        duration_seconds=duration,
                        attempt=attempt,
                        input_tokens=final_usage.input_tokens,
                        output_tokens=final_usage.output_tokens,
                        output_chars=len(content),
                        first_token_seconds=completion.first_token_seconds,
                        estimated_cost_usd=cost,
                    )
                    if records is not None:
                        records.append(record)
                    return ProviderResponse(
                        provider=provider_name,
                        content=content,
                        usage=final_usage,
                        estimated_cost_usd=cost,
                        first_token_seconds=completion.first_token_seconds,
                    )
                except ProviderError as exc:
                    duration = perf_counter() - started
                    last_error = exc
                    if records is not None:
                        records.append(
                            ProviderCallRecord(
                                provider=provider_name,
                                success=False,
                                duration_seconds=duration,
                                attempt=attempt,
                                error_kind=exc.kind,
                                error_message=str(exc),
                            )
                        )
                    if exc.kind not in RETRYABLE_ERROR_KINDS:
                        break
        if last_error is not None:
            raise last_error
        raise ProviderError(preferred_provider, "unknown", "没有可用的 Provider")

    def _provider_order(self, preferred_provider: str) -> list[str]:
        configured = list(self.config.provider_fallback_order or ())
        ordered = [preferred_provider]
        ordered.extend(name for name in configured if name != preferred_provider)
        return ordered


def estimate_usage(request: ProviderRequest, content: str) -> ProviderUsage:
    input_chars = len(request.prompt) + len(request.system_prompt)
    return ProviderUsage(
        input_tokens=max(1, input_chars // 4),
        output_tokens=max(1, len(content) // 4),
    )


def estimate_cost(provider: str, usage: ProviderUsage, config: AgentConfig) -> float:
    prices = config.provider_prices_per_1k_tokens or {}
    input_price, output_price = prices.get(provider, (0.0, 0.0))
    return (usage.input_tokens / 1000 * input_price) + (usage.output_tokens / 1000 * output_price)


def default_provider_registry() -> ProviderRegistry:
    registry = ProviderRegistry()
    registry.register(DeepSeekProvider())
    registry.register(GeminiProvider())
    return registry
