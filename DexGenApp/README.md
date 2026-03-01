# DexGen Client (Google Drive Rendezvous)

This application serves as the frontend client for the DexGen generative application. It automatically connects to your Colab backend by discovering the URL through Google Drive.

## Architecture (Option A)

This app uses **Google Drive Rendezvous** to communicate with the Colab backend:
1. **Google Colab:**
   You run a specific notebook (`DexGen_Colab_OneCell.ipynb`). It launches the FastAPI backend, opens a free Cloudflare Quick Tunnel, and writes the resulting public URL to your Google Drive (`MyDrive/DexGen/current_url.txt`).
2. **Mac Client (This app):**
   The application uses `rclone` to constantly check your `gdrive:` remote for the active URL. 
   You never have to copy-paste URLs. Just click "Run" in Colab, wait for it to start, and double-click the DexGen app on your Mac.

## One-Time Setup

For this to work seamlessly, you must complete these three steps on your Mac:

### 1. Configure Rclone
The app relies on `rclone` to read the GDrive synchronization files.
1. Install rclone: `brew install rclone`
2. Run `rclone config`
3. Create a new remote exactly named: `gdrive`
4. Select `drive` (Google Drive) as the storage type.
5. Follow the browser prompts to authorize it.

### 2. Save your API Key in the macOS Keychain
To prevent copy-pasting API keys, the app securely reads it from your macOS Keychain.
Run this command in your terminal exactly as written (replacing `YOUR_SECRET_KEY` with your actual DexGen API Key):
```bash
security add-generic-password -a $USER -s DEXGEN_API_KEY -w 'YOUR_SECRET_KEY'
```

### 3. Place Secrets in Google Drive
The Colab backend needs to know what API key to expect.
Create a file named `secrets.json` and upload it to `MyDrive/DexGen/secrets.json`:
```json
{
  "DEXGEN_API_KEY": "YOUR_SECRET_KEY"
}
```

## Daily Usage

1. Open Google Colab and run the **`DexGen_Colab_OneCell.ipynb`** cell.
2. Wait until the cell prints `✅ Published URL and Status to Google Drive`.
3. Double-click **`DexGen App.app`** on your Mac.
4. The app will state **"Connected"** and display your URL automatically.

## Troubleshooting
* **Backend Not Started:** The app cannot find the URL file in GDrive. Ensure Colab is running, completed its setup sequence, and that rclone is authenticated properly as `gdrive`.
* **Bad API Key:** The key stored in your Mac keychain does not match the key you put loosely in your Colab `secrets.json`. Ensure they match exactly.
* **Missing API Key:** Run the `security add-generic-password` command above.

## Developer Instructions (Rebuilding)
To package this app into an executable macOS `.app` bundle:
```bash
./build.sh
```
The resulting executable will be generated at `dist/DexGen App.app`.
