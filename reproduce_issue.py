import sys
import os

# Add current directory to sys.path
sys.path.append(os.getcwd())

try:
    print("Attempting to import app.routers.chat...")
    from app.routers import chat
    print("Successfully imported app.routers.chat")
except Exception as e:
    print(f"Error importing app.routers.chat: {e}")
    import traceback
    traceback.print_exc()

try:
    print("\nAttempting to import app.services.pr_chat...")
    from app.services import pr_chat
    print("Successfully imported app.services.pr_chat")
except Exception as e:
    print(f"Error importing app.services.pr_chat: {e}")
    traceback.print_exc()
