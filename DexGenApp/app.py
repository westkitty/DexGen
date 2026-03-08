import gradio as gr
import requests
import os
import json
import time
import subprocess
import getpass
from datetime import datetime

CONNECT_TIMEOUT = 5
READ_TIMEOUT_IMAGE = 120
READ_TIMEOUT_VIDEO = 300

# --- Auto Discovery via Rclone ---

def get_rclone_data(path, is_json=False):
    """Silently fetches data from GDrive using rclone."""
    try:
        result = subprocess.run(
            ["rclone", "cat", f"gdrive:DexGen/{path}"],
            capture_output=True, text=True, check=True
        )
        content = result.stdout.strip()
        if is_json:
            return json.loads(content)
        return content
    except subprocess.CalledProcessError:
        return None
    except json.JSONDecodeError:
        return None
    except FileNotFoundError:
        # rclone not installed or not in PATH
        return None

def fetch_backend_info():
    """Returns (status_text, base_url, last_updated_str)"""
    # 1. Read URL
    base_url = get_rclone_data("current_url.txt", is_json=False)
    
    # 2. Read Status
    status_data = get_rclone_data("status.json", is_json=True)
    
    if not base_url or not status_data:
        return "Not Running (Press Run in Colab)", "", "Unknown"
        
    is_ok = status_data.get("ok", False)
    started_at = status_data.get("started_at")
    
    if not is_ok:
        err = status_data.get("last_error", "Unknown Error")
        return f"Error: {err}", base_url, "Unknown"
        
    last_updated = "Unknown"
    if started_at:
        try:
            # Convert epoch to local time string
            dt = datetime.fromtimestamp(int(started_at))
            last_updated = dt.strftime("%Y-%m-%d %H:%M:%S")
        except:
            pass
            
    return "Connected", base_url, last_updated

# --- Keychain API Auth ---

def load_api_key_from_keychain():
    user = os.environ.get("USER") or getpass.getuser()
    try:
        result = subprocess.run(
            ["security", "find-generic-password", "-a", user, "-s", "DEXGEN_API_KEY", "-w"],
            capture_output=True, text=True, check=True
        )
        return result.stdout.strip()
    except subprocess.CalledProcessError:
        return None
    except FileNotFoundError:
        return None

# --- Core Business Logic ---

def coerce_int(value, default):
    try:
        if value in (None, ""):
            return default
        return int(value)
    except (TypeError, ValueError):
        return default


def coerce_float(value, default):
    try:
        if value in (None, ""):
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def do_refresh():
    status, url, updated = fetch_backend_info()
    return status, url, updated, ""

def test_connection_func(base_url):
    status_text, current_url, updated_time = fetch_backend_info()
    
    if not current_url:
         return status_text, current_url, updated_time, json.dumps({
            "error": "Backend not started",
            "details": "Press Run in Colab first. URL file missing from GDrive."
        }, indent=2)

    api_key = load_api_key_from_keychain()
    if not api_key:
        return status_text, current_url, updated_time, json.dumps({
            "error": "Missing API Key",
            "details": "Run exactly this in terminal:\nsecurity add-generic-password -a $USER -s DEXGEN_API_KEY -w 'YOUR_API_KEY'"
        }, indent=2)

    url = f"{current_url.rstrip('/')}/auth_check"
    headers = {"X-API-Key": api_key}
    
    start_time = time.time()
    try:
        response = requests.get(url, headers=headers, timeout=(CONNECT_TIMEOUT, READ_TIMEOUT_IMAGE))
        latency = (time.time() - start_time) * 1000
        
        if response.status_code == 401:
            return status_text, current_url, updated_time, "Bad API key"

        if not response.ok:
            return status_text, current_url, updated_time, json.dumps({"status": response.status_code, "body": response.text, "latency_ms": round(latency, 2)}, indent=2)
            
        return "Connected", current_url, updated_time, json.dumps({"status": "Success", "latency_ms": round(latency, 2), "response": response.json()}, indent=2)

    except (requests.exceptions.ReadTimeout, requests.exceptions.ConnectionError):
        return "Backend not started or unreachable", current_url, updated_time, "Backend not started or unreachable"
    except Exception as e:
        return "Error", current_url, updated_time, json.dumps({"error": "Unexpected Error", "details": str(e)}, indent=2)

