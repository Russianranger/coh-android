"""Bounded exporter, not a replacement parser for the complete player graph.

Imports named authored moves, Include member lists, original state numbering,
interrupt memberships, move flags and explicit ranges. Missing durations and
next-moves stay visibly unresolved; this tool never invents them.
"""
import hashlib
import json
import re
from pathlib import Path

SELECTED = {
    # Relative selected-move order follows player.txt and motion.inc includes.
    "player/motion/motion_fall.inc": ["RunFall", "RunFall_2"],
    "player/motion/motion_jump.inc": ["jumpPre", "jumpUp", "jumpApex", "jumpFall", "jumpFall2", "JumpPost"],
    "player/powers.inc": ["KickBrawl_R", "KickBrawl_R_post", "KickBrawl_L", "KickBrawl_L_post", "KickBrawl_cycle"],
    "player/reactions.inc": ["KnockDown_cycle"],
    "player/emotes.inc": ["Teabag_Pre", "Teabag", "Bow_Reverant", "Bow_Reverant_post"],
}

def clean(text):
    return "\n".join(re.split(r"#|//", line, 1)[0] for line in text.splitlines())

def export(source_root, asset_root):
    source_root, asset_root = Path(source_root), Path(asset_root)
    seqroot = asset_root / "data/sequencers"
    paths = {str(p.relative_to(asset_root / "data")).lower(): p for p in seqroot.rglob("*") if p.is_file()}
    hashes = {}
    def read(path):
        key=("ouroboros/"+str(path.relative_to(source_root))) if path.is_relative_to(source_root) else ("i24/"+str(path.relative_to(asset_root)))
        hashes[key] = hashlib.sha256(path.read_bytes()).hexdigest()
        return clean(path.read_text(errors="replace"))
    player_text=read(seqroot/"player.txt").lower().replace("\\","/")
    assert player_text.index("sequencers/player/motion.inc") < player_text.index("sequencers/player/powers.inc") < player_text.index("sequencers/player/reactions.inc") < player_text.index("sequencers/player/emotes.inc")
    motion_text=read(seqroot/"player/motion.inc").lower().replace("\\","/")
    assert motion_text.index("sequencers/player/motion/motion_fall.inc") < motion_text.index("sequencers/player/motion/motion_jump.inc")
    # Code bits are explicit; dynamic bits are appended in file order, skipping
    # duplicates, exactly as seqLoadStateBits. Sorted-name table is lookup only.
    state_h = source_root / "Common/seq/seqstate.h"
    state_c = source_root / "Common/seq/seqstate.c"
    raw_h, raw_c = read(state_h), read(state_c)
    triggered=source_root / "Common/seq/TriggeredMove.h"
    read(triggered)
    assert re.search(r"#define\s+MAXSTATES\s+876\b",triggered.read_text())
    defines = {k:int(v) for k,v in re.findall(r"#define\s+STATE_(\w+)\s+(\d+)", state_h.read_text())}
    states = {"EMPTY": 0}
    for name, define in re.findall(r'\{\s*"([^"]+)"\s*,\s*STATE_(\w+)', raw_c):
        states[name] = defines[define]
    for name in re.findall(r"^\s*StateBit\s+(\w+)", read(seqroot / "statebits.statebits"), re.M):
        name=name.upper()
        if name not in states:
            states[name] = max(states.values())+1
    assert max(states.values()) < 876
    seq_h = read(source_root / "Common/seq/seq.h")
    flag_values = {name: 1 << int(bit) for name, bit in re.findall(r"SEQMOVE_(\w+)\s*=\s*\(1\s*<<\s*(\d+)\)", seq_h)}
    read(source_root / "Common/seq/seqload.c")
    read(source_root / "Common/seq/seqsequence.c")
    read(source_root / "libs/UtilitiesLib/src/utils/mathutil.c")
    def expand(text, stack=()):
        lines=[]
        for line in text.splitlines():
            fields=line.split()
            if fields and fields[0].lower()=="include":
                key=fields[1].replace("\\", "/").lower()
                if key in stack: raise ValueError("cyclic include")
                lines += expand(read(paths[key]), stack+(key,))
            else: lines.append(line)
        return lines
    moves=[]
    for rel, names in SELECTED.items():
        text=read(seqroot / rel)
        blocks=re.findall(r"^\s*Move\s+(\S+)(.*?)^\s*MEnd\s*$", text, re.M|re.S)
        by_name={name.lower():(name,body) for name,body in blocks}
        for wanted in names:
            name, body=by_name[wanted.lower()]
            m={"name":name,"source":"data/sequencers/"+rel,"requires":[],"members":[],"interrupts":[],"flags":0,"priority":0,"scale":1.,"interpolate":5.,"next_name":"Ready","types":{}}
            ty=None
            for line in expand(body):
                fields=line.split()
                if not fields: continue
                key=fields[0].lower(); args=fields[1:]
                if key=="type":
                    ty=args[0].lower(); m["types"].setdefault(ty,{"type_scale":1.})
                elif key=="tend": ty=None
                elif ty:
                    if key=="anim" and "asset" not in m["types"][ty]:
                        m["types"][ty].update(asset="ANIMS/"+args[0].replace("\\","/")+".anim", first_frame=float(args[1]) if len(args)>1 else 0., last_frame=float(args[2]) if len(args)>2 else None)
                    elif key=="scale": m["types"][ty]["type_scale"]=float(args[0])
                elif key in ("requires", "member", "interrupts"):
                    m[{"requires":"requires","member":"members","interrupts":"interrupts"}[key]] += [a.upper() for a in args]
                elif key=="flags":
                    for flag in args: m["flags"] |= flag_values[flag.upper()]
                elif key in ("priority", "scale", "interpolate"): m[key]=float(args[0]) if key!="priority" else int(args[0])
                elif key=="nextmove": m["next_name"]=args[0]
                elif key=="cyclemove": raise ValueError("selected subset cannot silently discard CycleMove")
            # setSparseBit deduplicates by append; it does NOT sort. This order
            # determines the move's cached anchor bit and equal-priority ties.
            m["required"]=list(dict.fromkeys(states[s] for s in m["requires"]))
            moves.append(m)
    irq={}
    for m in moves:
        for name in m["interrupts"]:
            irq.setdefault(name,len(irq)+1)
    for m in moves:
        def words(names):
            out=[0]*14
            for name in names:
                if name in irq: out[irq[name]//32] |= 1 << (irq[name]%32)
            return out
        m["member_words"]=words(m["members"]+[m["name"].upper()])
        m["interrupt_words"]=words(m["interrupts"])
        m["next_move"]=next((i for i,n in enumerate(moves) if n["name"].lower()==m["next_name"].lower()),None)
    used={name:states[name] for m in moves for name in m["requires"]}
    return {"version":1,"scope":"selection/timing only; explicit authored ranges, unresolved original clip ends preserved","states":used,"moves":moves,"source_sha256":hashes}

def write_header(fixture,path):
    def arr(values,n): return "{"+",".join(str(v)+"u" for v in (values+[0]*n)[:n])+"}"
    out=['/* Generated from hash-pinned original sequencer data. */', '#include "coh_sequencer.h"']
    for key,bit in fixture["states"].items(): out.append(f"#define S_{key} {bit}u")
    for i,m in enumerate(fixture["moves"]): out.append("#define M_"+m["name"].upper()+f" {i}u")
    out.append("static const CohSeqMove source_moves[] = {")
    for m in fixture["moves"]:
        out.append("{"+json.dumps(m["name"])+f', {m["flags"]}u, {m["priority"]}, '+arr(m["required"],12)+f', {len(m["required"])}u, '+arr(m["member_words"],14)+", "+arr(m["interrupt_words"],14)+", "+("COH_SEQ_NONE" if m["next_move"] is None else str(m["next_move"])+"u")+", {0}, 0, "+str(m["scale"])+"f, "+str(m["interpolate"])+"f},")
    out += ["};", "static const CohSeqGraph source_graph={source_moves,sizeof source_moves/sizeof source_moves[0]};"]
    for rig in ("male", "huge"):
        out.append(f"static const CohSeqClip {rig}_clips[] = {{")
        for i,m in enumerate(fixture["moves"]):
            c=m["types"].get(rig,m["types"].get("male"))
            if not c or c.get("last_frame") is None:
                out.append("{{NULL,1},"+str(i)+",0,0,0,1},")
            else:
                out.append("{{"+json.dumps(c["asset"])+",1},"+f'{i},1,{c["first_frame"]}f,{c["last_frame"]}f,{c["type_scale"]}f'+"},")
        out.append("};")
    Path(path).write_text("\n".join(out)+"\n")

if __name__=="__main__":
    import argparse
    p=argparse.ArgumentParser(); p.add_argument("--source-root",required=True);p.add_argument("--asset-root",required=True);p.add_argument("--output",required=True)
    a=p.parse_args(); f=export(a.source_root,a.asset_root)
    Path(a.output).write_text(json.dumps(f,indent=2)+"\n")
