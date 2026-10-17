#!/usr/bin/env python3
"""Pure private-source transformation. Never edits upstream or starts a server."""
from pathlib import Path
import hashlib
HERE=Path(__file__).resolve().parent
SOURCE_SHA256='cd739e2a1b424bf089017be73d3c42adef0f23aca7563e8577cfc98ecdfebff9'
def stage(source):
 source=source.replace('\r\n','\n')
 if hashlib.sha256(source.encode()).hexdigest()!=SOURCE_SHA256:raise ValueError('original groupnetsend source pin differs')
 marker='void worldSendUpdate(NetLink *link,int full_update)\n{'
 final='    //sendAllBounds(pak);\n    pak->reliable=1;\n    pktSend(&pak,link);'
 if source.count(marker)!=1 or source.count(final)!=1:raise ValueError('hook anchor differs')
 include='\n'+(HERE/'source_groups_eligibility.inc').read_text()+'\n'+(HERE/'source_groups_transaction.inc').read_text()+'\n'
 source=source.replace(marker,include+marker)
 start=source.index(marker); anchor='    Packet        *pak;'; at=source.index(anchor,start)+len(anchor)
 source=source[:at]+'\n    coh_groups_transaction_begin(link,full_update);'+source[at:]
 return source.replace(final,'    coh_groups_transaction_finish(pak);\n'+final)
