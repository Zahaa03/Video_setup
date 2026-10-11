#!/usr/bin/env python3
# One-time macOS setup for the video queue launcher.
# Run with: python3 video_setup.py
# Existing files that would be replaced are backed up first.

from __future__ import annotations
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path

PROJECT_DIR = Path.home() / "Desktop" / "Python_test"
LAUNCHER_PATH = PROJECT_DIR / "video_launcher.py"
DOWNLOADER_PATH = PROJECT_DIR / "video_converter_cli.py"
QUEUE_PATH = PROJECT_DIR / "urls.txt"
ZSHRC_PATH = Path.home() / ".zshrc"
ALIAS_LINE = """alias downloader='cd "$HOME/Desktop/Python_test" && python3 "$HOME/Desktop/Python_test/video_launcher.py"'"""
MARKER = "# >>> video_setup.py downloader alias >>>"

LAUNCHER_SOURCE = r"""
#!/usr/bin/env python3
import shlex
import subprocess
import sys
import tkinter as tk
from tkinter import messagebox
from pathlib import Path
from urllib.parse import urlparse, parse_qs

BASE_DIR = Path(__file__).resolve().parent
DOWNLOADER = BASE_DIR / "video_converter_cli.py"
URLS_FILE = BASE_DIR / "urls.txt"


def extract_urls(text):
    return [part.strip() for part in text.replace(",", "\n").splitlines() if part.strip()]


def valid_youtube_url(url):
    try:
        parsed = urlparse(url)
        host = (parsed.hostname or "").lower()
        if host == "youtu.be":
            return bool(parsed.path.strip("/"))
        if host in ("youtube.com", "www.youtube.com", "m.youtube.com"):
            if parsed.path == "/watch":
                return bool(parse_qs(parsed.query).get("v"))
            return parsed.path.startswith(("/shorts/", "/live/", "/embed/"))
        return False
    except ValueError:
        return False


def view_queue():
    win = tk.Toplevel(root)
    win.title("View Download Queue")
    win.geometry("650x420")
    tk.Label(win, text="Saved URLs", font=("Arial", 15, "bold")).pack(pady=10)
    box = tk.Text(win, wrap="word", font=("Arial", 11))
    box.pack(fill="both", expand=True, padx=12, pady=8)
    if URLS_FILE.exists():
        contents = URLS_FILE.read_text(encoding="utf-8").strip()
        box.insert("1.0", contents or "Your queue is empty.")
    else:
        box.insert("1.0", "No queue file exists yet.")
    box.config(state="disabled")
    tk.Button(win, text="Close", command=win.destroy).pack(pady=10)


def launch_download():
    if not DOWNLOADER.is_file():
        messagebox.showerror("Downloader not found", f"Could not find:\n{DOWNLOADER}")
        return
    urls = extract_urls(url_box.get("1.0", tk.END))
    if not urls:
        messagebox.showwarning("No URLs", "Paste one or more YouTube URLs first.")
        return
    invalid = [url for url in urls if not valid_youtube_url(url)]
    if invalid:
        messagebox.showerror("Check your URLs", "These don't look like YouTube video URLs:\n\n" + "\n".join(invalid))
        return
    try:
        URLS_FILE.write_text("\n".join(urls) + "\n", encoding="utf-8")
        python_path = sys.executable
        command = (
            f"cd {shlex.quote(str(BASE_DIR))} && "
            f"{shlex.quote(python_path)} {shlex.quote(str(DOWNLOADER))} "
            f"--queue-file {shlex.quote(str(URLS_FILE))} "
            f"--quality {shlex.quote(quality_var.get())}"
        )
        escaped = command.replace("\\", "\\\\").replace('"', '\\"')
        applescript = (
            'tell application "Terminal"\n'
            '    activate\n'
            f'    do script "{escaped}"\n'
            'end tell'
        )
        subprocess.run(["osascript", "-e", applescript], check=True)
        url_box.delete("1.0", tk.END)
        messagebox.showinfo("Download started", f"Saved {len(urls)} URL(s) to urls.txt.\nTerminal has opened.")
    except Exception as exc:
        messagebox.showerror("Could not start download", str(exc))


root = tk.Tk()
root.title("Video Download Queue")
root.geometry("700x500")
root.minsize(520, 390)
tk.Label(root, text="Video Download Queue", font=("Arial", 18, "bold")).pack(pady=(18, 5))
tk.Label(root, text="Paste YouTube URLs separated by commas or new lines:").pack(pady=5)
url_box = tk.Text(root, height=10, wrap="word", font=("Arial", 11))
url_box.pack(fill="both", expand=True, padx=18, pady=8)
quality_frame = tk.Frame(root)
quality_frame.pack(pady=8)
tk.Label(quality_frame, text="Maximum quality:").pack(side="left", padx=5)
quality_var = tk.StringVar(value="720p")
tk.OptionMenu(quality_frame, quality_var, "360p", "480p", "720p", "1080p", "1440p", "2160p").pack(side="left")
buttons = tk.Frame(root)
buttons.pack(pady=12)
tk.Button(buttons, text="Save URLs & Start Download", command=launch_download,
          font=("Arial", 11, "bold"), padx=12, pady=8).pack(side="left", padx=5)
tk.Button(buttons, text="View Queue", command=view_queue,
          font=("Arial", 11), padx=16, pady=8).pack(side="left", padx=5)
tk.Label(root, text=f"Queue file: {URLS_FILE}", font=("Arial", 9)).pack(pady=(0, 12))
root.mainloop()
"""

