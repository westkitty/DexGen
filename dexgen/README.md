# DexGen Setup Instructions

This guide provides instructions for deploying the local MacBook Orchestrator and the remote Google Colab Render Node for the DexGen Distributed Pipeline.

## Repository Map

```
dexgen/
├── remote/
│   ├── DexGen_RemoteNode.ipynb   # Unified server + model loader for Colab
│   └── server.py                 # Extracted FastAPI logic
├── local/
│   ├── orchestrator.py           # Gradio UI & Polling logic
│   └── requirements.txt          # local deps (gradio, requests)
├── shared/
│   ├── api_contract.md           # Restatement of Section 5
│   └── prompt_templates.md       # Starsilk consistency bibles
└── README.md                     # Runbook and install steps
```

## Setup: Remote Render Node (Google Colab T4)

1. Navigate to `dexgen/remote/`.
2. Upload `DexGen_RemoteNode.ipynb` to Google Colab.
3. In the Colab menu, go to **Runtime > Change runtime type** and ensure the hardware accelerator is set to **T4 GPU**.
4. Run all cells in the notebook.
   - The notebook will install dependencies, mount Google Drive (optional), set up `cloudflared`, and launch the FastAPI server.
5. In the notebook output, look for a URL ending in `.trycloudflare.com`. This is your **Bridge URL**. Copy it.

## Setup: Local Orchestrator (MacBook Air M1)

1. Open your terminal on your MacBook.
2. Navigate to the `dexgen/local/` directory:
   ```bash
   cd dexgen/local
   ```
3. Install the required local dependencies. It is recommended to use a virtual environment:
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   ```
4. Start the Orchestrator UI:
   ```bash
   python orchestrator.py
   ```
5. Open your web browser and navigate to the local Gradio address (usually `http://127.0.0.1:7860`).

### Connecting the UI to the Remote Node

1. In the Gradio UI header, paste the **Bridge URL** (`https://<random_string>.trycloudflare.com`) acquired from the Colab notebook.
2. Enter your **API Key** (by default, `starsilk_remote_auth_key`, unless changed in `server.py`).
3. Set the **Local Storage Path**. By default, it looks for `/Volumes/ExternalSSD/Starsilk_Renders`. If you do not have an external SSD connected, change this to a local path on your Mac before generating images.

## Storage and Usage

* All finished jobs are directly downloaded to the Local Storage Path.
* Each generation produces a media file (`.png` or `.mp4`) and a companion `.json` file containing the prompt, seed, and job metadata.
* Use the **Starsilk Library** tab in the UI to view completed generations.
