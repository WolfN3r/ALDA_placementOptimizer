import sys
sys.path.insert(0, './scripts/lib')
from n8n_json_handler import run_n8n_script

SCRIPT_PATH = './scripts/03_initial_placer.py'  # 👈 CHANGE ONLY THIS PATH

return run_n8n_script(SCRIPT_PATH, items)
