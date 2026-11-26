"""Disposable parser process with CPU/memory/time bounds, not a full OS sandbox."""
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path


def extract_isolated(filename, data, timeout=25):
    from app.services.rag.ingestion import EXTENSIONS, MAX_BYTES, Extracted
    suffix = Path(filename).suffix.lower()
    if suffix not in EXTENSIONS or not data or len(data) > MAX_BYTES:
        raise ValueError("Unsupported file type or file exceeds 5 MiB")
    environment = {key: os.environ[key] for key in ("SYSTEMROOT", "WINDIR", "TEMP", "TMP") if key in os.environ}
    job = None
    with tempfile.TemporaryDirectory(prefix="cs-parser-") as directory, tempfile.TemporaryFile() as output:
        process = subprocess.Popen([sys.executable, "-I", str(Path(__file__).resolve()), suffix],
            stdin=subprocess.PIPE, stdout=output, stderr=subprocess.DEVNULL, cwd=directory, env=environment,
            creationflags=(0x08000000 | 0x00000004) if os.name == "nt" else 0)
        try:
            if os.name == "nt":
                job = windows_job(process)
            process.communicate(input=data, timeout=timeout)
            if process.returncode:
                raise ValueError("Document extraction failed or exceeded resource limits")
            if output.seek(0, 2) > 6_100_000:
                raise ValueError("Extracted document exceeds output limits")
            output.seek(0)
            result = json.loads(output.read().decode("utf-8"))
            return Extracted(result["digest"], tuple(result["pages"]), suffix)
        except (subprocess.TimeoutExpired, OSError, json.JSONDecodeError, KeyError) as exc:
            raise ValueError("Document extraction failed or exceeded resource limits") from exc
        finally:
            if process.poll() is None:
                process.kill()
                process.wait(timeout=5)
            if job is not None:
                import ctypes
                close = ctypes.WinDLL("kernel32").CloseHandle
                close.argtypes = [ctypes.c_void_p]
                close(job)


def windows_job(process):
    import ctypes
    from ctypes import wintypes as w

    class Basic(ctypes.Structure):
        _fields_ = [("process_time", ctypes.c_int64), ("job_time", ctypes.c_int64), ("flags", w.DWORD),
                    ("min_working", ctypes.c_size_t), ("max_working", ctypes.c_size_t), ("active", w.DWORD),
                    ("affinity", ctypes.c_size_t), ("priority", w.DWORD), ("scheduling", w.DWORD)]

    class IO(ctypes.Structure):
        _fields_ = [(name, ctypes.c_uint64) for name in ("read_ops", "write_ops", "other_ops", "read_bytes", "write_bytes", "other_bytes")]

    class Extended(ctypes.Structure):
        _fields_ = [("basic", Basic), ("io", IO), ("process_memory", ctypes.c_size_t),
                    ("job_memory", ctypes.c_size_t), ("peak_process", ctypes.c_size_t), ("peak_job", ctypes.c_size_t)]

    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel.CreateJobObjectW.restype = w.HANDLE
    kernel.SetInformationJobObject.argtypes = [w.HANDLE, ctypes.c_int, ctypes.c_void_p, w.DWORD]
    kernel.AssignProcessToJobObject.argtypes = [w.HANDLE, w.HANDLE]
    kernel.CloseHandle.argtypes = [w.HANDLE]
    handle = kernel.CreateJobObjectW(None, None)
    limits = Extended()
    limits.basic.flags = 0x2000 | 0x100 | 0x200 | 0x2 | 0x8
    limits.basic.process_time = 20 * 10_000_000
    # Windows venv python.exe is a launcher that starts the actual interpreter.
    limits.basic.active = 2
    limits.process_memory = 256 * 1024 * 1024
    limits.job_memory = 384 * 1024 * 1024
    if not handle or not kernel.SetInformationJobObject(handle, 9, ctypes.byref(limits), ctypes.sizeof(limits)) or not kernel.AssignProcessToJobObject(handle, int(process._handle)):
        if handle:
            kernel.CloseHandle(handle)
        raise OSError("Parser resource containment unavailable")
    # Process was created suspended: bounds apply before parser imports any file.
    resume = ctypes.WinDLL("ntdll").NtResumeProcess
    resume.argtypes = [w.HANDLE]
    if resume(int(process._handle)) != 0:
        kernel.CloseHandle(handle)
        raise OSError("Parser could not start")
    return handle


def worker_main():
    if os.name != "nt":
        import resource
        resource.setrlimit(resource.RLIMIT_AS, (256 * 1024 * 1024,) * 2)
        resource.setrlimit(resource.RLIMIT_CPU, (20, 20))
        resource.setrlimit(resource.RLIMIT_FSIZE, (6_100_000,) * 2)
    sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
    from app.services.rag.ingestion import extract, MAX_BYTES
    data = sys.stdin.buffer.read(MAX_BYTES + 1)
    result = extract("document" + sys.argv[1], data)
    sys.stdout.buffer.write(json.dumps({"digest": result.digest, "pages": result.pages}, ensure_ascii=False).encode("utf-8"))


if __name__ == "__main__":
    worker_main()