def generate_image_func(model, prompt, negative_prompt, steps, width, height, seed, guidance_scale):
    status_text, current_url, updated_time = fetch_backend_info()
    
    if not current_url:
        return status_text, current_url, updated_time, json.dumps({"error": "Backend not started", "details": "Press Run in Colab first."}, indent=2), ""
        
    api_key = load_api_key_from_keychain()
    if not api_key:
        return status_text, current_url, updated_time, json.dumps({"error": "Missing API Key"}, indent=2), ""

    url = f"{current_url.rstrip('/')}/generate"
    headers = {"Content-Type": "application/json", "X-API-Key": api_key}
    payload = {
        "model": model,
        "prompt": prompt,
        "negative_prompt": negative_prompt or None,
        "steps": coerce_int(steps, 30),
        "width": coerce_int(width, 512),
        "height": coerce_int(height, 512),
        "seed": coerce_int(seed, 0),
        "guidance_scale": coerce_float(guidance_scale, 7.5)
    }

    try:
        response = requests.post(url, json=payload, headers=headers, timeout=(CONNECT_TIMEOUT, READ_TIMEOUT_IMAGE))
        
        if response.status_code == 401:
            return status_text, current_url, updated_time, "Bad API key", ""
            
        if not response.ok:
            return status_text, current_url, updated_time, json.dumps({"status": response.status_code, "body": response.text}, indent=2), ""
            
        json_resp = response.json()
        saved_to = json_resp.get("saved_to", "")
        return status_text, current_url, updated_time, json.dumps(json_resp, indent=2), saved_to

    except (requests.exceptions.ReadTimeout, requests.exceptions.ConnectionError):
        return "Backend not started or unreachable", current_url, updated_time, "Backend not started or unreachable", ""
    except Exception as e:
        return "Error", current_url, updated_time, json.dumps({"error": "Unexpected Error", "details": str(e)}, indent=2), ""


def generate_video_func(model, prompt, negative_prompt, image_path, steps, frames, fps, seed, guidance_scale):
    status_text, current_url, updated_time = fetch_backend_info()
    
    if not current_url:
        return status_text, current_url, updated_time, json.dumps({"error": "Backend not started", "details": "Press Run in Colab first."}, indent=2), ""
        
    api_key = load_api_key_from_keychain()
    if not api_key:
        return status_text, current_url, updated_time, json.dumps({"error": "Missing API Key"}, indent=2), ""

    url = f"{current_url.rstrip('/')}/generate_video"
    headers = {"Content-Type": "application/json", "X-API-Key": api_key}
    payload = {
        "model": model,
        "prompt": prompt,
        "negative_prompt": negative_prompt or None,
        "image_path": (image_path or "").strip(),
        "steps": coerce_int(steps, 25),
        "frames": coerce_int(frames, 16),
        "fps": coerce_int(fps, 8),
        "seed": coerce_int(seed, 0),
        "guidance_scale": coerce_float(guidance_scale, 7.5)
    }

    try:
        response = requests.post(url, json=payload, headers=headers, timeout=(CONNECT_TIMEOUT, READ_TIMEOUT_VIDEO))
        
        if response.status_code == 401:
            return status_text, current_url, updated_time, "Bad API key", ""
            
        if not response.ok:
            return status_text, current_url, updated_time, json.dumps({"status": response.status_code, "body": response.text}, indent=2), ""
            
        json_resp = response.json()
        saved_to = json_resp.get("saved_to", "")
        return status_text, current_url, updated_time, json.dumps(json_resp, indent=2), saved_to

    except (requests.exceptions.ReadTimeout, requests.exceptions.ConnectionError):
        return "Backend not started or unreachable", current_url, updated_time, "Backend not started or unreachable", ""
    except Exception as e:
        return "Error", current_url, updated_time, json.dumps({"error": "Unexpected Error", "details": str(e)}, indent=2), ""


# --- Gradio UI Layout ---

initial_status, initial_url, initial_updated = fetch_backend_info()

