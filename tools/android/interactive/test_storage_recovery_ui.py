"""Execute shipped recovery and cancellation controls without a saved-profile bypass."""
from pathlib import Path
import subprocess
import tempfile
import unittest

from test_storage_ui import production_method

ROOT = Path(__file__).resolve().parents[3]
JAVA = ROOT / 'android/interactive/src/main/java/io/github/russianranger/cohclientinteractive'

HOST = r'''
import java.util.*;
class View {static final int VISIBLE=0,GONE=8;}
class TextView {String text="";void setText(String value){text=value;}}
class Button extends TextView {boolean enabled;int visibility=View.VISIBLE;void setEnabled(boolean value){enabled=value;}void setVisibility(int value){visibility=value;}}
class ClientRuntime {
    enum ProfileState {ABSENT,READY,PRESERVE}
    static boolean owned;
    static boolean operationInProgress(){return owned;}
}
class ClientService {
    static final String CREATE="coh.client.CREATE";
    static class State {
        boolean busy,storageBusy,reportExporting,blocked;
        ClientRuntime.ProfileState profileState=ClientRuntime.ProfileState.ABSENT;
        String profileNote="No saved character profile exists";
    }
}
class AlertDialog {
    interface Click {void click(Object dialog,int which);}
    static Builder shown;
    static class Builder {
        String title,message,positiveLabel,negativeLabel;Click positive,negative;
        Builder(Object owner){}
        Builder setTitle(String value){title=value;return this;}
        Builder setMessage(String value){message=value;return this;}
        Builder setNegativeButton(String label,Click action){negativeLabel=label;negative=action;return this;}
        Builder setPositiveButton(String label,Click action){positiveLabel=label;positive=action;return this;}
        void show(){shown=this;}
        void accept(){positive.click(this,1);}
        void cancel(){if(negative!=null)negative.click(this,0);}
    }
}
class HostActivity {
    ClientService service=new ClientService();ClientService.State state=new ClientService.State();
    boolean exporting;
    Button run=new Button(),createFresh=new Button(),stop=new Button();TextView profileStatus=new TextView();
    List<String> actions=new ArrayList<>();
    void request(String action){actions.add(action);}
    void setTextIfChanged(TextView view,String value){view.setText(value);}
    ACTIVITY_METHODS
    void refresh(){refreshProfileControls(state);refreshAbortControl(state);}
    void confirm(){confirmFreshProfile();}
}
public class StorageRecoveryUiHost {
    static void need(boolean value){if(!value)throw new AssertionError();}
    static void noLaunch(HostActivity ui){need(ui.actions.isEmpty());}
    public static void main(String[] args)throws Exception {
        HostActivity ui=new HostActivity();
        switch(args[0]) {
        case "absent":ui.refresh();need(ui.createFresh.visibility==View.VISIBLE&&ui.createFresh.enabled&&!ui.run.enabled);need(ui.profileStatus.text.equals(ui.state.profileNote));break;
        case "ready":ui.state.profileState=ClientRuntime.ProfileState.READY;ui.state.profileNote="Saved profile ready";ui.refresh();need(ui.run.enabled&&!ui.createFresh.enabled&&ui.createFresh.visibility==View.GONE);need(ui.profileStatus.text.equals("Saved profile ready"));break;
        case "preserve":ui.state.profileState=ClientRuntime.ProfileState.PRESERVE;ui.state.profileNote="Existing profile is incomplete; preserve it";ui.refresh();need(!ui.run.enabled&&!ui.createFresh.enabled&&ui.createFresh.visibility==View.GONE);need(ui.profileStatus.text.contains("preserve"));ui.confirm();need(AlertDialog.shown==null);noLaunch(ui);break;
        case "busy":for(int flag=0;flag<7;flag++){ui=new HostActivity();if(flag==0)ui.state.busy=true;if(flag==1)ui.state.storageBusy=true;if(flag==2)ui.state.reportExporting=true;if(flag==3)ui.state.blocked=true;if(flag==4)ui.exporting=true;if(flag==5)ClientRuntime.owned=true;if(flag==6)ui.service=null;ui.refresh();need(!ui.createFresh.enabled&&!ui.run.enabled);ui.confirm();need(AlertDialog.shown==null);noLaunch(ui);ClientRuntime.owned=false;}break;
        case "ready_busy":for(int flag=0;flag<4;flag++){ui=new HostActivity();ui.state.profileState=ClientRuntime.ProfileState.READY;if(flag==0)ui.state.busy=true;if(flag==1)ui.state.storageBusy=true;if(flag==2)ui.state.reportExporting=true;if(flag==3)ui.state.blocked=true;ui.refresh();need(!ui.run.enabled&&!ui.createFresh.enabled);}break;
        case "confirm":ui.confirm();need(AlertDialog.shown!=null);noLaunch(ui);need(AlertDialog.shown.message.contains("no saved profile")&&AlertDialog.shown.message.contains("do not restore")&&AlertDialog.shown.message.contains("current runtime and imported assets"));AlertDialog.shown.accept();need(ui.actions.equals(Arrays.asList(ClientService.CREATE)));break;
        case "cancel":ui.confirm();AlertDialog.shown.cancel();noLaunch(ui);break;
        case "stale_ready":ui.confirm();ui.state.profileState=ClientRuntime.ProfileState.READY;AlertDialog.shown.accept();noLaunch(ui);break;
        case "stale_preserve":ui.confirm();ui.state.profileState=ClientRuntime.ProfileState.PRESERVE;AlertDialog.shown.accept();noLaunch(ui);break;
        case "stale_owner":ui.confirm();ClientRuntime.owned=true;AlertDialog.shown.accept();noLaunch(ui);break;
        case "null":ui.state=null;ui.confirm();need(AlertDialog.shown==null);noLaunch(ui);break;
        case "abort":ui.refresh();need(!ui.stop.enabled);ui.state.storageBusy=true;ui.refresh();need(ui.stop.enabled&&ui.stop.text.equals("Cancel storage scan / cleanup"));ui.state.storageBusy=false;ui.state.busy=true;ui.refresh();need(ui.stop.enabled&&ui.stop.text.equals("Abort operation"));break;
        default:throw new AssertionError("Unknown recovery UI scenario");
        }
    }
}
'''


class StorageRecoveryUiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        activity = (JAVA / 'ClientActivity.java').read_text()
        methods = [production_method(activity, signature) for signature in (
            'private boolean profileIdle(', 'private boolean canCreateFreshProfile(',
            'private void refreshProfileControls(', 'private void confirmFreshProfile(',
            'private void refreshAbortControl(')]
        cls.folder = tempfile.TemporaryDirectory(prefix='coh-storage-recovery-ui-')
        cls.path = Path(cls.folder.name)
        source = cls.path / 'StorageRecoveryUiHost.java'
        source.write_text(HOST.replace('ACTIVITY_METHODS', '\n'.join(methods)))
        subprocess.run(['java', '-m', 'jdk.compiler/com.sun.tools.javac.Main', '--release', '8',
                        '-d', str(cls.path), str(source)], check=True, capture_output=True, text=True)

    @classmethod
    def tearDownClass(cls): cls.folder.cleanup()

    def scenario(self, name):
        subprocess.run(['java', '-cp', str(self.path), 'StorageRecoveryUiHost', name],
                       check=True, capture_output=True, text=True)

    def test_missing_profile_offers_only_explicit_creation(self): self.scenario('absent')
    def test_verified_profile_offers_only_reopen(self): self.scenario('ready')
    def test_partial_profile_stays_visible_and_cannot_be_overwritten(self): self.scenario('preserve')
    def test_creation_rejects_all_competing_operations_and_disconnection(self): self.scenario('busy')
    def test_reopen_rejects_busy_storage_export_and_cleanup_guard(self): self.scenario('ready_busy')
    def test_creation_requires_concrete_confirmation_and_uses_native_create_route(self): self.scenario('confirm')
    def test_cancel_confirmation_never_starts_creation(self): self.scenario('cancel')
    def test_saved_profile_appearing_during_confirmation_prevents_creation(self): self.scenario('stale_ready')
    def test_partial_profile_appearing_during_confirmation_prevents_creation(self): self.scenario('stale_preserve')
    def test_storage_owner_acquired_during_confirmation_prevents_creation(self): self.scenario('stale_owner')
    def test_unbound_state_cannot_show_creation_confirmation(self): self.scenario('null')
    def test_abort_remains_available_during_storage_and_gameplay_operations(self): self.scenario('abort')


if __name__ == '__main__': unittest.main()
