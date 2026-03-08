# DexGen Project Bible — As-Built v1.0 (Truth Source: Reality Check Report)

## 1. Executive Summary
DexGen is a distributed generative pipeline designed to decouple heavy inference workloads from local orchestration. 
* **Remote Render Node:** A Google Colab instance utilizing an NVIDIA graphics processing unit (GPU) for high-performance model execution.
* **Local Orchestration:** A macOS Gradio-based application (the application programming interface (API) client) that manages user input, security, and automated backend discovery.
* **Bridge Mechanism:** Uses a Google Drive rendezvous system to synchronize the backend uniform resource locator (URL) and health status with the local client.

## 2. Architecture Overview
The system follows a "decoupled bridge" architecture. Instead of persistent static IPs, the backend establishes a secure tunnel and writes its dynamic coordinates to a shared cloud storage layer.

**Core Workflow:**
1. **Rendezvous:** Backend starts, establishes a Cloudflare tunnel (cloudflared), and writes the public URL and status to Google Drive.
2. **Discovery:** macOS client uses `rclone` to read the rendezvous files and identifies the active backend.
3. **Authentication:** Client retrieves the `DEXGEN_API_KEY` from the macOS Keychain.
4. **Execution:** Secure requests are sent to the backend with the required `X-API-Key` header.
5. **Output:** Generated assets are saved directly to Google Drive paths, which are then synced or downloaded out-of-band.

## 3. Component Specs

### 3.1 Colab Backend (FastAPI)
The backend is a FastAPI server running in a Google Colab notebook environment. It handles synchronous generation requests for images and videos.

**Current Endpoints:**
* **GET `/` (Health):** Returns backend status and available models.
* **POST `/generate` (Image):** Synchronous image generation.
    * **Request Schema:**
      ```json
      {
        "model": "sd15" | "flux_schnell",
        "prompt": "string",
        "negative_prompt": "string | null",
        "steps": 30,
        "width": 512,
        "height": 512,
        "seed": 0,
        "guidance_scale": 7.5
      }
      ```
* **POST `/generate_video` (Video):** Synchronous video generation.
    * **Request Schema:**
      ```json
      {
        "model": "i2vgen_xl" | "svd",
        "prompt": "string",
        "image_path": "/content/drive/MyDrive/DexGen/inputs/source.png",
        "steps": 30,
        "frames": 16,
        "fps": 8,
        "seed": 0,
        "guidance_scale": 7.5
      }
      ```

### 3.2 ModelManager
The `ModelManager` class handles sequential model loading into video random access memory (VRAM) and provides an explicit cleanup strategy.

**As-Built Model Configurations:**
* **sd15 (Stable Diffusion 1.5):** Loads `runwayml/stable-diffusion-v1-5` using `torch.float16` and `safetensors`.
* **flux_schnell (FLUX.1-schnell):** Loads `black-forest-labs/FLUX.1-schnell` using `torch.float16` with CPU offloading enabled via `enable_model_cpu_offload()`.
* **i2vgen_xl (I2VGen-XL):** Loads `ali-vilab/i2vgen-xl` using `torch.float16` and `variant="fp16"`, with CPU offloading enabled.
* **svd (Stable Video Diffusion img2vid-xt):** Loads `stabilityai/stable-video-diffusion-img2vid-xt` using `torch.float16` and `variant="fp16"`, with CPU offloading enabled.

**VRAM Strategy:**
The backend utilizes an `inference_lock` to ensure only one model is active at a time. Every job is followed by explicit `gc.collect()` and `torch.cuda.empty_cache()` calls.

### 3.3 Cloudflare Tunnel (cloudflared)
The backend URL is established via `cloudflared`. The URL is captured from the process output using a regular expression and written to the rendezvous file:
* **Capture Command:** `cloudflared tunnel --url http://127.0.0.1:8000`
* **Writing Logic:** The URL is persisted to `/content/drive/MyDrive/DexGen/current_url.txt`.

