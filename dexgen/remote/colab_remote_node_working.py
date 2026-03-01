#!/usr/bin/env python3
"""
DexGen Colab Remote Node (FastAPI + Cloudflare tunnel).

This backend matches the local DexGen client contract:
- Writes public URL to: /content/drive/MyDrive/DexGen/current_url.txt
- Writes health/status to: /content/drive/MyDrive/DexGen/status.json
- Serves:
    GET  /
    POST /generate
    POST /generate_video
"""

from __future__ import annotations

import gc
import json
import os
import re
import secrets as py_secrets
import subprocess
import threading
import time
from typing import Any, Dict, Optional

import imageio
import nest_asyncio
import numpy as np
import torch
import uvicorn
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from PIL import Image

try:
    from google.colab import drive  # type: ignore
except Exception as exc:
    raise RuntimeError("This script is meant to run in Google Colab.") from exc


ROOT = "/content/drive/MyDrive/DexGen"
STATUS_FILE = f"{ROOT}/status.json"
URL_FILE = f"{ROOT}/current_url.txt"
SECRETS_FILE = f"{ROOT}/secrets.json"
DEFAULT_KEY = "starsilk_remote_auth_key"


def mount_and_prepare() -> None:
    print("Mounting Google Drive...")
    drive.mount("/content/drive", force_remount=True)
    os.makedirs(f"{ROOT}/inputs", exist_ok=True)
    os.makedirs(f"{ROOT}/outputs", exist_ok=True)
    print(f"Workspace ready at {ROOT}")


def load_api_key() -> str:
    if not os.path.exists(SECRETS_FILE):
        with open(SECRETS_FILE, "w", encoding="utf-8") as f:
            json.dump({"DEXGEN_API_KEY": DEFAULT_KEY}, f)
    with open(SECRETS_FILE, "r", encoding="utf-8") as f:
        raw = json.load(f)
    key = raw.get("DEXGEN_API_KEY", DEFAULT_KEY)
    print(f"API key loaded: {key[:4]}****")
    return key


GLOBAL_STATUS: Dict[str, Any] = {
    "ok": False,
    "base_url": None,
    "started_at": int(time.time()),
    "last_error": "Initializing",
}


def write_status(ok: bool, error: Optional[str] = None, base_url: Optional[str] = None) -> None:
    GLOBAL_STATUS["ok"] = ok
    if error is not None:
        GLOBAL_STATUS["last_error"] = error
    if base_url is not None:
        GLOBAL_STATUS["base_url"] = base_url
    with open(STATUS_FILE, "w", encoding="utf-8") as f:
        json.dump(GLOBAL_STATUS, f)


active_pipeline = None
active_model_id = None
inference_lock = threading.Lock()
APP = FastAPI(title="DexGen Remote Node", version="1.0.2")
API_KEY = ""


class ModelManager:
    @staticmethod
    def cleanup() -> None:
        global active_pipeline, active_model_id
        if active_pipeline is not None:
            del active_pipeline
            active_pipeline = None
            active_model_id = None
        gc.collect()
        if torch.cuda.is_available():
            torch.cuda.empty_cache()

    @staticmethod
    def load(model_id: str):
        global active_pipeline, active_model_id
        if not torch.cuda.is_available():
            raise RuntimeError("CUDA not available. Use a T4/A100 runtime in Colab.")

        if active_model_id == model_id and active_pipeline is not None:
            return active_pipeline

        ModelManager.cleanup()
        print(f"Loading model: {model_id}")

        if model_id == "sd15":
            from diffusers import StableDiffusionPipeline

            pipe = StableDiffusionPipeline.from_pretrained(
                "runwayml/stable-diffusion-v1-5",
                torch_dtype=torch.float16,
                use_safetensors=True,
            ).to("cuda")
        elif model_id == "flux_schnell":
            from diffusers import FluxPipeline

            pipe = FluxPipeline.from_pretrained(
                "black-forest-labs/FLUX.1-schnell",
                torch_dtype=torch.bfloat16,
            )
            pipe.enable_model_cpu_offload()
        elif model_id == "i2vgen_xl":
            from diffusers import I2VGenXLPipeline

            pipe = I2VGenXLPipeline.from_pretrained(
                "ali-vilab/i2vgen-xl",
                torch_dtype=torch.float16,
                variant="fp16",
            )
            pipe.enable_model_cpu_offload()
        elif model_id == "svd":
            from diffusers import StableVideoDiffusionPipeline

            pipe = StableVideoDiffusionPipeline.from_pretrained(
                "stabilityai/stable-video-diffusion-img2vid-xt",
                torch_dtype=torch.float16,
                variant="fp16",
            )
            pipe.enable_model_cpu_offload()
        else:
            raise ValueError(f"Unknown model: {model_id}")

        active_model_id = model_id
        active_pipeline = pipe
        return pipe


def write_mp4(frames, path: str, fps: int) -> None:
    writer = imageio.get_writer(path, fps=fps, codec="libx264", format="FFMPEG")
    try:
        for frame in frames:
            if isinstance(frame, Image.Image):
                writer.append_data(np.array(frame.convert("RGB")))
            else:
                writer.append_data(np.array(frame))
    finally:
        writer.close()


