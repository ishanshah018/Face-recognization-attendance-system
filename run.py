import subprocess
import sys
import os
import time
import threading

def log_streamer(process, name):
    try:
        for line in iter(process.stdout.readline, ''):
            if line:
                print(f"[{name}] {line.strip()}")
    except Exception:
        pass
    finally:
        try:
            process.stdout.close()
        except Exception:
            pass

def main():
    root_dir = os.path.dirname(os.path.abspath(__file__))
    frontend_dir = os.path.join(root_dir, "frontend")
    
    # Resolve correct paths to Python interpreter and uvicorn inside the virtual env
    if sys.platform == "win32":
        uvicorn_bin = os.path.join(root_dir, ".venv", "Scripts", "uvicorn.exe")
    else:
        uvicorn_bin = os.path.join(root_dir, ".venv", "bin", "uvicorn")
        
    # Fallback to global command if .venv doesn't exist or doesn't have uvicorn
    if not os.path.exists(uvicorn_bin):
        uvicorn_bin = "uvicorn"

    print("🚀 Starting Face Recognition Attendance System...")

    # 1. Start Backend API
    print("👉 Starting FastAPI Backend...")
    backend_cmd = [uvicorn_bin, "app.main:app", "--host", "127.0.0.1", "--port", "8000", "--reload"]
    try:
        backend_process = subprocess.Popen(
            backend_cmd,
            cwd=root_dir,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1
        )
    except Exception as e:
        print(f"❌ Failed to start Backend: {e}")
        sys.exit(1)

    backend_thread = threading.Thread(target=log_streamer, args=(backend_process, "Backend"), daemon=True)
    backend_thread.start()

    # Wait a moment for backend to initialize
    time.sleep(2)

    # 2. Start Frontend UI
    print("👉 Starting Frontend UI (Vite + React)...")
    npm_cmd = "npm.cmd" if sys.platform == "win32" else "npm"
    try:
        frontend_process = subprocess.Popen(
            [npm_cmd, "run", "dev"],
            cwd=frontend_dir,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1
        )
    except Exception as e:
        print(f"❌ Failed to start Frontend: {e}")
        backend_process.terminate()
        sys.exit(1)

    frontend_thread = threading.Thread(target=log_streamer, args=(frontend_process, "Frontend"), daemon=True)
    frontend_thread.start()

    print("\n✅ Both servers are running successfully!")
    print("🔗 Frontend: http://127.0.0.1:5173")
    print("🔗 Backend API: http://127.0.0.1:8000")
    print("💡 Press Ctrl+C to stop both servers at the same time.\n")

    try:
        while True:
            # Check if either process died
            if backend_process.poll() is not None:
                print("❌ Backend stopped unexpectedly.")
                break
            if frontend_process.poll() is not None:
                print("❌ Frontend stopped unexpectedly.")
                break
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n🛑 Stopping servers...")
    finally:
        # Clean up processes on exit
        backend_process.terminate()
        frontend_process.terminate()
        try:
            backend_process.wait(timeout=3)
            frontend_process.wait(timeout=3)
        except subprocess.TimeoutExpired:
            backend_process.kill()
            frontend_process.kill()
        print("👋 Goodbye!")

if __name__ == "__main__":
    main()
