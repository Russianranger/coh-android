#!/usr/bin/env python3
"""Compile/execute the closed native directory core on host and Bionic ARM64.

No game/database/assets are fetched, started or changed. The ARM fixture is a
static Bionic binary run through QEMU user mode on Linux, not Android OS/Wine.
"""
from __future__ import annotations
import argparse
import datetime as dt
import hashlib
import json
import os
from pathlib import Path
import platform
import re
import subprocess
import sys
import time

HERE=Path(__file__).resolve().parent
NDK_VERSION="27.2.12479018"
SOURCES=("coh_live_directory_core.h","coh_live_directory_core.c","coh_live_directory_jni.c",
         "native_core_faults.c","test_native_live_directory_core.py","native_live_fixture.c",
         "NativeLiveDirectory.java","NativeLiveDirectoryFixture.java","qualify_native_live_directory.py","README.md")
FLAGS=["-std=c11","-O2","-Wall","-Wextra","-Werror","-Wpedantic"]

def pin(path):
    path=Path(path)
    with path.open("rb") as source:digest=hashlib.file_digest(source,"sha256").hexdigest()
    return {"bytes":path.stat().st_size,"sha256":digest}
def require(condition,message):
    if not condition:raise ValueError(message)
def execute(command,out,record,label):
    started=time.monotonic();result=subprocess.run([str(x) for x in command],capture_output=True,timeout=180,check=False)
    stdout=out/(label+".stdout");stderr=out/(label+".stderr")
    require(len(result.stdout)<=256*1024 and len(result.stderr)<=256*1024,"Controlled output bound exceeded")
    stdout.write_bytes(result.stdout);stderr.write_bytes(result.stderr)
    entry={"label":label,"command":[str(x) for x in command],"exit_code":result.returncode,
           "elapsed_seconds":time.monotonic()-started,"stdout":pin(stdout),"stderr":pin(stderr)}
    record["commands"].append(entry)
    require(result.returncode==0,f"{label} failed; retained stdout/stderr")
    return result.stdout.decode("utf-8")

