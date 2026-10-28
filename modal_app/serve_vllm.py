"""vLLM OpenAI-compatible server trên Modal (CHỈ dùng lúc dev; lúc thi chạy vLLM local trong Docker).

Chạy tạm (dừng app khi tắt lệnh):   modal serve modal_app/serve_vllm.py
Trọng số tải 1 lần vào Modal Volume `datamate-hf-cache`. API key lấy từ Modal Secret `datamate-vllm`
(biến VLLM_API_KEY); client đọc cùng key từ biến môi trường DATAMATE_LLM_API_KEY.
"""
from pathlib import Path

import modal
import yaml

CFG_PATH = Path(__file__).resolve().parents[1] / "config" / "model.yaml"   # trong container: /config/model.yaml
CFG = yaml.safe_load(CFG_PATH.read_text())
MODEL = CFG["models"][CFG["active"]]
SERVE = CFG["modal"]
PORT = 8000

image = (
    modal.Image.from_registry("nvidia/cuda:12.8.1-devel-ubuntu22.04", add_python="3.12")
    .entrypoint([])
    .uv_pip_install(f"vllm=={SERVE['vllm_version']}", "huggingface_hub[hf_transfer]", "pyyaml")
    .env({"HF_HUB_ENABLE_HF_TRANSFER": "1"})
    .add_local_file(str(CFG_PATH), "/config/model.yaml")
)
hf_cache = modal.Volume.from_name("datamate-hf-cache", create_if_missing=True)
vllm_cache = modal.Volume.from_name("datamate-vllm-cache", create_if_missing=True)
app = modal.App("datamate-vllm")


@app.function(image=image, gpu=SERVE["gpu"], scaledown_window=SERVE["scaledown_window_s"], timeout=60 * 60,
              max_containers=SERVE.get("max_containers", 1),
              volumes={"/root/.cache/huggingface": hf_cache, "/root/.cache/vllm": vllm_cache},
              secrets=[modal.Secret.from_name("datamate-vllm")])
@modal.concurrent(max_inputs=SERVE["max_concurrent_inputs"])
@modal.web_server(port=PORT, startup_timeout=20 * 60)
def serve():
    import os
    import subprocess
    print(f"[datamate] model={MODEL['id']}@{MODEL['revision'][:10]} gpu={SERVE['gpu']} "
          f"ước tính ~{SERVE['usd_per_hour']} USD/giờ GPU khi đang chạy (scale-to-zero sau "
          f"{SERVE['scaledown_window_s']}s rảnh)", flush=True)
    cmd = ["vllm", "serve", MODEL["id"], "--revision", MODEL["revision"], "--served-model-name", MODEL["id"],
           "--dtype", MODEL["dtype"], "--max-model-len", str(MODEL["max_model_len"]),
           "--host", "0.0.0.0", "--port", str(PORT), "--api-key", os.environ["VLLM_API_KEY"],
           "--generation-config", "vllm", *MODEL["serve_args"]]
    subprocess.Popen(cmd)
