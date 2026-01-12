import subprocess
import sys
import os

if __name__ == "__main__":
    print("🚀 Starting Agentic Local Backend...")
    print("   To start the full stack (backend + frontend), use './start.sh'")
    print("   Running api.py...\n")
    
    try:
        # Check if api.py exists
        if not os.path.exists("api.py"):
            print("❌ Error: api.py not found in current directory.")
            sys.exit(1)
            
        subprocess.run([sys.executable, "api.py"], check=True)
    except KeyboardInterrupt:
        print("\n✅ Stopped.")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        sys.exit(1)
