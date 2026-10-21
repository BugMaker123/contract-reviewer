"""Windows distribution entry point; also hosts isolated document parsing."""
import os
import sys
from pathlib import Path


def main():
    if len(sys.argv) > 1 and sys.argv[1] == '--parse-document':
        import json
        from fastapi import HTTPException
        from backend.document_parse import extract
        try:
            result = {'text': extract(sys.stdin.buffer.read(), sys.argv[2])}
        except HTTPException as error:
            result = {'status': error.status_code, 'error': error.detail}
        sys.stdout.buffer.write(json.dumps(result, ensure_ascii=False).encode('utf-8'))
        return

    import logging
    import socket
    import threading
    import tkinter as tk
    from tkinter import ttk
    import webbrowser
    from logging.handlers import RotatingFileHandler

    if sys.platform == 'win32':
        import ctypes
        window = ctypes.windll.kernel32.GetConsoleWindow()
        if window:
            ctypes.windll.user32.ShowWindow(window, 0)
    data = Path(os.environ.get('LEXIS_DATA_DIR') or (Path(os.environ.get('LOCALAPPDATA', str(Path.home()))) / 'LexisGraph'))
    data.mkdir(parents=True, exist_ok=True)
    os.environ['LEXIS_DATA_DIR'] = str(data)
    log_path = data / 'application.log'
    logging.basicConfig(level=logging.INFO, handlers=[RotatingFileHandler(log_path, maxBytes=2_000_000, backupCount=3, encoding='utf-8')], format='%(asctime)s %(levelname)s %(name)s %(message)s')

    root = tk.Tk()
    root.title('LexisGraph 合同工作台')
    root.geometry('460x240')
    root.resizable(False, False)
    frame = ttk.Frame(root, padding=24)
    frame.pack(fill='both', expand=True)
    ttk.Label(frame, text='LexisGraph 合同工作台', font=('Microsoft YaHei UI', 17, 'bold')).pack(anchor='w')
    status = tk.StringVar(value='正在启动，请稍候…')
    ttk.Label(frame, textvariable=status, wraplength=410).pack(anchor='w', pady=(16, 8))
    ttk.Label(frame, text='使用期间请保留此窗口，关闭窗口即可退出。').pack(anchor='w')
    buttons = ttk.Frame(frame)
    buttons.pack(anchor='w', pady=20)
    server = None
    url = ''
    def open_page():
        if url:
            webbrowser.open(url)
    open_button = ttk.Button(buttons, text='打开工作台', command=open_page, state='disabled')
    open_button.pack(side='left', padx=(0, 12))
    ttk.Button(buttons, text='打开数据目录', command=lambda: os.startfile(data)).pack(side='left', padx=(0, 12))
    def close():
        if server:
            status.set('正在保存并退出…')
            server.should_exit = True
            poll_exit()
        else:
            root.destroy()
    def poll_exit():
        if worker.is_alive():
            root.after(200, poll_exit)
        else:
            root.destroy()
    ttk.Button(buttons, text='退出', command=close).pack(side='left')
    root.protocol('WM_DELETE_WINDOW', close)
    def serve():
        nonlocal server, url
        try:
            import uvicorn
            from backend.main import app
            sock = socket.socket()
            sock.bind(('127.0.0.1', 0))
            url = f'http://127.0.0.1:{sock.getsockname()[1]}'
            logging.info('Desktop URL: %s', url)
            server = uvicorn.Server(uvicorn.Config(app, log_config=None, host='127.0.0.1', workers=1))
            server.run(sockets=[sock])
        except Exception:
            logging.exception('Desktop startup failed')
    worker = threading.Thread(target=serve, daemon=True)
    worker.start()
    def ready():
        if server and server.started:
            status.set(f'服务已启动：{url}')
            open_button.configure(state='normal')
            if '--no-browser' not in sys.argv:
                open_page()
        elif not worker.is_alive():
            status.set(f'启动失败，请查看日志：{log_path}')
        else:
            root.after(200, ready)
    root.after(200, ready)
    root.mainloop()


if __name__ == '__main__':
    main()
