"""Project root for all scripts: folder above scripts/ (override with env WANGEROOGE_BASE)."""
import os
BASE = os.environ.get('WANGEROOGE_BASE') or os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
