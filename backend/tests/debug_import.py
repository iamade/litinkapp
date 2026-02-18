import sys
import os

# Add the project root to sys.path
sys.path.append(os.getcwd())

from dotenv import load_dotenv

load_dotenv(".envs/.env.local")

try:
    print("Attempting to import app.api.routes.auth...")
    from app.api.routes import auth

    print("Import successful!")
    print(f"Auth router: {auth.router}")
except Exception as e:
    print(f"Import failed: {e}")
    import traceback

    traceback.print_exc()
