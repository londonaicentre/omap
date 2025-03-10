# import sys
# import os

# print("DEBUG: conftest.py is running")

# # Get the absolute path of the project's root directory
# ROOT_DIR = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))

# # Add 'src' to the Python path
# SRC_PATH = os.path.join(ROOT_DIR, "src")
# if SRC_PATH not in sys.path:
#     sys.path.insert(0, SRC_PATH)
#     print(f"DEBUG: Added {SRC_PATH} to sys.path")

import sys

print("DEBUG: sys.path =", sys.path)