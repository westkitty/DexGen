# DexGen: Running the Project

This guide provides a concise, step-by-step process for running the **DexGen Distributed Pipeline**, which connects a remote Google Colab GPU node to a local macOS Gradio client.

## 1. Prerequisites (macOS Client)

- **Python 3.10+** (Recommended)
- **rclone**: Configured with a remote named `gdrive` pointing to your Google Drive.
- **DEXGEN_API_KEY**: Stored in your macOS Keychain. Run the following once (using the default key below or your own):
  ```bash
  security add-generic-password -a $USER -s DEXGEN_API_KEY -w 'starsilk_remote_auth_key'
  ```
  *Note: `starsilk_remote_auth_key` is the default key used by the backend if none is provided.*

---

## 2. Start the Remote Render Node (Google Colab)

1. Open `DexGen_Final_Colab.ipynb` in Google Colab.
2. Ensure you are using a **T4 GPU** runtime (**Runtime > Change runtime type**).
3. Run all cells (**Cmd/Ctrl + F9**).
   - *Note: The notebook will automatically mount Google Drive and create a `secrets.json` file with the default key if it doesn't already exist.*
4. Wait for the large **🚀 SERVER IS READY** message at the bottom.

---

## 3. Start the Local Orchestrator (macOS)

1. Open your terminal and navigate to the `DexGenApp` directory:
   ```bash
   cd DexGenApp
   ```
2. Create and activate a virtual environment:
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   ```
3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
4. Launch the application:
   ```bash
   python app.py
   ```
5. The UI will automatically open in your browser (default: `http://127.0.0.1:7860`).

---

## 4. Usage Workflow

1. **Discovery:** Upon launch, the app uses `rclone` to fetch the current backend URL and health status from Google Drive.
2. **Refresh:** If the backend was started after the client, click the **"Refresh Backend"** button in the UI.
3. **Generate:**
   - **Image:** Enter a prompt in the "Image" tab and click **"Generate Image"**.
   - **Video:** Ensure your source image is in `MyDrive/DexGen/inputs/`, enter its path, and click **"Generate Video"**.
4. **Output:** All generated assets are saved to `MyDrive/DexGen/outputs/` on Google Drive.