DOWNLOADER_SOURCE = r"""
#!/usr/bin/env python3
from __future__ import annotations
import argparse
import shutil
import sys
from pathlib import Path
import yt_dlp

DEFAULT_DOWNLOAD_DIR = Path.home() / "Desktop" / "Video_Downloads"


def parse_args():
    parser = argparse.ArgumentParser(description="Download media you are authorized to save using yt-dlp and FFmpeg.")
    parser.add_argument("urls", nargs="*", help="One or more video URLs")
    parser.add_argument("--quality", default="2160p", choices=["2160p", "1440p", "1080p", "720p", "480p", "360p"])
    parser.add_argument("--output", default="%(title)s.%(ext)s")
    parser.add_argument("--download-dir", default=str(DEFAULT_DOWNLOAD_DIR))
    parser.add_argument("--temp-dir", default=str(Path.home() / ".tmp_video_downloads"))
    parser.add_argument("--queue-file", help="Text file containing one URL per line")
    parser.add_argument("--no-playlist", action="store_true", help="Download only one video if URL points to a playlist")
    return parser.parse_args()


def progress_hook(status):
    state = status.get("status")
    if state == "downloading":
        downloaded = status.get("downloaded_bytes", 0)
        total = status.get("total_bytes") or status.get("total_bytes_estimate") or 0
        speed = status.get("speed") or 0
        if total:
            print(f"\rDownloading: {downloaded / total * 100:6.2f}% | {downloaded / 1048576:8.2f} MiB / {total / 1048576:8.2f} MiB | {speed / 1048576:6.2f} MiB/s", end="", flush=True)
        else:
            print(f"\rDownloading: {downloaded / 1048576:8.2f} MiB | {speed / 1048576:6.2f} MiB/s", end="", flush=True)
    elif state == "finished":
        print("\nDownload finished; processing...")


def build_queue(args):
    queue = list(args.urls)
    if args.queue_file:
        path = Path(args.queue_file).expanduser()
        if not path.is_file():
            raise FileNotFoundError(f"Queue file not found: {path}")
        queue.extend(line.strip() for line in path.read_text(encoding="utf-8").splitlines()
                     if line.strip() and not line.lstrip().startswith("#"))
    if not queue:
        raise ValueError("No URLs provided. Use URL arguments or --queue-file.")
    return queue


def main():
    args = parse_args()
    if shutil.which("ffmpeg") is None:
        print("Error: ffmpeg was not found in PATH. Install it, then try again.", file=sys.stderr)
        return 1
    try:
        queue = build_queue(args)
        download_dir = Path(args.download_dir).expanduser()
        download_dir.mkdir(parents=True, exist_ok=True)
        temp_dir = Path(args.temp_dir).expanduser()
        temp_dir.mkdir(parents=True, exist_ok=True)
        height = int(args.quality.rstrip("p"))
        output = Path(args.output)
        outtmpl = str((download_dir / output.name).with_suffix(".%(ext)s")) if output.suffix.lower() == ".mp4" else str(download_dir / args.output)
        options = {
            "format": f"bestvideo[height<={height}]+bestaudio/best[height<={height}]/best",
            "outtmpl": outtmpl,
            "merge_output_format": "mp4",
            "noplaylist": args.no_playlist,
            "continuedl": True,
            "retries": 10,
            "fragment_retries": 10,
            "concurrent_fragment_downloads": 4,
            "paths": {"temp": str(temp_dir), "home": str(download_dir)},
            "progress_hooks": [progress_hook],
            "quiet": True,
            "no_warnings": False,
        }
        failures = 0
        with yt_dlp.YoutubeDL(options) as ydl:
            for index, url in enumerate(queue, start=1):
                print(f"\nQueue {index}/{len(queue)}: {url}")
                try:
                    info = ydl.extract_info(url, download=True)
                    if info is None:
                        failures += 1
                        print("No media information returned.", file=sys.stderr)
                    else:
                        print(f"Saved: {info.get('title', '(unknown title)')}")
                except Exception as exc:
                    failures += 1
                    print(f"Failed: {url} -> {exc}", file=sys.stderr)
        if failures:
            print(f"Finished with {failures} failure(s).", file=sys.stderr)
            return 1
        print(f"\nAll done. Files saved in: {download_dir}")
        return 0
    except KeyboardInterrupt:
        print("\nCancelled by user.", file=sys.stderr)
        return 130
    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
"""


