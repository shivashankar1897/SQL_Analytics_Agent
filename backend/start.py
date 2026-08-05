# start.py — Author: Suresh D R | AI Product Developer & Technology Mentor
# Run this ONE file to start both FastAPI and Streamlit together.
# Usage: python start.py
#
# FastAPI  → http://localhost:8000
# Streamlit → http://localhost:8501

import os
import subprocess
import sys
import time
import signal
import threading

def stream_output(proc, prefix):
    for line in iter(proc.stdout.readline, b''):
        print(f"{prefix} {line.decode().rstrip()}", flush=True)

def main():
    env = os.environ.copy()
    env["BACKEND_URL"] = "http://localhost:8000"

    print("=" * 55)
    print("  SQL Analytics Agent — Starting up")
    print("  Author: Suresh D R | AI Product Developer")
    print("=" * 55)
    print()

    # Start FastAPI backend
    print("▶ Starting FastAPI backend on http://localhost:8000 ...")
    backend = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "src.api.main:app",
         "--host", "0.0.0.0", "--port", "8000",
         "--timeout-keep-alive", "300"],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        env=env,
    )

    # Give backend 3 seconds to start
    time.sleep(3)

    # Start Streamlit frontend
    print("▶ Starting Streamlit UI on http://localhost:8501 ...")
    frontend = subprocess.Popen(
        [sys.executable, "-m", "streamlit", "run", "streamlit_app.py",
         "--server.port=8501",
         "--server.address=0.0.0.0",
         "--server.headless=true"],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        env=env,
    )

    # Stream logs from both in background threads
    threading.Thread(target=stream_output, args=(backend,  "[API]"), daemon=True).start()
    threading.Thread(target=stream_output, args=(frontend, "[UI] "), daemon=True).start()

    print()
    print("✅ Both services started!")
    print("   API → http://localhost:8000/health")
    print("   UI  → http://localhost:8501")
    print()
    print("Press CTRL+C to stop both.")
    print()

    def shutdown(sig, frame):
        print("\nShutting down...")
        backend.terminate()
        frontend.terminate()
        sys.exit(0)

    signal.signal(signal.SIGINT,  shutdown)
    signal.signal(signal.SIGTERM, shutdown)

    # Wait for either process to exit
    while True:
        if backend.poll() is not None:
            print("❌ Backend exited unexpectedly. Check logs above.")
            frontend.terminate()
            sys.exit(1)
        if frontend.poll() is not None:
            print("❌ Streamlit exited unexpectedly. Check logs above.")
            backend.terminate()
            sys.exit(1)
        time.sleep(1)

if __name__ == "__main__":
    main()
