from pathlib import Path
import sys
from types import SimpleNamespace
import unittest
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import login_ui

def result(text='',code=0):return SimpleNamespace(stdout=text,returncode=code)
def geometry(w,width=1024,height=768):return result(f'WINDOW={w}\nX=104\nY=130\nWIDTH={width}\nHEIGHT={height}\n')

class OwnedFrameWindow(unittest.TestCase):
    @patch.object(login_ui,'sh')
    def test_map_title_independent_owned_class_and_size(self,sh):
        sh.side_effect=[result('101\n'),geometry(101)]
        self.assertEqual(login_ui.owned_client_window([8082]),(104,130,1024,768))
        sh.assert_any_call('xdotool','search','--all','--onlyvisible','--pid','8082','--class',r'^cityofheroes\.exe$')
        self.assertFalse(any('--name' in c.args for c in sh.call_args_list))
    @patch.object(login_ui,'sh')
    def test_ime_is_not_a_frame(self,sh):
        def run(*args):
            if args[1]=='search':return result('101\n102\n')
            return geometry(args[-1],1,1) if args[-1]=='102' else geometry(101)
        sh.side_effect=run
        self.assertEqual(login_ui.owned_client_window([8082]),(104,130,1024,768))
    @patch.object(login_ui,'sh')
    def test_ambiguity_fails_closed(self,sh):
        sh.side_effect=lambda *a: result('101\n102') if a[1]=='search' else geometry(a[-1])
        self.assertIsNone(login_ui.owned_client_window([8082]))
    @patch.object(login_ui,'sh')
    def test_no_single_owned_process(self,sh):
        for pids in ([],[1,2],[0],[-1],[True],['1']):self.assertIsNone(login_ui.owned_client_window(pids))
        sh.assert_not_called()
    @patch.object(login_ui,'sh')
    def test_failed_or_malformed_search(self,sh):
        for r in (result('',1),result('abc'),result(''),result(' '.join(map(str,range(17))))):
            sh.return_value=r;self.assertIsNone(login_ui.owned_client_window([8082]))
    @patch.object(login_ui,'sh')
    def test_stale_wrong_or_small_geometry(self,sh):
        for g in (result('',1),result('WIDTH=1024'),geometry(999),geometry(101,1,1),result('WINDOW=101 X=-1 Y=0 WIDTH=1024 HEIGHT=768')):
            sh.side_effect=[result('101'),g];self.assertIsNone(login_ui.owned_client_window([8082]))
if __name__=='__main__':unittest.main()
