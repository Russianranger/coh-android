"""Execute shipped sidebar readiness and controller edges against host UI adapters."""
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[3]
JAVA = ROOT/'android/interactive/src/main/java/io/github/russianranger/cohclientinteractive'
sys.path.insert(0, str(Path(__file__).parent))
from test_storage_ui import production_method

HOST = r'''
import java.util.*;
import io.github.russianranger.cohclientinteractive.ClientInput;
class SystemClock {static long now=100;static long uptimeMillis(){return now;}}
class Toast {static final int LENGTH_SHORT=0;static Toast makeText(Object owner,String text,int length){return new Toast();}void show(){}}
class Button {
    String label;boolean enabled=true,pressed;Runnable click;
    Button(String value,Runnable action){label=value;click=action;}
    void setEnabled(boolean value){enabled=value;}void setPressed(boolean value){pressed=value;}
    void tap(){if(enabled)click.run();}
}
class LinearLayout {
    List<Object> children=new ArrayList<>();LinearLayout(Object owner){}
    void addView(Object value){children.add(value);}void addView(Object value,Object params){children.add(value);}
    static class LayoutParams {LayoutParams(int x,int y,int weight){}}
}
class InputDevice {static final int SOURCE_GAMEPAD=0x401;}
class KeyEvent {
    static final int ACTION_DOWN=0,ACTION_UP=1;
    static final int KEYCODE_DPAD_LEFT=21,KEYCODE_DPAD_UP=19,KEYCODE_DPAD_RIGHT=22,KEYCODE_DPAD_DOWN=20;
    static final int KEYCODE_ESCAPE=111,KEYCODE_ENTER=66,KEYCODE_NUMPAD_ENTER=160,KEYCODE_TAB=61;
    static final int KEYCODE_DEL=67,KEYCODE_FORWARD_DEL=112,KEYCODE_SHIFT_LEFT=59,KEYCODE_SHIFT_RIGHT=60;
    static final int KEYCODE_CTRL_LEFT=113,KEYCODE_CTRL_RIGHT=114,KEYCODE_ALT_LEFT=57,KEYCODE_ALT_RIGHT=58;
    static final int KEYCODE_BUTTON_A=96,KEYCODE_BUTTON_B=97,KEYCODE_BUTTON_X=99;
    static final int KEYCODE_BUTTON_L1=102,KEYCODE_BUTTON_R1=103,KEYCODE_BUTTON_THUMBL=106,KEYCODE_BUTTON_START=108;
    final int code,action,repeat,source,unicode;
    KeyEvent(int code,int action,int repeat,int source,int unicode){this.code=code;this.action=action;this.repeat=repeat;this.source=source;this.unicode=unicode;}
    int getKeyCode(){return code;}int getAction(){return action;}int getRepeatCount(){return repeat;}
    int getSource(){return source;}int getUnicodeChar(){return unicode;}
}
class BaseActivity {
    boolean focus=true;boolean hasWindowFocus(){return focus;}
    public boolean dispatchKeyEvent(KeyEvent event){return false;}
    public void onWindowFocusChanged(boolean value){focus=value;}
    public void onReleaseAll(String session){}
}
class ClientService {
    static class State {
        boolean busy=true,inputReady=true,finishing,blocked,characterSaved,canSaveLogout=true;
        String session="0123456789abcdef0123456789abcdef",sessionPhase="connected";
        long movementDeadlineUptimeMillis=10000,saveDeadlineUptimeMillis=15000;
    }
    boolean allow=true,pending,reject,enterReject;
    int enterRequests,cancellations,orderedReleases;
    List<ClientInput.PerformanceCommand> commands=new ArrayList<>();
    List<String> keys=new ArrayList<>();Set<Integer> held=new LinkedHashSet<>();
    boolean canSendPerformanceCommand(){return allow&&!pending;}
    boolean isPerformanceCommandPending(){return pending;}
    boolean requestPerformanceCommand(ClientInput.PerformanceCommand command){
        if(!canSendPerformanceCommand()||reject)return false;commands.add(command);pending=true;return true;
    }
    boolean requestEnter(){if(pending||enterReject)return false;++enterRequests;return true;}
    boolean sendKey(String session,int key,boolean down){
        if(pending)return false;keys.add(key+":"+down);if(down)held.add(key);else held.remove(key);return true;
    }
    void releaseAllInputs(String session){++cancellations;pending=false;for(int key:held)keys.add(key+":false");held.clear();}
    void releaseInput(String session){++orderedReleases;}
    boolean canCaptureContact(){return !pending;}boolean canOpenTaskContact(){return !pending;}
    boolean canCaptureTask(boolean done){return !pending;}boolean canCompleteAcceptedTask(){return !pending;}
    boolean canRequestSaveLogout(){return !pending;}
}
class Surface {
    final HostActivity ui;boolean enabled=true;int buttons;
    Surface(HostActivity value){ui=value;}
    void setControllerButtons(int value){buttons=value;}
    void setInputEnabled(boolean value){if(enabled&&!value)releaseInput();enabled=value;}
    void releaseInput(){ui.onReleaseAll(ui.shownSession);}
}
class HostActivity extends BaseActivity {
    ClientService service=new ClientService();ClientService.State state=new ClientService.State();
    Surface display=new Surface(this);
    Button enterKey,showFps,fps10,fps30,typeText;
    Button captureContact=new Button("",()->{}),openTaskContact=new Button("",()->{}),captureAcceptedTask=new Button("",()->{});
    Button completeTask=new Button("",()->{}),captureCompletedTask=new Button("",()->{}),saveLogout=new Button("",()->{});
    boolean inputActive=true,textDialogVisible,movementSuppressed,deadlineMovementSuppressed;
    String shownSession=state.session;float rightX,rightY;int textRequests;
    final ClientInput.KeyOwners heldKeys=new ClientInput.KeyOwners();
    final ClientInput.WalkingKeys walkingKeys=new ClientInput.WalkingKeys();
    final ClientInput.StartButton startButton=new ClientInput.StartButton();
    final Set<Integer> heldButtons=new HashSet<>();
    final List<Button> movementButtons=new ArrayList<>();
    Button button(String name,Runnable action){return new Button(name,action);}
    void showTextInput(){++textRequests;}
    HostActivity(){LinearLayout controls=new LinearLayout(this);BUILD_CONTROLS}
    PRODUCTION_METHODS
    void refresh(){refreshDeadlineControls();}
    void command(ClientInput.PerformanceCommand value){sendPerformanceCommand(value);}
    void enter(){sendEnter();}
    void holdKey(){heldKeys.press(21,'w',this::sendOwnedKey);}
    void key(int code,int action,int repeat){dispatchKeyEvent(new KeyEvent(code,action,repeat,InputDevice.SOURCE_GAMEPAD,0));}
}
public class SidebarHost {
    static void need(boolean value){if(!value)throw new AssertionError();}
    static void noCommands(HostActivity ui){need(ui.service==null||ui.service.commands.isEmpty());}
    public static void main(String[] args){
        HostActivity ui=new HostActivity();ui.refresh();
        switch(args[0]) {
        case "buttons":
            need(ui.enterKey.label.equals("Enter / Start")&&ui.showFps.label.equals("Show FPS"));
            need(ui.fps10.label.equals("10 FPS")&&ui.fps30.label.equals("30 FPS"));
            ui.showFps.tap();need(ui.service.commands.equals(Arrays.asList(ClientInput.PerformanceCommand.SHOW_FPS)));
            ui.service.pending=false;ui.refresh();ui.fps10.tap();
            ui.service.pending=false;ui.refresh();ui.fps30.tap();
            need(ui.service.commands.equals(Arrays.asList(ClientInput.PerformanceCommand.SHOW_FPS,
                ClientInput.PerformanceCommand.FPS_10,ClientInput.PerformanceCommand.FPS_30)));break;
        case "login":
            ui.state.sessionPhase="menu";ui.state.canSaveLogout=false;ui.refresh();
            need(!ui.showFps.enabled&&!ui.fps10.enabled&&!ui.fps30.enabled&&ui.enterKey.enabled);
            ui.command(ClientInput.PerformanceCommand.FPS_30);noCommands(ui);
            ui.enterKey.tap();need(ui.service.enterRequests==1);break;
        case "world_capability":
            ui.state.canSaveLogout=false;ui.refresh();need(ui.showFps.enabled&&ui.fps10.enabled&&ui.fps30.enabled);
            ui.state.sessionPhase="grounded";ui.refresh();need(ui.showFps.enabled);break;
        case "gates":
            for(int flag=0;flag<13;++flag){ui=new HostActivity();
                if(flag==0)ui.inputActive=false;if(flag==1)ui.state.inputReady=false;
                if(flag==2)ui.state.busy=false;if(flag==3)ui.state.finishing=true;
                if(flag==4)ui.state.blocked=true;if(flag==5)ui.state.characterSaved=true;
                if(flag==6)ui.shownSession="";if(flag==7)ui.shownSession="foreign";
                if(flag==8)ui.textDialogVisible=true;if(flag==9)ui.movementSuppressed=true;
                if(flag==10)ui.state.movementDeadlineUptimeMillis=SystemClock.now;
                if(flag==11)ui.focus=false;if(flag==12)ui.service=null;
                ui.refresh();need(!ui.showFps.enabled&&!ui.fps10.enabled&&!ui.fps30.enabled&&!ui.enterKey.enabled);
                ui.command(ClientInput.PerformanceCommand.FPS_30);ui.enter();noCommands(ui);
            }break;
        case "native_rejection":
            ui.service.allow=false;ui.refresh();need(!ui.showFps.enabled);ui.command(ClientInput.PerformanceCommand.FPS_30);noCommands(ui);
            ui.service.allow=true;ui.service.reject=true;ui.command(ClientInput.PerformanceCommand.FPS_30);noCommands(ui);
            ui.command(null);noCommands(ui);break;
        case "owned_command": {
            ui.holdKey();ui.heldButtons.add(KeyEvent.KEYCODE_BUTTON_A);
            ui.command(ClientInput.PerformanceCommand.FPS_30);need(ui.service.pending&&ui.service.held.isEmpty());
            need(!ui.heldKeys.contains(21)&&ui.heldButtons.isEmpty());
            int discarded=ui.service.cancellations;
            ui.refresh();need(ui.service.pending&&ui.service.cancellations==discarded);
            need(!ui.showFps.enabled&&!ui.fps10.enabled&&!ui.fps30.enabled&&!ui.enterKey.enabled&&!ui.typeText.enabled);
            ui.command(ClientInput.PerformanceCommand.FPS_10);ui.enter();
            need(ui.service.commands.size()==1&&ui.service.enterRequests==0);
            need(ui.dispatchKeyEvent(new KeyEvent(KeyEvent.KEYCODE_ENTER,0,0,0x101,0))==false);
            ui.service.pending=false;ui.refresh();need(ui.showFps.enabled&&ui.enterKey.enabled);break;
        }
        case "focus_cancel":
            ui.command(ClientInput.PerformanceCommand.FPS_30);need(ui.service.pending);
            ui.onWindowFocusChanged(false);need(!ui.service.pending&&!ui.showFps.enabled&&!ui.enterKey.enabled);
            ui.onWindowFocusChanged(true);ui.refresh();need(ui.showFps.enabled);break;
        case "start_once":
            ui.key(KeyEvent.KEYCODE_BUTTON_START,0,0);need(ui.service.enterRequests==1);
            ui.key(KeyEvent.KEYCODE_BUTTON_START,0,0);ui.key(KeyEvent.KEYCODE_BUTTON_START,0,1);
            ui.key(KeyEvent.KEYCODE_BUTTON_START,0,2);need(ui.service.enterRequests==1);
            ui.key(KeyEvent.KEYCODE_BUTTON_START,1,0);need(ui.service.enterRequests==1);
            ui.key(KeyEvent.KEYCODE_BUTTON_START,0,0);need(ui.service.enterRequests==2);break;
        case "start_login":
            ui.state.sessionPhase="menu";ui.state.canSaveLogout=false;ui.refresh();
            ui.key(KeyEvent.KEYCODE_BUTTON_START,0,0);ui.key(KeyEvent.KEYCODE_BUTTON_START,1,0);
            need(ui.service.enterRequests==1);noCommands(ui);break;
        case "start_transition":
            ui.inputActive=false;ui.key(KeyEvent.KEYCODE_BUTTON_START,0,0);
            ui.inputActive=true;ui.key(KeyEvent.KEYCODE_BUTTON_START,0,1);need(ui.service.enterRequests==0);
            ui.key(KeyEvent.KEYCODE_BUTTON_START,1,0);ui.key(KeyEvent.KEYCODE_BUTTON_START,0,0);
            need(ui.service.enterRequests==1);
            ui.onWindowFocusChanged(false);ui.onWindowFocusChanged(true);
            ui.key(KeyEvent.KEYCODE_BUTTON_START,0,3);need(ui.service.enterRequests==1);
            ui.key(KeyEvent.KEYCODE_BUTTON_START,1,0);ui.key(KeyEvent.KEYCODE_BUTTON_START,0,0);
            need(ui.service.enterRequests==2);break;
        case "other_controls":
            ui.key(KeyEvent.KEYCODE_BUTTON_A,0,0);need(ui.display.buttons==1);
            ui.key(KeyEvent.KEYCODE_BUTTON_L1,0,0);need(ui.display.buttons==5);
            ui.key(KeyEvent.KEYCODE_BUTTON_A,1,0);need(ui.display.buttons==4);
            ui.key(KeyEvent.KEYCODE_BUTTON_L1,1,0);need(ui.display.buttons==0);
            ui.key(KeyEvent.KEYCODE_BUTTON_B,0,0);ui.key(KeyEvent.KEYCODE_BUTTON_B,1,0);
            ui.key(KeyEvent.KEYCODE_BUTTON_X,0,0);ui.key(KeyEvent.KEYCODE_BUTTON_X,1,0);
            need(ui.service.keys.equals(Arrays.asList("65307:true","65307:false","32:true","32:false")));
            ui.key(KeyEvent.KEYCODE_BUTTON_THUMBL,0,0);need(ui.textRequests==1);break;
        case "keyboard_enter":
            ui.dispatchKeyEvent(new KeyEvent(KeyEvent.KEYCODE_ENTER,0,0,0x101,0));
            ui.dispatchKeyEvent(new KeyEvent(KeyEvent.KEYCODE_ENTER,1,0,0x101,0));
            need(ui.service.keys.equals(Arrays.asList("65293:true","65293:false")));
            need(ui.service.enterRequests==0);break;
        case "allowlist":
            need(ClientInput.PerformanceCommand.values().length==3);
            need(ClientInput.PerformanceCommand.SHOW_FPS.safeName.equals("show_fps"));
            need(ClientInput.PerformanceCommand.FPS_10.safeName.equals("cap_10"));
            need(ClientInput.PerformanceCommand.FPS_30.safeName.equals("cap_30"));
            ClientInput.StartButton start=new ClientInput.StartButton();need(!start.press(1)&&!start.press(0));
            start.release();need(start.press(0)&&!start.press(0));start.reset();need(!start.press(2));break;
        default:throw new AssertionError("Unknown sidebar scenario");
        }
    }
}
'''


class SidebarCommandTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        text = (JAVA/'ClientActivity.java').read_text()
        methods = [production_method(text, signature) for signature in (
            'private boolean commandInputBusy(', 'private boolean gameInputOpen(',
            'private boolean ownedInputOpen(', 'private boolean canSendPerformanceCommand(',
            'private void refreshPerformanceControls(', 'private void sendPerformanceCommand(',
            'private void sendEnter(', 'private boolean canWalk(', 'private boolean movementWindowOpen(',
            'private void refreshDeadlineControls(', 'private void refreshMovementControls(',
            'private void pressKey(', 'private void releaseKey(', 'private boolean sendOwnedKey(',
            'private void releaseRemoteInputs(', 'private void resetLocalInputs(',
            'private void releaseControls()', 'private void releaseControls(boolean',
            '@Override public boolean dispatchKeyEvent(', '@Override public void onWindowFocusChanged(',
            '@Override public void onReleaseAll(String session)')]
        start = text.index('        typeText=button("Send text / L3"')
        end = text.index('        controls.addView(text("Atlas movement', start)
        cls.directory = tempfile.TemporaryDirectory(prefix='coh-sidebar-ui-')
        cls.path = Path(cls.directory.name)
        host = cls.path/'SidebarHost.java'
        host.write_text(HOST.replace('PRODUCTION_METHODS', '\n'.join(methods))
            .replace('BUILD_CONTROLS', text[start:end]))
        subprocess.run(['java', '-m', 'jdk.compiler/com.sun.tools.javac.Main', '--release', '8',
            '-d', str(cls.path), str(JAVA/'ClientInput.java'), str(host)],
            check=True, capture_output=True, text=True)

    @classmethod
    def tearDownClass(cls):
        cls.directory.cleanup()

    def scenario(self, name):
        subprocess.run(['java', '-cp', str(self.path), 'SidebarHost', name],
            check=True, capture_output=True, text=True, timeout=10)

    def test_sidebar_buttons_request_only_the_three_fixed_native_actions(self): self.scenario('buttons')
    def test_login_has_enter_without_performance_command_or_credential_submission(self): self.scenario('login')
    def test_connected_and_grounded_performance_actions_use_the_runtime_capability(self): self.scenario('world_capability')
    def test_unready_foreign_saved_paused_dialog_and_expired_sessions_cannot_send(self): self.scenario('gates')
    def test_invalid_and_rejected_requests_cannot_queue_commands(self): self.scenario('native_rejection')
    def test_pending_command_releases_old_input_and_survives_its_automatic_surface_disable(self): self.scenario('owned_command')
    def test_explicit_focus_loss_cancels_the_command_and_allows_a_fresh_request(self): self.scenario('focus_cancel')
    def test_short_start_press_queues_one_enter_and_repeats_or_release_do_not_duplicate_it(self): self.scenario('start_once')
    def test_start_can_submit_the_native_login_field_without_typing_a_command(self): self.scenario('start_login')
    def test_held_start_cannot_submit_after_input_readiness_or_focus_changes(self): self.scenario('start_transition')
    def test_click_shoulders_escape_jump_and_text_controller_mappings_are_preserved(self): self.scenario('other_controls')
    def test_hardware_keyboard_enter_preserves_ordinary_key_ownership(self): self.scenario('keyboard_enter')
    def test_enum_allowlist_and_start_latch_reject_replayed_edges(self): self.scenario('allowlist')


if __name__ == '__main__':
    unittest.main()
