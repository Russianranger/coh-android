"""Export and missing-process behavior for measured combined process samples."""
import copy,json,unittest
from fragment_interop_emulator_check import process_set_snapshot


def sample():
    rows=[dict(pid=10,start_ticks=1000,role='ANDROID_APP_AND_NATIVE_CLIENT',rss_bytes=4096,pss_bytes=2048,identity_stable=True),
          dict(pid=20,start_ticks=2000,role='WINE_SERVERS',rss_bytes=8192,pss_bytes=4096,identity_stable=True),
          dict(pid=30,start_ticks=3000,role='POSTGRESQL',rss_bytes=12288,pss_bytes=6144,identity_stable=True)]
    return dict(schema='coh-same-uid-process-memory-v1',begin_elapsed_ms=1,end_elapsed_ms=10,sample_window_ms=9,
        uid=1000,self_pid=10,process_limit=32,process_count=3,wine_processes=1,postgresql_processes=1,
        incomplete_process_metrics=0,unreadable_status_count=0,samples=1,scan_complete=True,expected_roles_observed=True,
        server_process_expected=True,processes=rows,observed_rss_sum_bytes=24576,observed_pss_sum_bytes=12288,
        total_rss_bytes=24576,total_pss_bytes=12288,sampled_peak_total_rss_bytes=24576,sampled_peak_total_pss_bytes=12288,
        atomic_snapshot=False,rss_sum_includes_repeated_shared_pages=True,pss_is_proportional=True)


