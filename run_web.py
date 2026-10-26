"""Single-process server; frontend and dependencies must be built beforehand."""
import os
from pathlib import Path
from dotenv import load_dotenv

if __name__=='__main__':
    load_dotenv(Path(__file__).with_name('.env.web'),override=False)
    os.environ['LEXIS_WEB_MODE']='1'
    if not os.environ.get('LEXIS_DATABASE_URL'):
        raise SystemExit('Set LEXIS_DATABASE_URL in .env.web before starting the web server')
    if not (Path(__file__).parent/'frontend/dist/index.html').is_file():
        raise SystemExit('Build frontend first: cd frontend && npm ci && npm run build')
    import uvicorn
    uvicorn.run('backend.main:app',host=os.environ.get('LEXIS_BIND_HOST','127.0.0.1'),
                port=int(os.environ.get('LEXIS_PORT','8002')),workers=1,proxy_headers=True,
                forwarded_allow_ips=os.environ.get('LEXIS_PROXY_IPS','127.0.0.1'))
