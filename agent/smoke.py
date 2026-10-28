"""Smoke test server LLM: 1 câu tiếng Việt -> spec JSON; in thời gian và token/giây.

  set -a; . ./.env; set +a; DATAMATE_LLM_BASE_URL=https://.../v1 python -m agent.smoke
"""
import json
import time

from .llm import LLM, load_config
from .prompt import messages
from .spec import json_schema, parse_spec


def main():
    cfg = load_config()
    llm = LLM(cfg)
    msgs = messages("dthu tháng 3/2026 tăng hay giảm bao nhiêu % so với tháng trước?", "2026-04-10",
                    "- Dữ liệu từ 2025-01-01 đến 2026-04-30", [])
    for label, schema in (("tự do (không ép schema)", None), ("structured output (json_schema)", json_schema())):
        t0 = time.time()
        c = llm.complete(msgs, schema)
        dt = time.time() - t0
        spec, err = parse_spec(c.text) if c.text else (None, c.error)
        print(f"== {label}: {dt:.2f}s, prompt {c.prompt_tokens} tok, completion {c.completion_tokens} tok, "
              f"{c.completion_tokens / max(c.seconds, 1e-9):.1f} tok/s (gồm prefill)")
        print("   raw:", (c.text or c.error or "")[:300])
        print("   spec:", json.dumps(spec.model_dump(exclude_none=True), ensure_ascii=False) if spec else f"LỖI {err}")


if __name__ == "__main__":
    main()
