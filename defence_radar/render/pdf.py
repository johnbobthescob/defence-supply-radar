"""Optional PDF/PNG rendering through a locally installed headless Chrome. Never raises if Chrome is missing."""
import shutil
import subprocess
from pathlib import Path


def find_chrome():
    for name in ("google-chrome", "chromium", "chromium-browser"):
        found = shutil.which(name)
        if found: return found
    p = Path("/opt/google/chrome/chrome")
    return str(p) if p.is_file() else None


def _run(args, timeout=60):
    chrome = find_chrome()
    if not chrome: return False
    try:
        done = subprocess.run([chrome, "--headless=new", "--disable-gpu", "--no-sandbox", *args], capture_output=True, timeout=timeout)
    except (OSError, subprocess.SubprocessError):
        return False
    return done.returncode == 0


def html_to_pdf(html_path, pdf_path):
    html_path, pdf_path = Path(html_path).resolve(), Path(pdf_path).resolve()
    ok = _run(["--no-pdf-header-footer", f"--print-to-pdf={pdf_path}", html_path.as_uri()])
    return bool(ok and pdf_path.is_file() and pdf_path.stat().st_size > 0)


def screenshot(html_path, png_path, width=1200, height=2400):
    html_path, png_path = Path(html_path).resolve(), Path(png_path).resolve()
    ok = _run([f"--screenshot={png_path}", f"--window-size={width},{height}", "--hide-scrollbars", html_path.as_uri()])
    return bool(ok and png_path.is_file() and png_path.stat().st_size > 0)
