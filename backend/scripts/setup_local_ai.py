"""Download pinned official CPU runtime/model into this workspace; no OS install."""
import hashlib
import argparse
import argparse
import json
import urllib.request
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1] / ".local-ai"
ARTIFACTS = [
    ("llama-b12559-bin-win-cpu-x64.zip", "https://github.com/ggml-org/llama.cpp/releases/download/b12559/llama-b12559-bin-win-cpu-x64.zip",
     "2f3dcb3aea4f52bf734f52040d2a688bdd76c2f762ae200a159646b37d84e393"),
    ("qwen2.5-1.5b-instruct-q4_k_m.gguf", "https://huggingface.co/Qwen/Qwen2.5-1.5B-Instruct-GGUF/resolve/91cad51170dc346986eccefdc2dd33a9da36ead9/qwen2.5-1.5b-instruct-q4_k_m.gguf",
     "6a1a2eb6d15622bf3c96857206351ba97e1af16c30d7a74ee38970e434e9407e"),
]


def digest(path):
    with path.open("rb") as source:
        return hashlib.file_digest(source, "sha256").hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--verify-only", action="store_true")
    args = parser.parse_args()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--verify-only", action="store_true")
    args = parser.parse_args()
    ROOT.mkdir(exist_ok=True)
    for name, url, expected in ARTIFACTS:
        target = ROOT / name
        if target.exists() and digest(target) == expected:
            print(f"Verified existing {name}", flush=True)
            continue
        if args.verify_only:
            raise SystemExit("Local AI artifacts missing or invalid. Run scripts/setup_local_ai.py explicitly first.")
        if args.verify_only:
            raise SystemExit("Local AI artifacts missing or invalid. Run scripts/setup_local_ai.py explicitly first.")
        partial = ROOT / (name + ".partial")
        request = urllib.request.Request(url, headers={"User-Agent": "CS-IRCFS-local-assistant-setup"})
        print(f"Downloading official artifact: {name}", flush=True)
        with urllib.request.urlopen(request, timeout=60) as response, partial.open("wb") as output:
            written, milestone = 0, 0
            while chunk := response.read(1024 * 1024):
                output.write(chunk)
                written += len(chunk)
                if written // (100 * 1024 * 1024) > milestone:
                    milestone = written // (100 * 1024 * 1024)
                    print(f"{name}: {written // (1024 * 1024)} MiB", flush=True)
        if digest(partial) != expected:
            raise SystemExit("Checksum mismatch; artifact will not be executed or loaded")
        # Atomic replacement only inside the workspace-owned artifact directory.
        partial.replace(target)
        print(f"SHA-256 verified: {name}", flush=True)
    binary = ROOT / "bin"
    binary.mkdir(exist_ok=True)
    with zipfile.ZipFile(ROOT / ARTIFACTS[0][0]) as archive:
        if sum(entry.file_size for entry in archive.infolist()) > 500 * 1024 * 1024:
            raise SystemExit("Runtime archive exceeds extraction bound")
        for entry in archive.infolist():
            if not (binary / entry.filename).resolve().is_relative_to(binary.resolve()):
                raise SystemExit("Unsafe runtime archive path")
        archive.extractall(binary)
    manifest = {"runtime": "llama.cpp b12559 CPU", "model": "Qwen2.5-1.5B-Instruct Q4_K_M",
                "sources": [{"name": name, "url": url, "sha256": sha} for name, url, sha in ARTIFACTS]}
    (ROOT / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print("Verified local AI files ready. No system installation or paid API used.", flush=True)


if __name__ == "__main__":
    main()
