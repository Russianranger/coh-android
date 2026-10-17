"""Qualification-side source execution only; no source/world authority factory.

Bootstrap this file itself by compile(frozen_bytes, filename, 'exec') AFTER the
entry script has frozen and revalidated its complete project dependency set.
Python stdlib/interpreter/toolchain are trusted host dependencies, not covered
by this project-only closure. Project helpers must have no transitive ordinary
project imports: pass other checked modules explicitly instead.
"""
import hashlib
from pathlib import Path
from types import ModuleType
class CheckedSources:
 def __init__(self,sources):
  self._sources={Path(path).resolve():bytes(raw) for path,raw in sources.items()}
  self.loads=[]
 def verify(self):
  for path,raw in self._sources.items():
   if path.read_bytes()!=raw:raise RuntimeError('qualification source changed: '+str(path))
 def load(self,name,path):
  request=Path(path)
  if request.suffix!='.py':raise ValueError('only admitted Python source; PYC is refused')
  path=request.resolve()
  if path not in self._sources:raise ValueError('project source not frozen: '+str(path))
  self.verify()
  raw=self._sources[path]
  module=ModuleType(name);module.__file__=str(path);module.__cached__=None
  module.__package__='';module.__loader__=None
  exec(compile(raw,str(path),'exec',dont_inherit=True),module.__dict__)
  self.verify()
  self.loads.append({'path':str(path),'sha256':hashlib.sha256(raw).hexdigest(),'execution':'compile_frozen_source_bytes','pyc_used':False})
  return module
