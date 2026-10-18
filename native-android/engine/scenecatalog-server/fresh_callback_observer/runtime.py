"""Optional source-profile wiring only; no process startup or authority gates."""
from . import probe,stage
ROLE=stage.ROLE

def enabled(compiled):
 return type(compiled) is dict and compiled.get('build_role')==ROLE

def source_paths(root):
 # Admission checks every executing helper/supplier against THIS committed tree.
 # This runtime map is private; it is not the compiled-PE consumer fingerprint.
 return set(stage.checkout_closure(root))

def precreate(compiled,path):
 if not enabled(compiled):return None
 try:return probe.precreate(path)
 except Exception:return None

def bind(owner,child,streams,children,handles):
 if owner is None:return
 try:probe.bind(owner,child,streams,children,handles)
 except Exception:pass

def refused():
 value=probe.empty();value['probe_state']='REFUSED';return probe.public(value)

def record(report,owner,child,*,cleanup_attempted):
 """Optional errors never alter the independent GROUPS/cleanup result."""
 try:
  public,private=probe.collect(owner,child,cleanup_attempted=cleanup_attempted)
  projected=probe.public(public)
  # Validate projection before mutating even these optional report fields.
  report.pop('source_profile_private_binding',None)
  report['source_profile_diagnostic']=projected
  if private is not None:report['source_profile_private_binding']=private
 except Exception:
  report.pop('source_profile_private_binding',None)
  report['source_profile_diagnostic']=refused()
