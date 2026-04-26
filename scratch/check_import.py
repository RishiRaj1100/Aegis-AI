import sys
import os
sys.path.append(os.getcwd())

try:
    from core.pipeline import AegisAIPipeline
    print("Pipeline imported successfully")
except Exception as e:
    import traceback
    traceback.print_exc()