### 3.4 Google Drive Layout
The following directories and files are required for proper operation:
* `/content/drive/MyDrive/DexGen/`
    * `current_url.txt`: Contains the current tunnel URL.
    * `status.json`: Contains the health status, starts time, and last error.
        * **Schema:** `{"ok": bool, "base_url": string, "started_at": integer, "last_error": string}`
    * `secrets.json`: Expected to contain `{"DEXGEN_API_KEY": "..."}`.
    * `inputs/`: Input images for video generation.
    * `outputs/`: Destination for all generated portable network graphics (PNG) and moving picture experts group-4 (MPEG-4) files.

### 3.5 macOS Client (Gradio)
The client interface is built with Gradio and handles auto-discovery.

* **Discovery Logic:**
  - `rclone cat gdrive:DexGen/current_url.txt`
  - `rclone cat gdrive:DexGen/status.json`
* **Security:** Loads the API key from the macOS Keychain:
  - `security find-generic-password -a $USER -s DEXGEN_API_KEY -w`
* **Timeouts:**
  - Connection timeout: 5 seconds
  - Image read timeout: 120 seconds
  - Video read timeout: 300 seconds
* **Network:** Binds to `0.0.0.0:7860` for local and network-level access (e.g., via Tailscale).

## 4. Operational Runbook

### 4.1 First-time Setup
1. **Backend:** Ensure `secrets.json` exists in `MyDrive/DexGen/` with a valid `DEXGEN_API_KEY`.
2. **Client:** Run the following in terminal to store the key:
   ```bash
   security add-generic-password -a $USER -s DEXGEN_API_KEY -w 'YOUR_API_KEY'
   ```
3. **rclone:** Configure `rclone` with a remote named `gdrive` pointing to the correct Google Drive account.

### 4.2 Start Backend
1. Open `DexGen_Final_Colab.ipynb` in Google Colab.
2. Run all cells.
3. Wait for the `SERVER IS READY` banner.

### 4.3 Start Client
1. Execute the macOS app or `app.py`.
2. The UI will automatically populate the "Base URL" and "Backend Status" fields upon startup or clicking "Refresh Backend".

### 4.4 Generation
* **Image:** Select `sd15` or `flux_schnell`, enter a prompt, and click "Generate Image".
* **Video:** Upload an image to the `inputs/` folder on Drive, provide the path in the UI, select `i2vgen_xl` or `svd`, and click "Generate Video".

## 5. Troubleshooting
* **Backend Status "Error":** Check the `last_error` field in `status.json` via GDrive or the client UI. Usually indicates VRAM exhaustion or `secrets.json` missing.
* **"Bad API Key":** Ensure the key in Keychain matches the key in `/content/drive/MyDrive/DexGen/secrets.json`.
* **"Backend Unreachable":** Verify the Cloudflare tunnel process is still running in the Colab notebook.

## 6. File Ledger
* `DexGen_Final_Colab.ipynb`: Authoritative backend source.
* `DexGenApp/app.py`: Authoritative client source.
* `DexGen Project Bible.md`: This document.

## 7. Planned / Target v1.1+ (NOT implemented)
* **Job Queue & Polling:** Transition from synchronous requests to an asynchronous job system with status polling.
* **Streaming Download Endpoints:** Direct download for local storage without relying on Google Drive replication.
* **4-bit NF4 Quantization:** Integration of `bitsandbytes` `4bit` loading for high-resolution stability if needed.

## 8. Changelog
* **Rev 1.0 (2026-02-28):** 
    - Corrected API endpoints to match synchronous implementation (`/generate`, `/generate_video`).
    - Updated security model to reflect macOS Keychain and GDrive `secrets.json` integration.
    - Documented as-built model loading strategies (fp16/bf16 with CPU offload).
    - Removed outdated references to `/v1` routing and async job polling.
    - Added explicit GDrive rendezvous file schemas (`status.json`, `current_url.txt`).
    - Documented `rclone`-based client discovery logic.
