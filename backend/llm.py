"""Provider-agnostic LLM client (no SDKs — plain HTTPS).

Configure in backend/.env:
    LLM_PROVIDER=gemini | openai | anthropic | azure_openai
    LLM_API_KEY=...
    LLM_MODEL=...            (optional; sensible default per provider)
    LLM_BASE_URL=...         (optional; for Azure OpenAI or an internal gateway)

If LLM_API_KEY is empty the assistant runs on the deterministic matcher alone.
"""
import json
import os
import urllib.request

PROVIDER = (os.getenv("LLM_PROVIDER") or "gemini").strip().lower()
API_KEY = os.getenv("LLM_API_KEY", "").strip()
BASE_URL = os.getenv("LLM_BASE_URL", "").rstrip("/")
DEFAULT_MODELS = {
    "gemini": "gemini-2.5-flash",
    "openai": "gpt-4o-mini",
    "azure_openai": "gpt-4o-mini",
    "anthropic": "claude-sonnet-5",
}
MODEL = os.getenv("LLM_MODEL", "").strip() or DEFAULT_MODELS.get(PROVIDER, "")
LABELS = {"gemini": "Gemini", "openai": "OpenAI", "azure_openai": "Azure OpenAI", "anthropic": "Claude"}


def enabled() -> bool:
    return bool(API_KEY) and PROVIDER in DEFAULT_MODELS


def label() -> str | None:
    return LABELS.get(PROVIDER) if enabled() else None


def _post(url: str, headers: dict, body: dict) -> dict:
    req = urllib.request.Request(url, data=json.dumps(body).encode(), method="POST",
                                 headers={"Content-Type": "application/json", **headers})
    with urllib.request.urlopen(req, timeout=30) as res:
        return json.load(res)


def complete(system: str, messages: list[dict]) -> str:
    """messages: [{"role": "user"|"assistant", "content": str}]. Returns the model's text."""
    if PROVIDER == "gemini":
        base = BASE_URL or "https://generativelanguage.googleapis.com/v1beta"
        data = _post(
            f"{base}/models/{MODEL}:generateContent",
            {"x-goog-api-key": API_KEY},
            {
                "systemInstruction": {"parts": [{"text": system}]},
                "contents": [{"role": "model" if m["role"] == "assistant" else "user",
                              "parts": [{"text": m["content"]}]} for m in messages],
                "generationConfig": {"temperature": 0.2, "responseMimeType": "application/json"},
            },
        )
        return data["candidates"][0]["content"]["parts"][0]["text"]

    if PROVIDER in ("openai", "azure_openai"):
        if PROVIDER == "azure_openai":
            # LLM_BASE_URL = https://<resource>.openai.azure.com/openai/deployments/<deployment>
            url, headers = f"{BASE_URL}/chat/completions?api-version=2024-06-01", {"api-key": API_KEY}
        else:
            url, headers = f"{BASE_URL or 'https://api.openai.com/v1'}/chat/completions", {"Authorization": f"Bearer {API_KEY}"}
        data = _post(url, headers, {
            "model": MODEL, "temperature": 0.2, "response_format": {"type": "json_object"},
            "messages": [{"role": "system", "content": system}, *messages],
        })
        return data["choices"][0]["message"]["content"]

    if PROVIDER == "anthropic":
        data = _post(
            f"{BASE_URL or 'https://api.anthropic.com'}/v1/messages",
            {"x-api-key": API_KEY, "anthropic-version": "2023-06-01"},
            {"model": MODEL, "max_tokens": 1024, "system": system, "messages": messages},
        )
        return "".join(b.get("text", "") for b in data["content"] if b.get("type") == "text")

    raise ValueError(f"Unsupported LLM_PROVIDER '{PROVIDER}'")


def complete_json(system: str, messages: list[dict]) -> dict:
    text = complete(system, messages).strip()
    if text.startswith("```"):
        text = text.strip("`").removeprefix("json").strip()
    start, end = text.find("{"), text.rfind("}")
    return json.loads(text[start:end + 1])
