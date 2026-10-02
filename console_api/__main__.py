"""python -B -m console_api; project-local dependencies are optional."""
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).resolve().parents[1] / 'tmp/p6ui-deps'))
import uvicorn

if __name__ == '__main__':
    uvicorn.run('console_api.app:app', host='127.0.0.1', port=8765, access_log=False)
