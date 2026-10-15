"""Host observer subset; the Windows C runtime fixture runs in the native job."""
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'game'))
from test_monorail import ObserverTests
