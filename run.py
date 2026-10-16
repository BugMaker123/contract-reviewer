import uvicorn
import sys
import os

# 确保在 Windows 控制台环境下正常输出 UTF-8
if sys.platform.startswith("win"):
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8")

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

if __name__ == "__main__":
    from backend.frontend_build import ensure_frontend_build
    ensure_frontend_build()
    print("=" * 65)
    print(" [LexisGraph] Contract Review Agent starting...")
    print(" Stack: LangGraph StateGraph + DeepSeek Dynamic Models + FastAPI")
    print(" Local URL: http://127.0.0.1:8001")
    print("=" * 65)
    uvicorn.run("backend.main:app", host="127.0.0.1", port=8001, reload=True,
                reload_dirs=[os.path.join(os.path.dirname(os.path.abspath(__file__)), "backend")])
