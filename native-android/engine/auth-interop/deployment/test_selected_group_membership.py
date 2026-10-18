"""New original region-filter/fixture controls, no server or Auth replay."""
from contextlib import ExitStack
import json
from pathlib import Path
import re
import sqlite3
import subprocess
import tempfile
from types import SimpleNamespace
import unittest
from unittest import mock

import hosted_selected_shard_play as stage
from source_audit import extract

ROOT=Path(__file__).resolve().parents[4]


def original_filter_source(source):
    start='void CServerList::MakeServerListPacket('
    following='\nvoid CServerList::MakeQueueSizePacket('
    if source.count(start)!=1 or source.count(following)!=1:
        raise ValueError('original_server_filter_boundary')
    value=source[source.index(start):source.index(following)].rstrip()
    if not value.endswith('}'):raise ValueError('original_server_filter_boundary')
    return value


class SelectedGroupMembershipTests(unittest.TestCase):
    def test_membership_is_only_in_new_selected_fixture_and_requires_original_procedure(self):
        original=stage.auth_service_profile.account_sql()
        self.assertNotIn('user_server_group',original)
        selected=stage.account_sql()
        self.assertEqual(selected.count('INSERT dbo.user_server_group'),1)
        self.assertIn('INSERT dbo.user_server_group(uid,server_group_id) VALUES(900001,1);',selected)
        self.assertIn('INSERT @selected_groups EXEC cohauth.dbo.get_server_groups @uid=900001;',stage.GROUP_QUERY)
        self.assertNotIn('USE ',stage.GROUP_QUERY)
        self.assertNotIn('UPDATE ',stage.GROUP_QUERY)
        self.assertNotIn('DELETE ',stage.GROUP_QUERY)
        self.assertNotIn('INSERT dbo.',stage.GROUP_QUERY)

    def test_same_sql_predicate_refuses_missing_wrong_extra_and_stale_owned_membership(self):
        schema=(ROOT/'upstream/ouroboros/Assets/DBSchemas/cohauth.sql').read_text()
        procedure=re.search(r'CREATE PROCEDURE \[dbo\]\.\[get_server_groups\](.*?)\nGO',schema,re.S).group(1)
        original_select=re.search(r'SELECT server_group_id FROM user_server_group\s+WHERE \[uid\] = @uid;',procedure).group(0)
        # SQLite executes the unchanged SELECT/CASE predicates. Only SQL Server
        # namespace/table-variable spelling and parameter binding are adapted;
        # the source stored-procedure SELECT supplies returned_groups itself.
        predicate=stage.GROUP_QUERY[stage.GROUP_QUERY.index('SELECT CASE'):].replace('cohauth.dbo.','').replace('@selected_groups','returned_groups')
        mutations={
            'missing':['DELETE FROM user_server_group'],
            'wrong-group':['UPDATE user_server_group SET server_group_id=2'],
            'extra-group':['INSERT INTO user_server_group VALUES(900001,2)'],
            'stale-uid':['UPDATE user_server_group SET uid=900000'],
            'wrong-account-uid':['UPDATE user_account SET uid=900002'],
            'extra-account':["INSERT INTO user_account VALUES('other',900002)"],
            'wrong-auth-account':["UPDATE user_auth SET account='other'"],
            'wrong-server-group':['UPDATE server SET server_group_id=2'],
            'wrong-server-id':['UPDATE server SET id=2'],
            'extra-server':["INSERT INTO server VALUES(2,1,'127.0.0.1','127.0.0.1',7000)"],
            'wrong-address':["UPDATE server SET ip='127.0.0.2'"],
            'wrong-inner-address':["UPDATE server SET inner_ip='127.0.0.2'"],
            'wrong-port':['UPDATE server SET client_port=7001'],
        }
        for case,changes in [('exact',[]),*mutations.items(),('stale-procedure-result',[])]:
            with self.subTest(case=case),sqlite3.connect(':memory:') as db:
                db.executescript('CREATE TABLE user_account(account text,uid int);CREATE TABLE user_auth(account text);'
                    'CREATE TABLE server(id int,server_group_id int,ip text,inner_ip text,client_port int);'
                    'CREATE TABLE user_server_group(uid int,server_group_id int);CREATE TABLE returned_groups(server_group_id int);')
                db.execute('INSERT INTO user_account VALUES(?,900001)',[stage.password_fixture.ACCOUNT])
                db.execute('INSERT INTO user_auth VALUES(?)',[stage.password_fixture.ACCOUNT])
                db.execute("INSERT INTO server VALUES(1,1,'127.0.0.1','127.0.0.1',7000)")
                db.execute('INSERT INTO user_server_group VALUES(900001,1)')
                for change in changes:db.execute(change)
                groups=db.execute(original_select.replace('@uid','?'),[900001]).fetchall()
                db.executemany('INSERT INTO returned_groups VALUES(?)',groups)
                if case=='stale-procedure-result':db.execute('UPDATE returned_groups SET server_group_id=2')
                self.assertEqual(db.execute(predicate).fetchone()[0],int(case=='exact'))

    def test_scalar_is_exact_integer_one_and_refuses_private_failures(self):
        for value in (0,2,-1,True,False,1.0,'1',None):
            with self.subTest(value=value),mock.patch.object(stage.activation,'scalar',return_value=value),\
                    self.assertRaisesRegex(ValueError,'selected_group_membership_not_exact'):
                stage.require_group_membership([],Path('private'))
        with mock.patch.object(stage.activation,'scalar',return_value=1) as scalar:
            stage.require_group_membership([],Path('private'))
            self.assertEqual(scalar.call_args.args[1],stage.GROUP_QUERY)
        error=ValueError('fixed_private_scalar_refusal')
        with mock.patch.object(stage.activation,'scalar',side_effect=error),self.assertRaises(ValueError) as caught:
            stage.require_group_membership([],Path('private'))
        self.assertIs(caught.exception,error)

    def test_actual_original_cpp_filter_omits_unassigned_group_one_and_preserves_match(self):
        source=(ROOT/'upstream/ouroboros/AuthServer/src/ServerList.cpp').read_text()
        code=r'''
#include <map>
#include <vector>
#include <cstring>
#include <cstdio>
#define MAX_REGIONS 10
#define MAX_SERVER_NAME 25
#define AC_SEND_SERVERLIST 4
#define OUROBOROS_PROTOCOL_VERSION_1 190516
struct ServerId {unsigned char id;char GetValueChar()const{return id;}bool operator<(const ServerId&o)const{return id<o.id;}};
struct Address {struct{unsigned S_addr;}S_un;};
struct WorldServer {ServerId serverid;Address outer_addr;int outer_port,region_id;char ageLimit,pkflag,status,isVIP;short UserNum,maxUsers;char name[26];};
struct Lock {void ReadLock()const{}void ReadUnlock()const{}};
struct {unsigned ProtocolVer;}config={191021};
class CServerList {public:typedef std::map<ServerId,WorldServer> ServerListType;ServerListType m_serverList;Lock mylock;
void MakeServerListPacket(std::vector<char>&,ServerId,int[MAX_REGIONS])const;};
'''
        code+='\n'.join(extract(source,name) for name in ('PushInt','PushShort'))+'\n'+original_filter_source(source)
        code+=r'''
int main(){unsigned checks=0;CServerList list;WorldServer w={};w.serverid.id=1;w.outer_addr.S_un.S_addr=0x0100007f;w.outer_port=7000;w.region_id=1;w.status=1;std::strcpy(w.name,"Owned fixture");list.m_serverList[w.serverid]=w;
int regions[MAX_REGIONS];for(int &r:regions){r=-1;}ServerId last={0};std::vector<char> b;
list.MakeServerListPacket(b,last,regions);if(b.size()!=5||b[3]!=0)return 1;checks++;
regions[0]=1;b.clear();list.MakeServerListPacket(b,last,regions);if(b[3]!=1||b[5]!=1)return 1;checks++;
regions[0]=2;b.clear();list.MakeServerListPacket(b,last,regions);if(b.size()!=5||b[3]!=0)return 1;checks++;
regions[1]=1;b.clear();list.MakeServerListPacket(b,last,regions);if(b[3]!=1)return 1;checks++;
for(int &r:regions){r=-1;}list.m_serverList.begin()->second.region_id=0;b.clear();list.MakeServerListPacket(b,last,regions);if(b[3]!=1)return 1;checks++;
std::printf("{\"passed\":true,\"checks\":%u,\"original_filter_unchanged\":true,\"real_auth_server_execution\":false}\n",checks);return 0;}
'''
        with tempfile.TemporaryDirectory() as name:
            path=Path(name)/'filter.cpp';binary=Path(name)/'filter';path.write_text(code)
            subprocess.run(['c++','-std=c++11','-O2','-Wall','-Wextra','-Werror',path,'-o',binary],check=True,capture_output=True)
            result=subprocess.run([binary],check=True,capture_output=True,timeout=10)
            self.assertEqual(json.loads(result.stdout),dict(passed=True,checks=5,original_filter_unchanged=True,real_auth_server_execution=False))

    def test_membership_is_checked_before_probe_and_after_every_outcome_without_masking_primary(self):
        for case in ('success','missing-before','changed-after','probe-and-after-fail'):
            with self.subTest(case=case):
                scope=stage.SelectedScope(Path('unused'));scope.binary=Path('probe')
                proof={'selected_probe_build':{'binary':{'sha256':'fixed'}}}
                baseline={'pid':30,'exists':True};groups=iter([0] if case=='missing-before' else [1,0] if case in ('changed-after','probe-and-after-fail') else [1,1])
                error=ValueError('fixed_native_failure')
                def scalar(sql,query,temporary):return next(groups) if query==stage.GROUP_QUERY else 1
                args=(Path('private'),proof,[],[21000,21001,21002],SimpleNamespace(pid=10),SimpleNamespace(pid=20),
                    Path('AuthServer.exe'),Path('DbServer.exe'),{}, {},30,baseline)
                with ExitStack() as stack:
                    stack.enter_context(mock.patch.object(stage.activation,'service_process_snapshot',return_value={'exists':True}))
                    stack.enter_context(mock.patch.object(stage.login,'owned_process_snapshot',return_value=baseline))
                    stack.enter_context(mock.patch.object(stage.activation,'owned_channel',return_value={'loopback_pair_verified':True}))
                    stack.enter_context(mock.patch.object(stage.activation,'game_listener',return_value={'owner_pid':20}))
                    stack.enter_context(mock.patch.object(stage.login,'inspect_listeners',return_value=set(args[3])))
                    stack.enter_context(mock.patch.object(stage.activation,'scalar',side_effect=scalar))
                    stack.enter_context(mock.patch.object(stage.login,'probe_identity',return_value={'sha256':'fixed'}))
                    probe=stack.enter_context(mock.patch.object(stage,'run_probe',return_value={'passed':True},side_effect=error if case=='probe-and-after-fail' else None))
                    if case=='success':
                        self.assertTrue(scope.exercise(*args));self.assertTrue(proof['selected_runtime_before_probe']['registered_group_membership_verified'])
                        self.assertTrue(proof['selected_runtime_after_probe']['registered_group_membership_verified'])
                    else:
                        with self.assertRaises(ValueError) as caught:scope.exercise(*args)
                        if case=='probe-and-after-fail':self.assertIs(caught.exception,error)
                        else:self.assertEqual(str(caught.exception),'selected_group_membership_not_exact')
                        if case=='missing-before':probe.assert_not_called();self.assertNotIn('client_login_attempted',proof)
                        else:self.assertFalse(proof['selected_runtime_after_probe_verified'])


if __name__=='__main__':unittest.main()