def main():
    parser=argparse.ArgumentParser();parser.add_argument("--out",type=Path,required=True)
    parser.add_argument("--host-headers",type=Path)
    parser.add_argument("--ndk",type=Path)
    parser.add_argument("--qemu",default="qemu-aarch64")
    args=parser.parse_args();out=args.out.resolve();out.mkdir(parents=True,exist_ok=False)
    report={"schema":"coh-live-native-directory-qualification-v1","started_utc":dt.datetime.now(dt.timezone.utc).isoformat(),
            "host":{"platform":platform.platform(),"uid":os.getuid()},"source_files":{name:pin(HERE/name) for name in SOURCES},
            "commands":[],"status":"incomplete","host_native_kernel":False,"host_JNI":False,"Bionic_ARM64_fixture":False,
            "Android_OS_Wine_FEX_PRoot_parity":False,"registered_Game_consumer":False,"shipping_admission":False,
            "physical_Thor_performance":False,"native_SQL_or_player_data_touched":False}
    try:
        execute([sys.executable,"-W","error::ResourceWarning",HERE/"test_native_live_directory_core.py"],out,report,"host-native-kernel-tests")
        report["host_native_kernel"]=True
        host_fixture=out/"native-live-host-fixture"
        execute(["gcc",*FLAGS,HERE/"coh_live_directory_core.c",HERE/"native_live_fixture.c","-o",host_fixture],out,report,"compile-host-fixture")
        host_result=json.loads(execute([host_fixture],out,report,"execute-host-fixture"));require(host_result["controls_passed"]==26 and host_result["failures"]==0,"Native fixture gates")
        report["host_fixture"]=host_result
        headers=args.host_headers or Path(os.environ["JAVA_HOME"])/"include"
        report["host_JNI_headers"]={str(p):pin(p) for p in [headers/"jni.h",(headers/"jni_md.h" if (headers/"jni_md.h").exists() else headers/"linux/jni_md.h")]}
        host_so=out/"libcoh_live_directory-host.so"
        execute(["gcc",*FLAGS,"-fPIC","-shared","-pthread","-I"+str(headers),"-I"+str(headers/"linux"),
                 HERE/"coh_live_directory_core.c",HERE/"coh_live_directory_jni.c","-o",host_so],out,report,"compile-host-JNI")
        classes=out/"classes";classes.mkdir()
        execute(["java","-m","jdk.compiler/com.sun.tools.javac.Main","-d",classes,HERE/"NativeLiveDirectory.java",HERE/"NativeLiveDirectoryFixture.java"],out,report,"compile-Java-facade-fixture")
        jni_result=json.loads(execute(["java","-Xcheck:jni","-cp",classes,"io.github.russianranger.cohclientinteractive.NativeLiveDirectoryFixture",host_so],out,report,"execute-host-JNI"))
        require((out/"execute-host-JNI.stderr").stat().st_size==0,"JNI warnings/errors are a qualification failure")
        require(jni_result["controls_passed"]==28 and jni_result["failures"]==0,"JNI fixture gates")
        report["host_JNI"]=True;report["host_JNI_fixture"]=jni_result
        if args.ndk:
            ndk=args.ndk.resolve();properties=(ndk/"source.properties").read_text()
            require(re.search(r"^Pkg.Revision\s*=\s*"+re.escape(NDK_VERSION)+r"\s*$",properties,re.M),"Pinned NDK revision required")
            tools=ndk/"toolchains/llvm/prebuilt/linux-x86_64/bin"
            compiler=tools/"aarch64-linux-android29-clang";readelf=tools/"llvm-readelf"
            report["NDK"]={"version":NDK_VERSION,"source_properties":pin(ndk/"source.properties"),"compiler":pin(compiler.resolve()),"compiler_version":execute([compiler,"--version"],out,report,"NDK-compiler-version")}
            arm_fixture=out/"native-live-Bionic-ARM64-fixture"
            execute([compiler,*FLAGS,"-static","-pthread",HERE/"coh_live_directory_core.c",HERE/"native_live_fixture.c","-o",arm_fixture],out,report,"compile-Bionic-ARM64-fixture")
            execute([readelf,"--file-header",arm_fixture],out,report,"inspect-Bionic-ARM64-fixture")
            arm_result=json.loads(execute([args.qemu,arm_fixture],out,report,"execute-Bionic-ARM64-fixture"))
            require(arm_result["libc"]=="Bionic" and arm_result["pointer_bytes"]==8 and arm_result["controls_passed"]==26 and arm_result["failures"]==0,"Actual static Bionic ARM64 fixture gates")
            report["Bionic_ARM64_fixture"]=True;report["Bionic_ARM64_fixture_result"]=arm_result
            android_so=out/"libcoh_live_directory.so"
            execute([compiler,*FLAGS,"-fPIC","-shared","-pthread","-fstack-protector-strong","-Wl,-z,relro,-z,now","-Wl,--no-undefined",
                     HERE/"coh_live_directory_core.c",HERE/"coh_live_directory_jni.c","-o",android_so],out,report,"compile-Bionic-ARM64-JNI")
            elf=execute([readelf,"--wide","--file-header","--dynamic","--dyn-syms",android_so],out,report,"inspect-Bionic-ARM64-JNI")
            require("AArch64" in elf and "Class:                             ELF64" in elf,"Android JNI ELF64/AArch64 required")
            needed=re.findall(r"\(NEEDED\).*?\[([^]]+)\]",elf)
            require(needed==["libc.so"],"JNI dependency boundary changed")
            for name in ("nativeCreate","nativeOpen","nativeNext","nativeCloseCursor","nativeCloseNamespace","nativeStats","nativeIdentity","nativeCanonicalGuestPath"):
                require("Java_io_github_russianranger_cohclientinteractive_NativeLiveDirectory_"+name in elf,"Missing JNI export "+name)
            report["Bionic_ARM64_JNI"]={**pin(android_so),"needed":needed,"symbols_checked":8}
        report["status"]="passed" if args.ndk else "host-only-passed"
    except Exception as exc:
        report["status"]="failed";report["failure"]={"type":type(exc).__name__,"message":str(exc)}
        raise
    finally:
        report["finished_utc"]=dt.datetime.now(dt.timezone.utc).isoformat()
        report["artifacts"]={p.name:pin(p) for p in sorted(out.iterdir()) if p.is_file() and p.name!="qualification.json"}
        (out/"qualification.json").write_text(json.dumps(report,indent=2,sort_keys=True)+"\n")

if __name__=="__main__":main()