@APP.middleware("http")
async def verify_api_key(request: Request, call_next):
    if request.headers.get("X-API-Key") != API_KEY:
        return JSONResponse(status_code=401, content={"error": "Unauthorized"})
    return await call_next(request)


@APP.get("/")
def health():
    return {"ok": True, "version": "1.0.2", "models": ["sd15", "flux_schnell", "i2vgen_xl", "svd"]}


@APP.post("/generate")
async def generate(req: Request):
    try:
        data = await req.json()
        model_id = data.get("model", "sd15")
        seed = int(data.get("seed", 0)) or py_secrets.randbelow(2**31 - 1)
        steps = int(data.get("steps", 30))
        width = int(data.get("width", 512))
        height = int(data.get("height", 512))
        prompt = data.get("prompt", "")
        neg_prompt = data.get("negative_prompt")
        guidance_scale = float(data.get("guidance_scale", 7.5))

        with inference_lock:
            pipe = ModelManager.load(model_id)
            gen = torch.Generator("cuda").manual_seed(seed)
            if model_id == "sd15":
                out = pipe(
                    prompt=prompt,
                    negative_prompt=neg_prompt,
                    num_inference_steps=steps,
                    width=width,
                    height=height,
                    guidance_scale=guidance_scale,
                    generator=gen,
                ).images[0]
            else:
                out = pipe(
                    prompt=prompt,
                    guidance_scale=0.0,
                    num_inference_steps=steps,
                    max_sequence_length=256,
                    height=height,
                    width=width,
                    generator=gen,
                ).images[0]

        filename = f"img_{model_id}_{seed}_{int(time.time())}.png"
        output_path = f"{ROOT}/outputs/{filename}"
        out.save(output_path)
        return {"saved_to": output_path, "seed": seed}
    except Exception as exc:
        write_status(False, error=str(exc))
        return JSONResponse(status_code=500, content={"error": str(exc)})


@APP.post("/generate_video")
async def generate_video(req: Request):
    try:
        data = await req.json()
        model_id = data.get("model", "i2vgen_xl")
        seed = int(data.get("seed", 0)) or py_secrets.randbelow(2**31 - 1)
        steps = int(data.get("steps", 25))
        num_frames = int(data.get("frames", 16))
        fps = int(data.get("fps", 8))
        prompt = data.get("prompt", "")
        image_path = data.get("image_path")
        if not image_path or not os.path.exists(image_path):
            raise FileNotFoundError(f"Source image not found: {image_path}")

        with inference_lock:
            pipe = ModelManager.load(model_id)
            gen = torch.Generator("cuda").manual_seed(seed)
            base_img = Image.open(image_path).convert("RGB")
            if model_id == "i2vgen_xl":
                frames = pipe(
                    prompt=prompt,
                    image=base_img.resize((512, 512)),
                    num_inference_steps=steps,
                    num_frames=num_frames,
                    generator=gen,
                ).frames[0]
            else:
                # T4-safe chunk size to avoid OOM spikes during decode.
                frames = pipe(
                    image=base_img.resize((1024, 576)),
                    num_frames=num_frames,
                    num_inference_steps=steps,
                    decode_chunk_size=8,
                    generator=gen,
                ).frames[0]

        filename = f"vid_{model_id}_{seed}_{int(time.time())}.mp4"
        output_path = f"{ROOT}/outputs/{filename}"
        write_mp4(frames, output_path, fps)
        return {"saved_to": output_path, "seed": seed}
    except Exception as exc:
        write_status(False, error=str(exc))
        return JSONResponse(status_code=500, content={"error": str(exc)})


def start_uvicorn() -> threading.Thread:
    nest_asyncio.apply()
    thread = threading.Thread(
        target=lambda: uvicorn.run(APP, host="0.0.0.0", port=8000, log_level="info"),
        daemon=True,
    )
    thread.start()
    return thread


def start_tunnel() -> str:
    process = subprocess.Popen(
        ["cloudflared", "tunnel", "--url", "http://127.0.0.1:8000"],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )
    pattern = re.compile(r"(https://[a-zA-Z0-9-]+\.trycloudflare\.com)")

    for _ in range(90):
        line = process.stdout.readline() if process.stdout else ""
        if line:
            match = pattern.search(line)
            if match:
                return match.group(1)
        time.sleep(1)

    process.terminate()
    raise RuntimeError("Cloudflare tunnel did not produce a public URL in time.")


def main() -> None:
    global API_KEY
    mount_and_prepare()
    API_KEY = load_api_key()

    write_status(False, error="Starting API server")
    _ = start_uvicorn()
    time.sleep(2)

    print("Starting Cloudflare tunnel...")
    url = start_tunnel()

    with open(URL_FILE, "w", encoding="utf-8") as f:
        f.write(url)
    write_status(True, error=None, base_url=url)

    print("\n" + "=" * 40)
    print("SERVER IS READY")
    print(f"URL: {url}")
    print(f"API key prefix: {API_KEY[:4]}****")
    print("=" * 40 + "\n")

    while True:
        time.sleep(60)


if __name__ == "__main__":
    main()