def backup_if_needed(path: Path) -> None:
    if path.exists():
        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        backup = path.with_name(f"{path.name}.backup-{timestamp}")
        shutil.copy2(path, backup)
        print(f"Backed up existing {path.name} to {backup}")


def write_file(path: Path, content: str, executable: bool = False) -> None:
    backup_if_needed(path)
    path.write_text(content.lstrip(), encoding="utf-8")
    if executable:
        path.chmod(path.stat().st_mode | 0o111)
    print(f"Created: {path}")


def configure_zsh_alias() -> None:
    existing = ZSHRC_PATH.read_text(encoding="utf-8") if ZSHRC_PATH.exists() else ""
    if "alias downloader=" in existing:
        print(f"An alias named 'downloader' already exists in {ZSHRC_PATH}; left unchanged.")
        print("If needed, edit ~/.zshrc manually to update the alias.")
        return
    if ZSHRC_PATH.exists():
        backup_if_needed(ZSHRC_PATH)
    with ZSHRC_PATH.open("a", encoding="utf-8") as handle:
        handle.write("\n\n" + MARKER + "\n" + ALIAS_LINE + "\n# <<< video_setup.py downloader alias <<<\n")
    print(f"Added downloader alias to {ZSHRC_PATH}")


def main() -> int:
    print("Setting up your video queue tools on macOS...")
    PROJECT_DIR.mkdir(parents=True, exist_ok=True)
    write_file(LAUNCHER_PATH, LAUNCHER_SOURCE, executable=True)
    write_file(DOWNLOADER_PATH, DOWNLOADER_SOURCE, executable=True)
    if not QUEUE_PATH.exists():
        QUEUE_PATH.write_text("# Paste one authorized video URL per line, or use the launcher.\n", encoding="utf-8")
        print(f"Created: {QUEUE_PATH}")
    else:
        print(f"Keeping existing queue file: {QUEUE_PATH}")

    print("\nInstalling/updating yt-dlp for this Python interpreter...")
    result = subprocess.run([sys.executable, "-m", "pip", "install", "-U", "yt-dlp"])
    if result.returncode != 0:
        print("\nyt-dlp installation failed. Try manually:")
        print(f'  "{sys.executable}" -m pip install -U yt-dlp')
        return result.returncode

    if shutil.which("ffmpeg") is None:
        print("\nFFmpeg was not found.")
        if shutil.which("brew"):
            print("Install it with: brew install ffmpeg")
        else:
            print("Install Homebrew from https://brew.sh, then run: brew install ffmpeg")
    else:
        print(f"\nFFmpeg found: {shutil.which('ffmpeg')}")

    configure_zsh_alias()
    print("\nSetup complete. Open a NEW Terminal window and type: downloader")
    print(f"Project folder: {PROJECT_DIR}")
    print("Downloads will be saved to ~/Desktop/Video_Downloads.")
    print("Only download media you own or are authorized to save.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
