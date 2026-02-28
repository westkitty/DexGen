# DexGen API Contract

This document outlines the Bridge Protocol between the local Orchestrator and the remote Render Node.

**Base Path:** `/v1`
**Authentication:** All requests must include the `X-API-Key` header with the configured API key.

## System Endpoints

### `GET /v1/health`
Returns the status of the remote node.
**Response:**
```json
{
  "status": "online",
  "gpu": "Tesla T4" 
}
```

### `GET /v1/stats`
Returns system uptime and VRAM statistics.
**Response:**
```json
{
  "uptime_seconds": 3600,
  "vram_total_mb": 15109,
  "vram_used_mb": 8500,
  "vram_free_mb": 6609
}
```

## Job Endpoints

### `POST /v1/generate` (Text-to-Image)
Submits a new Flux image generation job.
**Request Body (JSON):**
```json
{
  "prompt": "A cel-shaded small black-and-white dog standing in a heroic pose, flat colors.",
  "character_lock": "A cel-shaded small black-and-white dog, floppy ears down, human-like eyes, thick clean outlines, flat colors, consistent facial markings, no breed morphing.",
  "style_preset": "Cel-shaded",
  "negative_prompt": "blurry, distorted, low quality, gradient backgrounds, realistic textures, 3D render, over-detailed, inconsistent line weight.",
  "seed": 42,
  "width": 1024,
  "height": 1024,
  "steps": 4,
  "save_to_drive": false
}
```
**Response:**
```json
{
  "job_id": "job_1234567890",
  "status": "queued"
}
```

### `POST /v1/animate` (Image-to-Video)
Submits a new Image-to-Video animation job.
**Request (Multipart Form Data):**
- `file`: The input image (PNG/JPG).
- `prompt`: (String) Text prompt for motion guidance.
- `fps`: (Integer, optional) Frames per second. Defaults to 7.
- `num_frames`: (Integer, optional) Number of frames. Defaults to 14.
- `motion_strength`: (Integer, optional) Motion strength. Defaults to 127.

**Response:**
```json
{
  "job_id": "job_0987654321",
  "status": "queued"
}
```

### `GET /v1/jobs/{job_id}`
Polls the current status of a job.
**Response:**
```json
{
  "job_id": "job_1234567890",
  "kind": "generate", 
  "status": "done",
  "progress": 1.0,
  "result_filename": "output_1234567890.png"
}
```
*`kind` is either "generate" or "animate".*
*`status` can be: "queued", "running", "done", "error".*

### `GET /v1/jobs/{job_id}/download`
Downloads the resulting file.
**Response:** Streams the binary file content (`image/png` or `video/mp4`).
