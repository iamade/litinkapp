from app.main import app
from fastapi.routing import APIRoute
for r in app.routes:
    if hasattr(r, 'routes'):
        for sr in r.routes:
            if isinstance(sr, APIRoute):
                print(sr.path, sr.methods)
    elif isinstance(r, APIRoute):
        print(r.path, r.methods)
