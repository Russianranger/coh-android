"""Isolated exact original texFixName short-suffix correction; never edits upstream."""
import difflib,hashlib
ORIGINAL_SHA256='940ef057ef069227a30687807b77623708162f3dc441f6a1b7f66235a363beed'
def patch(function):
 if hashlib.sha256(function.encode()).hexdigest()!=ORIGINAL_SHA256:raise ValueError('Exact original texFixName function pin differs')
 before="{\nint        type = 0;";after="{\nchar *const res_start = res;\nint        type = 0;"
 guard="else if(res[-8] == '.')";fixed="else if(res - res_start >= 8 && res[-8] == '.')"
 if function.count(before)!=1 or function.count(guard)!=1:raise ValueError('Exact two-location candidate preimage differs')
 candidate=function.replace(before,after,1).replace(guard,fixed,1)
 return candidate,{'original_function_sha256_lf':ORIGINAL_SHA256,'candidate_function_sha256_lf':hashlib.sha256(candidate.encode()).hexdigest(),'isolated_correction_only':True,'unchanged_original_for_repaired_cases':False,'diff':''.join(difflib.unified_diff(function.splitlines(True),candidate.splitlines(True),fromfile='original/texFixName',tofile='candidate/texFixName'))}
