import sys
import os

# Ensure `src/` is in `sys.path`
src_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "../src"))
if src_path not in sys.path:
    sys.path.insert(0, src_path)

print(f"DEBUG: conftest.py is running")
print(f"DEBUG: sys.path = {sys.path}")