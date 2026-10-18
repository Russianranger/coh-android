"""Optional source-profile wiring only; no process startup or authority gates."""
from pathlib import Path
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

def probe_windows_path(owner,catalog,catalog_windows):
 """Use the existing admitted C-drive destination for the same owned sidecar.

 The generic Unix-to-Wine helper uses Z:, whose reparse drive root is refused
 by the unchanged source sink path policy. This function creates no mapping,
 file or directory and never weakens that policy.
 """
 try:
  probe.require(type(owner) is probe.ProbeOwner)
  catalog=Path(catalog)
  probe.require(catalog_windows==r'C:\coh-native-catalog\catalog.cohcat'
   and catalog.is_absolute() and catalog.name=='catalog.cohcat'
   and owner.path==catalog.parent/'source-profile-probe.json')
  probe.require(probe._path_info(owner).st_size==0)
  return r'C:\coh-native-catalog\source-profile-probe.json'
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
