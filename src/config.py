from pathlib import Path

# This file assumes the project structure is:
# project_root/
# ├── data/
# ├── src/
# │   ├── __init__.py
# │   ├── config.py
# │   └── ...

# BASE_DIR is the root of the 'src' directory
BASE_DIR = Path(__file__).parent

# DATA_DIR is the 'data' directory located one level up from BASE_DIR
DATA_DIR = BASE_DIR.parent / 'data'