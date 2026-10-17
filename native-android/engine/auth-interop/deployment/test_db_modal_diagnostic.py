import copy
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest import mock

import db_modal_diagnostic as stage
import hosted_auth_login as login

ROOT=Path(__file__).resolve().parents[4]


class DbModalDiagnosticTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.policy=stage.policy(ROOT)

    def raw(self,text,status='ok'):
        return {'pid':5256,'rows':[{'pid':5256,'top_level':True,'class_name':'#32770','control_id':0,
            'text':'City of Heroes','text_status':'ok'}, {'pid':5256,'top_level':False,'class_name':'Static',
            'control_id':10,'text':text,'text_status':status}], 'enumerated_top_level':10,
            'deadline_reached':False,'inventory_bound_reached':False,'text_bound_reached':False,
            'owner_changed_count':1 if status=='owner_changed' else 0,'top_level_enumeration_completed':True}

    def test_source_backed_assertion_and_exception_never_export_private_fields(self):
        point=self.policy['points']['ring_buffer_unset']
        private=('private-user secret-password cookie=395634 uid=900001 SQL SELECT account '
                 'D:\\private\\host-name 0x7a222222 stack frames')
        body=('Assertion failed\n\nProgram: '+private+'\nFile: D:\\private\\ring.hpp\nLine: '
            +str(point['lines'][0])+'\nExpression: !m_base\n\nError Message: '+private+'\n'+private)
        result=stage.admit(self.raw(body),5256,self.policy)
        match=result['source_matches'][0]
        self.assertEqual(match['kind'],'source_assertion');self.assertEqual(match['assertion_enum'],'ring_buffer_unset')
        self.assertTrue(match['source_assertion_line_verified']);self.assertTrue(match['source_call_site_verified'])
        self.assertTrue(match['source_expression_match']);self.assertFalse(match['compiled_expression_variant_match'])
        serialized=json.dumps(result)
        for secret in ('private-user','secret-password','395634','900001','SELECT','host-name','0x7a222222','stack frames','D:'):
            self.assertNotIn(secret,serialized)
        body='Exception caught: EXCEPTION_ACCESS_VIOLATION\nProgram: '+private+'\n'+private
        result=stage.admit(self.raw(body),5256,self.policy)
        self.assertEqual(result['source_matches'][0]['exception_enum'],'EXCEPTION_ACCESS_VIOLATION')
        self.assertFalse(result['raw_titles_controls_or_stacks_exported'])

    def test_wrong_source_expression_line_unknown_exception_and_timeouts(self):
        point=self.policy['points']['ring_buffer_unset']
        for filename,expression,line in (('foreign.hpp','!m_base',point['lines'][0]),
                ('ring.hpp','arbitrary-private-expression',point['lines'][0]),('ring.hpp','!m_base',99999)):
            text=f'Assertion failed\nFile: D:\\private\\{filename}\nLine: {line}\nExpression: {expression}\n'
            result=stage.admit(self.raw(text),5256,self.policy)
            self.assertEqual(result['source_matches'][0]['kind'],'source_assertion_unknown')
            self.assertNotIn(expression,json.dumps(result))
        result=stage.admit(self.raw('Exception caught: private-numeric-code\nsecret'),5256,self.policy)
        self.assertEqual(result['source_matches'][0]['exception_enum'],'unknown_exception')
        for status in ('timeout','truncated','owner_changed'):
            value=self.raw('Exception caught: EXCEPTION_ACCESS_VIOLATION',status)
            if status=='truncated':value['text_bound_reached']=True
            result=stage.admit(value,5256,self.policy)
            self.assertEqual(result['source_matches'],[])
        for key,value in (('pid',5257),('pid',True),('deadline_reached',1),('owner_changed_count',True),('rows',[])):
            bad=self.raw('secret');bad[key]=value
            if key=='rows':bad['owner_changed_count']=1
            with self.subTest(key=key),self.assertRaises(ValueError):stage.admit(bad,5256,self.policy)
        for key,value in (('pid',5257),('pid',True),('top_level',1),('text_status',[]),('text','x'*32769),('control_id',True)):
            bad=self.raw('secret');bad['rows'][1][key]=value
            with self.subTest(key=key),self.assertRaises(ValueError):stage.admit(bad,5256,self.policy)
        for key,value in (('class_name','Button'),('class_name','Edit'),('control_id',65535),('top_level',True)):
            bad=self.raw('Exception caught: EXCEPTION_ACCESS_VIOLATION');bad['rows'][1][key]=value
            with self.subTest(key=key,value=value):self.assertEqual(stage.admit(bad,5256,self.policy)['source_matches'],[])
        bad=self.raw('secret');bad['top_level_enumeration_completed']=False
        with self.assertRaisesRegex(ValueError,'enumeration_failed'):stage.admit(bad,5256,self.policy)
        bad['deadline_reached']=True
        self.assertTrue(stage.admit(bad,5256,self.policy)['deadline_reached'])

    def test_observer_is_bounded_private_and_uses_only_read_messages(self):
        reader=(stage.HERE/'windows/db_modal_observer.cs').read_text()
        for fragment in ('EnumWindows','EnumChildWindows','GetWindowThreadProcessId','0x000e','0x000d',
                         '65536','32768','8000','100,out','owner_changed'):
            self.assertIn(fragment,reader)
        for forbidden in ('WM_COMMAND','PostMessage','SetWindowText','EndDialog','CloseWindow','SendInput'):
            self.assertNotIn(forbidden,reader)
        raw=self.raw('Exception caught: EXCEPTION_ACCESS_VIOLATION\nprivate dialog text')
        def execute(argv,**kwargs):
            self.assertEqual(kwargs['stderr'],subprocess.DEVNULL)
            self.assertEqual(kwargs['timeout'],30)
            self.assertIn('[CohDbModalReader]::Observe(5256)',argv[-1])
            self.assertNotIn('private dialog text',argv[-1])
            kwargs['stdout'].write(json.dumps(raw).encode());kwargs['stdout'].flush()
            return mock.Mock(returncode=0)
        # Actual HEAD ownership of these new inputs is checked separately at
        # runtime; emulate exact blobs here without running a Windows process.
        with tempfile.TemporaryDirectory() as name, \
             mock.patch.object(stage.subprocess,'check_output',side_effect=lambda argv,**kw:(ROOT/argv[-1][len('HEAD:'):]).read_bytes()), \
             mock.patch.object(stage.subprocess,'run',side_effect=execute):
            result=stage.observe(ROOT,5256,Path(name))
        self.assertEqual(result['source_matches'][0]['exception_enum'],'EXCEPTION_ACCESS_VIOLATION')
        self.assertEqual(len(result['classifier_source_sha256']),2)
        self.assertEqual(result['original_source_sha256'],dict(stage.SOURCE_PINS,**{stage.MACRO_FORWARD_PATH:stage.MACRO_FORWARD_SHA}))
        self.assertEqual(result['source_call_site_count'],78)
        self.assertEqual(result['compiled_variant_pe_sha256'],stage.PE_SHA)

    @unittest.skipUnless(os.name=='nt','Windows-only new API compilation and benign owned self-observation')
    def test_windows_actual_api_preflight_before_service_start(self):
        with tempfile.TemporaryDirectory(prefix='coh-modal-preflight-') as name:
            result=stage.preflight(ROOT,Path(name))
        self.assertTrue(result['passed']);self.assertTrue(result['owned_cleanup_complete'])
        self.assertFalse(result['auth_or_sql_services_started'])
        self.assertEqual(result['benign_self_observation']['pid'],result['owned_pid'])
        self.assertTrue(result['benign_self_observation']['top_level_enumeration_completed'])
        self.assertFalse(result['benign_self_observation']['raw_titles_controls_or_stacks_exported'])

    def test_preflight_owned_child_cleanup_on_timeout_or_generation_refusal(self):
        for failure in (None,'timeout','generation','job_stop'):
            with self.subTest(failure=failure),tempfile.TemporaryDirectory() as name:
                child=mock.Mock(pid=5256,returncode=0);job=mock.Mock(handle=123)
                if failure=='timeout':child.wait.side_effect=subprocess.TimeoutExpired('private-preflight',30)
                def stop(process):job.handle=None;return failure!='job_stop'
                job.stop.side_effect=stop
                def popen(argv,**kwargs):
                    self.assertIn('Observe($PID)',argv[-1]);self.assertEqual(kwargs['stderr'],subprocess.DEVNULL)
                    value={'before':639278690324197929,'after':639278690324197930 if failure=='generation' else 639278690324197929,
                        'observation':self.raw('unrecognized private benign text')}
                    kwargs['stdout'].write(json.dumps(value).encode());kwargs['stdout'].flush()
                    return child
                with mock.patch.object(login,'OwnedJob',return_value=job), \
                     mock.patch.object(stage.subprocess,'Popen',side_effect=popen), \
                     mock.patch.object(stage.subprocess,'check_output',side_effect=lambda argv,**kw:(ROOT/argv[-1][len('HEAD:'):]).read_bytes()):
                    if failure is None:
                        result=stage.preflight(ROOT,Path(name));self.assertTrue(result['owned_cleanup_complete'])
                        self.assertNotIn('unrecognized private benign text',json.dumps(result))
                    else:
                        with self.assertRaises((ValueError,subprocess.TimeoutExpired)):stage.preflight(ROOT,Path(name))
                job.stop.assert_called_once_with(child)

    def test_exact_pe_variants_and_location_only_sites_are_distinct(self):
        self.assertEqual(len(self.policy['sites']),78);self.assertEqual(len(self.policy['variants']),4)
        for key,variant in self.policy['variants'].items():
            point=self.policy['points'][key]
            text='Assertion failed\nFile: D:\\private\\'+point['file']+'\nLine: '+str(point['lines'][0])+'\nExpression: '+variant+'\n'
            match=stage.admit(self.raw(text),5256,self.policy)['source_matches'][0]
            self.assertEqual(match['assertion_enum'],key)
            self.assertTrue(match['source_call_site_verified']);self.assertTrue(match['compiled_expression_variant_match'])
            self.assertFalse(match['source_expression_match'])
        key,site=next((key,site) for key,site in self.policy['sites'].items() if site['legacy'] is None)
        prefix='Assertion failed\nFile: D:\\private\\'+site['file']+'\nLine: '+str(site['line'])+'\n'
        for suffix in ('Expression: private-unknown-expression\n',''):
            match=stage.admit(self.raw(prefix+suffix),5256,self.policy)['source_matches'][0]
            self.assertEqual(match['source_site_enum'],key);self.assertTrue(match['source_call_site_verified'])
            self.assertEqual(match['kind'],'source_assertion_unknown');self.assertEqual(match['assertion_enum'],'none')
            self.assertFalse(match['source_expression_match']);self.assertFalse(match['compiled_expression_variant_match'])
            self.assertFalse(match['source_assertion_line_verified'])
            self.assertNotIn('private-unknown-expression',json.dumps(match))
        ambiguous=copy.deepcopy(self.policy);ambiguous['sites']['fixed_duplicate_site']=dict(site)
        match=stage.admit(self.raw(prefix+'Expression: '+site['expression']),5256,ambiguous)['source_matches'][0]
        self.assertEqual(match['source_site_enum'],'ambiguous_source_site')
        self.assertFalse(match['source_call_site_verified']);self.assertFalse(match['source_expression_match'])

    def test_lexical_index_balances_multiline_arguments_comments_and_strings(self):
        text='''// assert(ignored)
/* assert(ignored_too) */
const char *s="assert(hidden)\\\" )";
const char *r=R"tag(assert(raw_hidden), ))tag";
assertmsg(
 foo("comma, )", nested(1,2)) /* comment ) , */ && values[fn(3,4)],
 "private, message)");
assert(a); assert(b);
'''
        calls=stage.assertion_calls(text)
        self.assertEqual(len(calls),3)
        self.assertEqual(calls[0]['line'],5)
        self.assertIn('foo("comma, )", nested(1,2))',calls[0]['expression'])
        self.assertNotIn('comment',calls[0]['expression'])
        self.assertEqual(calls[1]['line'],calls[2]['line'])
        for bad in ('assert(unclosed(','assertmsg(a, "unterminated)','/* unterminated','assert(a[0);'):
            self.assertIsNone(stage.assertion_calls(bad))

    def test_stringized_spacing_preserves_literals_and_operator_boundaries(self):
        for line,original,changed in (
                (709,'!"This has already been freed!"','!"This has already be en freed!"'),
                (726,'!"Trying to free a chunk of memory that is not part of this pool!"',
                    '!"Trying to free a chunk of memory that is not pa rt of this pool!"')):
            prefix='Assertion failed\nFile: D:\\private\\MemoryPool.c\nLine: '+str(line)+'\nExpression: '
            good=stage.admit(self.raw(prefix+original),5256,self.policy)['source_matches'][0]
            self.assertEqual(good['kind'],'source_assertion');self.assertTrue(good['source_expression_match'])
            bad=stage.admit(self.raw(prefix+changed),5256,self.policy)['source_matches'][0]
            self.assertTrue(bad['source_call_site_verified']);self.assertEqual(bad['source_site_enum'],good['source_site_enum'])
            self.assertEqual(bad['kind'],'source_assertion_unknown');self.assertFalse(bad['source_expression_match'])
            self.assertFalse(bad['compiled_expression_variant_match']);self.assertNotIn(changed,json.dumps(bad))
        self.assertEqual(stage.normalized(' x  +\n ++y /* removed */ '),'x + ++y')
        self.assertNotEqual(stage.normalized('x + ++y'),stage.normalized('x++ + y'))
        self.assertEqual(stage.normalized(' x/* removed */  + y '),'x + y')
        for expression in ('!"a  b\\\" c"',"' '", 'R"tag(a  b, ")tag"'):
            self.assertEqual(stage.normalized('  '+expression+'\n'),expression)
            if '  ' in expression:
                self.assertNotEqual(stage.normalized(expression),stage.normalized(expression.replace('  ',' ')))

    def test_source_forward_and_compiled_variants_require_exact_pins(self):
        for constant,message in (('PE_ARCHIVE_SHA','compiled_archive_identity'),
                ('PE_SHA','compiled_binary_identity'),('MACRO_FORWARD_SHA','macro_forward_source_identity')):
            with self.subTest(constant=constant),mock.patch.object(stage,constant,'0'*64):
                with self.assertRaisesRegex(ValueError,message):stage.policy(ROOT)
        with mock.patch.object(stage,'PE_VARIANTS',dict(stage.PE_VARIANTS,unretained='private-unretained-expression')):
            with self.assertRaisesRegex(ValueError,'compiled_variant_not_present'):stage.policy(ROOT)


if __name__=='__main__':unittest.main()
