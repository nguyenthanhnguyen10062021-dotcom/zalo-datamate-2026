"""Client OpenAI-compatible (vLLM). Dev trỏ Modal, lúc thi trỏ vLLM local: chỉ đổi base_url qua biến môi trường.

Dùng structured output (response_format json_schema -> guided decoding của vLLM) để luôn ra JSON đúng schema.
"""
from __future__ import annotations

import os
import time
from dataclasses import dataclass
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]


def load_config(path: str | Path = ROOT / "config" / "model.yaml") -> dict:
    cfg = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    cfg["model"] = cfg["models"][os.environ.get("DATAMATE_MODEL", cfg["active"])]
    return cfg


@dataclass
class Completion:
    text: str | None
    prompt_tokens: int = 0
    completion_tokens: int = 0
    seconds: float = 0.0
    error: str | None = None


class LLM:
    def __init__(self, cfg: dict):
        from openai import OpenAI
        c = cfg["client"]
        self.cfg, self.model = cfg, cfg["model"]
        self.retries = c.get("retries", 1)
        self.client = OpenAI(base_url=os.environ.get(c["base_url_env"], c["default_base_url"]),
                             api_key=os.environ.get(c["api_key_env"], "EMPTY"),
                             timeout=c.get("timeout_s", 90), max_retries=0)

    def complete(self, messages: list[dict], schema: dict | None = None, temperature: float | None = None,
                 seed: int | None = None) -> Completion:
        s = self.cfg["sampling"]
        kwargs = dict(model=self.model["id"], messages=messages, max_tokens=s["max_tokens"],
                      temperature=s["temperature"] if temperature is None else temperature,
                      seed=s["seed"] if seed is None else seed,
                      extra_body={"chat_template_kwargs": self.model.get("chat_template_kwargs", {})})
        if schema is not None:
            kwargs["response_format"] = {"type": "json_schema",
                                         "json_schema": {"name": "spec", "schema": schema, "strict": True}}
        error = None
        for _ in range(1 + self.retries):
            t0 = time.time()
            try:
                r = self.client.chat.completions.create(**kwargs)
                u = r.usage
                return Completion(r.choices[0].message.content, u.prompt_tokens if u else 0,
                                  u.completion_tokens if u else 0, time.time() - t0)
            except Exception as e:  # noqa: BLE001  (mạng/timeout/server): thử lại 1 lần rồi bỏ
                error = f"{type(e).__name__}: {str(e)[:200]}"
        return Completion(None, error=error)