with gr.Blocks(title="DexGen Client") as demo:
    gr.Markdown("# DexGen Client")
    
    with gr.Row(variant="panel"):
        status_disp = gr.Textbox(label="Backend Status", value=initial_status, interactive=False, scale=1)
        url_disp = gr.Textbox(label="Base URL", value=initial_url, interactive=False, scale=2)
        updated_disp = gr.Textbox(label="Last Updated", value=initial_updated, interactive=False, scale=1)
        refresh_btn = gr.Button("Refresh Backend", variant="secondary", scale=1)

    with gr.Tabs():
        with gr.TabItem("Image"):
            with gr.Row():
                with gr.Column(scale=2):
                    model_image = gr.Dropdown(choices=["sd15", "flux_schnell"], value="sd15", label="Model")
                    prompt_image = gr.Textbox(label="Prompt", lines=3, placeholder="Enter your prompt...")
                    neg_prompt_image = gr.Textbox(label="Negative Prompt", lines=2, placeholder="Optional...")
                    with gr.Row():
                        steps_image = gr.Number(label="Steps", value=30, precision=0)
                        width_image = gr.Number(label="Width", value=512, precision=0)
                        height_image = gr.Number(label="Height", value=512, precision=0)
                    with gr.Row():
                        seed_image = gr.Number(label="Seed", value=0, precision=0)
                        guideline_image = gr.Number(label="Guidance Scale", value=7.5)
                    
                    with gr.Row():
                        test_img_btn = gr.Button("Test Connection", variant="secondary")
                        generate_img_btn = gr.Button("Generate Image", variant="primary")
                    
                with gr.Column(scale=1):
                    res_img = gr.Code(label="Response", language="json", interactive=False, lines=12)
                    save_img = gr.Textbox(label="Saved Path", interactive=False)

        with gr.TabItem("Video"):
            with gr.Row():
                with gr.Column(scale=2):
                    model_video = gr.Dropdown(choices=["i2vgen_xl", "svd"], value="i2vgen_xl", label="Model")
                    prompt_video = gr.Textbox(label="Prompt", lines=3, placeholder="Enter your prompt...")
                    neg_prompt_video = gr.Textbox(label="Negative Prompt", lines=2, placeholder="Optional...")
                    image_path_video = gr.Textbox(label="Drive Image Path", placeholder="/content/drive/MyDrive/DexGen/inputs/source.png")
                    with gr.Row():
                        steps_video = gr.Number(label="Steps", value=30, precision=0)
                        frames_video = gr.Number(label="Frames", value=16, precision=0)
                        fps_video = gr.Number(label="FPS", value=8, precision=0)
                    with gr.Row():
                        seed_video = gr.Number(label="Seed", value=0, precision=0)
                        guideline_video = gr.Number(label="Guidance Scale", value=7.5)
                    
                    with gr.Row():
                        test_vid_btn = gr.Button("Test Connection", variant="secondary")
                        generate_vid_btn = gr.Button("Generate Video", variant="primary")
                    
                with gr.Column(scale=1):
                    res_vid = gr.Code(label="Response", language="json", interactive=False, lines=12)
                    save_vid = gr.Textbox(label="Saved Path", interactive=False)

    # Wire up events
    def do_refresh():
        status, url, updated = fetch_backend_info()
        return status, url, updated, "", ""
        
    def wrapped_test_connection(url):
        status, url, updated, resp = test_connection_func(url)
        return status, url, updated, resp, ""

    refresh_outputs = [status_disp, url_disp, updated_disp, res_img, save_img]
    
    refresh_btn.click(fn=do_refresh, inputs=[], outputs=refresh_outputs)
    
    test_img_btn.click(
        fn=wrapped_test_connection, 
        inputs=[url_disp],
        outputs=refresh_outputs
    )
    test_vid_btn.click(
        fn=wrapped_test_connection, 
        inputs=[url_disp],
        outputs=[status_disp, url_disp, updated_disp, res_vid, save_vid]
    )
    
    generate_img_btn.click(
        fn=generate_image_func,
        inputs=[model_image, prompt_image, neg_prompt_image, steps_image, width_image, height_image, seed_image, guideline_image],
        outputs=[status_disp, url_disp, updated_disp, res_img, save_img],
        api_name=False
    )

    generate_vid_btn.click(
        fn=generate_video_func,
        inputs=[model_video, prompt_video, neg_prompt_video, image_path_video, steps_video, frames_video, fps_video, seed_video, guideline_video],
        outputs=[status_disp, url_disp, updated_disp, res_vid, save_vid],
        api_name=False
    )

if __name__ == "__main__":
    print("Binding to 0.0.0.0 for Tailscale tailnet access...")
    print("Local access: http://127.0.0.1:7860")
    demo.launch(
        server_name="0.0.0.0",
        server_port=7860,
        inbrowser=True,
        prevent_thread_lock=False,
        theme=gr.themes.Default(),
    )