class ProcessSetContract(unittest.TestCase):
    def test_known_group_and_unknown_before_observation(self):
        value=sample();self.assertIs(process_set_snapshot(value),value)
        process_set_snapshot(dict(schema=value['schema'],status='not_sampled',total_rss_bytes=None,total_pss_bytes=None))

    def test_partial_pss_stays_null_and_peak_remains_historical(self):
        value=sample();value['processes'][1]['pss_bytes']=None;value.update(observed_pss_sum_bytes=8192,total_pss_bytes=None,incomplete_process_metrics=1)
        process_set_snapshot(value)
        value['total_pss_bytes']=8192
        with self.assertRaises(ValueError):process_set_snapshot(value)

    def test_duplicates_stale_private_data_and_invented_totals_refuse(self):
        for change in ('duplicate','stale','private','wrong_sum','false_complete','false_scope','negative','fractional'):
            value=sample()
            if change=='duplicate':value['processes'][1]['pid']=10
            if change=='stale':value['processes'][1]['identity_stable']=False
            if change=='private':value['processes'][1]['cmdline']='private'
            if change=='wrong_sum':value['total_pss_bytes']+=1
            if change=='false_complete':value['scan_complete']=False
            if change=='false_scope':value['rss_sum_includes_repeated_shared_pages']=False
            if change=='negative':value['processes'][1]['pss_bytes']=-1
            if change=='fractional':value['processes'][1]['pss_bytes']=4.0
            with self.subTest(change=change),self.assertRaises(ValueError):process_set_snapshot(value)

    def test_bounded_large_export_is_below_existing_phase_reader_limit(self):
        value=sample();value['processes']=[dict(value['processes'][0],pid=i+1,role='OTHER_APP_UID',rss_bytes=1<<50,pss_bytes=1<<50) for i in range(32)]
        value['processes'][9]['role']='ANDROID_APP_AND_NATIVE_CLIENT';value.update(process_count=32,wine_processes=0,postgresql_processes=0,expected_roles_observed=True,server_process_expected=False)
        for metric in ('rss','pss'):
            value['observed_'+metric+'_sum_bytes']=32<<50;value['total_'+metric+'_bytes']=32<<50;value['sampled_peak_total_'+metric+'_bytes']=32<<50
        process_set_snapshot(value);self.assertLess(len(json.dumps(value,indent=2).encode()),12*1024)

    def test_compact_64_complete_unknown_and_overflow(self):
        value=sample();value['process_limit']=64
        fields=['pid','start_ticks','role','rss_bytes','pss_bytes','identity_stable','unavailable','zombie_no_address_space']
        value['process_row_fields']=fields
        value['processes']=[[i+1,1<<50,'ANDROID_APP_AND_NATIVE_CLIENT' if i==9 else 'OTHER_APP_UID',1<<50,1<<50,True,0,False] for i in range(64)]
        value.update(process_count=64,wine_processes=0,postgresql_processes=0,expected_roles_observed=True,server_process_expected=False)
        for metric in ('rss','pss'):
            value['observed_'+metric+'_sum_bytes']=64<<50;value['total_'+metric+'_bytes']=64<<50;value['sampled_peak_total_'+metric+'_bytes']=64<<50
        process_set_snapshot(value)
        # Leave more than 10 KiB for all nine existing phase records and headers.
        self.assertLess(len(json.dumps(value,indent=2).encode()),14*1024)
        unknown=copy.deepcopy(value)
        for row in unknown['processes']:row[3:8]=[None,None,True,5,False]
        for metric in ('rss','pss'):unknown['observed_'+metric+'_sum_bytes']=0;unknown['total_'+metric+'_bytes']=None
        unknown['incomplete_process_metrics']=64;unknown['unavailable_codes']={'1':'RSS_FIELD_UNAVAILABLE','4':'PSS_READ_FAILED'}
        process_set_snapshot(unknown);self.assertLess(len(json.dumps(unknown,indent=2).encode()),14*1024)
        overflow=copy.deepcopy(value);overflow['scan_complete']=False
        overflow['omitted_same_uid_processes']=1;overflow['total_rss_bytes']=overflow['total_pss_bytes']=None
        process_set_snapshot(overflow)
        for change in ('width','legend','status','zombie'):
            invalid=copy.deepcopy(value)
            if change=='width':invalid['processes'][0].pop()
            if change=='legend':invalid['process_row_fields'][1]='private'
            if change=='status':invalid['processes'][0][6]=True
            if change=='zombie':invalid['processes'][0][7]=True
            with self.subTest(change=change),self.assertRaises(ValueError):process_set_snapshot(invalid)

    def aggregated(self):
        value=sample();value['process_limit']=64
        roles=('ANDROID_APP_AND_NATIVE_CLIENT','WINE_SERVERS','POSTGRESQL','OTHER_APP_UID')
        counts=(1,9,80,1);units=(4096,8192,12288,4096)
        categories={}
        for role,count,rss in zip(roles,counts,units):
            categories[role]=dict(process_count=count,observed_rss_bytes=count*rss,observed_pss_bytes=count*rss//2,
                rss_bytes=count*rss,pss_bytes=count*rss//2,rss_complete=True,pss_complete=True,
                missing_rss_processes=0,missing_pss_processes=0,zombie_processes=0,reason_flags=0)
        total=dict(categories[roles[0]])
        for key in ('process_count','observed_rss_bytes','observed_pss_bytes','rss_bytes','pss_bytes'):
            total[key]=sum(v[key] for v in categories.values())
        value['aggregation']=dict(scope='all_scanned_same_uid_processes',directory_entry_limit=8192,directory_entries_scanned=93,
            role_unclassified_processes=0,total=total,categories=categories)
        value['detail_rows_omitted']=value['omitted_same_uid_processes']=88
        for metric in ('rss','pss'):
            value['observed_'+metric+'_sum_bytes']=total['observed_'+metric+'_bytes']
            value['total_'+metric+'_bytes']=value['sampled_peak_total_'+metric+'_bytes']=total[metric+'_bytes']
        return value

    def test_streaming_totals_are_independent_of_optional_detail(self):
        value=self.aggregated();process_set_snapshot(value)
        self.assertGreater(value['total_pss_bytes'],sum(row['pss_bytes'] for row in value['processes']))
        legacy=copy.deepcopy(value);del legacy['aggregation']
        with self.assertRaises(ValueError):process_set_snapshot(legacy)
        for change in ('omission','partition','complete','sum','reason'):
            invalid=copy.deepcopy(value)
            if change=='omission':invalid['detail_rows_omitted']=0
            if change=='partition':invalid['aggregation']['total']['process_count']-=1
            if change=='complete':invalid['aggregation']['total']['rss_complete']=False
            if change=='sum':invalid['observed_pss_sum_bytes']-=1
            if change=='reason':invalid['aggregation']['total']['reason_flags']=1
            with self.subTest(change=change),self.assertRaises(ValueError):process_set_snapshot(invalid)

    def test_missing_metric_outside_details_and_scan_churn_are_explicit(self):
        value=self.aggregated();aggregate=value['aggregation'];other=aggregate['categories']['OTHER_APP_UID'];total=aggregate['total']
        missing=other['observed_rss_bytes'];other.update(observed_rss_bytes=0,rss_bytes=None,rss_complete=False,missing_rss_processes=1,reason_flags=2)
        total.update(observed_rss_bytes=total['observed_rss_bytes']-missing,rss_bytes=None,rss_complete=False,missing_rss_processes=1,reason_flags=2)
        value['observed_rss_sum_bytes']=total['observed_rss_bytes'];value['total_rss_bytes']=None
        process_set_snapshot(value)
        churn=self.aggregated();churn['scan_complete']=False
        for summary in [churn['aggregation']['total']]+list(churn['aggregation']['categories'].values()):
            summary.update(rss_bytes=None,pss_bytes=None,rss_complete=False,pss_complete=False,reason_flags=1)
        churn['total_rss_bytes']=churn['total_pss_bytes']=None;process_set_snapshot(churn)

    def test_large_aggregate_does_not_require_an_unbounded_process_list(self):
        value=self.aggregated();value['aggregation']['directory_entries_scanned']=8192
        category=value['aggregation']['categories']['POSTGRESQL'];category.update(process_count=8000,
            observed_rss_bytes=8000*12288,observed_pss_bytes=8000*6144,rss_bytes=8000*12288,pss_bytes=8000*6144)
        total=value['aggregation']['total']
        for key in ('process_count','observed_rss_bytes','observed_pss_bytes','rss_bytes','pss_bytes'):
            total[key]=sum(c[key] for c in value['aggregation']['categories'].values())
        value['detail_rows_omitted']=value['omitted_same_uid_processes']=total['process_count']-len(value['processes'])
        for metric in ('rss','pss'):
            value['observed_'+metric+'_sum_bytes']=total['observed_'+metric+'_bytes']
            value['total_'+metric+'_bytes']=value['sampled_peak_total_'+metric+'_bytes']=total[metric+'_bytes']
        process_set_snapshot(value);self.assertEqual(len(value['processes']),3)
        self.assertLess(len(json.dumps(value,indent=2).encode()),8*1024)


if __name__=='__main__':unittest.main()
