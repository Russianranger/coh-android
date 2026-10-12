"""Shipped Send Text dialog/service/runtime routes; native field effect is a device gate."""
from pathlib import Path
import subprocess
import tempfile
import unittest

from test_storage_ui import production_method
from test_client_sidebar_runtime import harness, JAVA, ZONING_JAVA

UI = r'''
import java.util.*;
import io.github.russianranger.cohclientinteractive.ClientInput;
class InputType {static int TYPE_CLASS_TEXT=1,TYPE_TEXT_FLAG_NO_SUGGESTIONS=2;}
class InputFilter {static class LengthFilter extends InputFilter {LengthFilter(int max){if(max!=32)throw new AssertionError();}}}
class View {static int IMPORTANT_FOR_AUTOFILL_NO_EXCLUDE_DESCENDANTS=8;}
class WindowManager {static class LayoutParams {static int SOFT_INPUT_STATE_ALWAYS_VISIBLE=4;}}
class Window {int mode;void setSoftInputMode(int value){mode=value;}}
class EditText {
 static EditText latest;String value="";boolean saved=true,autofill=true,focused;
 EditText(Object owner){latest=this;}void setSingleLine(boolean value){}void setInputType(int value){}
 void setImportantForAutofill(int value){autofill=false;}void setSaveEnabled(boolean value){saved=value;}
 void setFilters(InputFilter[] value){}void setText(String text){value=text;}void selectAll(){}
 String getText(){return value;}void requestFocus(){focused=true;}
}
class CheckBox {static CheckBox latest;boolean checked;CheckBox(Object owner){latest=this;}void setText(String value){}void setChecked(boolean value){checked=value;}boolean isChecked(){return checked;}}
class LinearLayout {static int VERTICAL=1;LinearLayout(Object owner){}void setOrientation(int value){}void addView(Object child){}}
class Toast {
 static int LENGTH_SHORT=0;static List<String> messages=new ArrayList<>();
 static Toast makeText(Object owner,String text,int length){messages.add(text);return new Toast();}void show(){}
}
class AlertDialog {
 interface Click {void click(AlertDialog dialog,int which);}interface Dismiss {void dismiss(AlertDialog dialog);}
 static AlertDialog latest;Click send;Dismiss dismiss;Window window=new Window();
 static class Builder {
  AlertDialog result=new AlertDialog();Builder(Object owner){}Builder setTitle(String value){return this;}Builder setMessage(String value){return this;}
  Builder setView(Object value){return this;}Builder setNegativeButton(String value,Click action){return this;}
  Builder setPositiveButton(String value,Click action){result.send=action;return this;}
  AlertDialog create(){latest=result;return result;}
 }
 void setOnDismissListener(Dismiss value){dismiss=value;}void show(){}Window getWindow(){return window;}
 void dismiss(){if(dismiss!=null)dismiss.dismiss(this);}void confirm(){send.click(this,1);dismiss();}
}
class ClientRuntime {
 int requests;String session,value;boolean replace,accept=true;
 boolean sendText(String selected,String text,boolean clear){requests++;session=selected;value=text;replace=clear;return accept;}
}
class ClientService {
 boolean busy=true,uiVisible=true,inputReady=true,stopping,finishing,blocked;
 String session="owned";ClientRuntime runtime=new ClientRuntime();int releases;
 void releaseAllInputs(String selected){releases++;}
 SERVICE_METHOD
}
class ActivityHost {
 boolean inputActive=true,textDialogVisible,available=true;ClientService service=new ClientService();String shownSession="owned";
 AlertDialog activeTextDialog;int orderedReleases,discardedReleases;
 boolean gameInputOpen(){return available;}void releaseControls(){releaseControls(!textDialogVisible);}
 void releaseControls(boolean discard){if(discard)discardedReleases++;else orderedReleases++;}
 void refreshMovementControls(){}
 UI_METHOD
 void open(){showTextInput();}
}
public class TextEntryUiHost {
 static void need(boolean value){if(!value)throw new AssertionError();}
 public static void main(String[] args){
  ActivityHost ui=new ActivityHost();ui.open();EditText field=EditText.latest;AlertDialog dialog=AlertDialog.latest;
  need(ui.textDialogVisible&&ui.orderedReleases==1&&ui.discardedReleases==0);
  need(field.focused&&!field.saved&&!field.autofill&&field.value.equals("COHLOCAL"));
  need(dialog.window.mode==WindowManager.LayoutParams.SOFT_INPUT_STATE_ALWAYS_VISIBLE);
  switch(args[0]){
   case "replace": field.setText("CoH 123!");dialog.confirm();need(ui.service.runtime.requests==1&&ui.service.runtime.replace&&ui.service.runtime.value.equals("CoH 123!"));break;
   case "append": CheckBox.latest.setChecked(false);field.setText("offline");dialog.confirm();need(ui.service.runtime.requests==1&&!ui.service.runtime.replace);break;
   case "cancel": dialog.dismiss();need(ui.service.runtime.requests==0);break;
   case "bounds": field.setText("bad\ntext");dialog.confirm();need(ui.service.runtime.requests==0);break;
   case "duplicate_dialog": ui.open();need(AlertDialog.latest==dialog&&ui.orderedReleases==1);dialog.dismiss();break;
   case "rejection": ui.service.runtime.accept=false;dialog.confirm();need(ui.service.runtime.requests==1&&ui.service.releases==1);break;
   case "foreign": ui.shownSession="foreign";dialog.confirm();need(ui.service.runtime.requests==0);break;
   case "replaced_session": ui.shownSession="foreign";ui.service.session="foreign";dialog.confirm();need(ui.service.runtime.requests==0);break;
   case "inactive": ui.inputActive=false;dialog.confirm();need(ui.service.runtime.requests==0);break;
   case "service_gates":
    for(int mode=0;mode<11;mode++){
     ClientService s=new ClientService();ClientRuntime runtime=s.runtime;
     if(mode==0)s.busy=false;if(mode==1)s.uiVisible=false;if(mode==2)s.inputReady=false;if(mode==3)s.stopping=true;
     if(mode==4)s.finishing=true;if(mode==5)s.blocked=true;if(mode==6)s.runtime=null;
     String session=mode==7?"foreign":"owned",value=mode==8?null:mode==9?"\n":"offline";
     need(s.sendText(session,value,true)==(mode==10));need(runtime.requests==(mode==10?1:0));
    }
    dialog.dismiss();break;
   default:throw new AssertionError();
  }
  need(!ui.textDialogVisible&&ui.activeTextDialog==null&&field.value.isEmpty());
  for(String message:Toast.messages)need(!message.contains("offline")&&!message.contains("CoH 123!"));
  System.out.println("PASS");
 }
}
'''

TEXT_RUNTIME = r'''
 static void textScenario(String mode)throws Exception {
  ClientRuntime r=new ClientRuntime();CountDownLatch blocker=new CountDownLatch(1);
  try {
   if(mode.equals("delivered")) {
    require(r.sendText("owned","offline",true));r.idle();
    require(r.decoder.writes.equals(Arrays.asList("text"))&&r.inputSent==1);
    require(r.log.equals(Arrays.asList("text_entry_dispatch","text_entry_submitted native_effect_verified=false")));
    for(String line:r.log)require(!line.contains("offline"));
   } else if(mode.equals("rejected")) {
    require(!r.sendText("foreign","offline",true));require(!r.sendText("owned","bad\n",true));
    r.cancelled=true;require(!r.sendText("owned","offline",true));r.cancelled=false;
    r.inputReady=false;require(!r.sendText("owned","offline",true));r.inputReady=true;
    r.performanceCommandPending=true;r.performanceCommandGeneration=1;require(!r.sendText("owned","offline",true));
    r.idle();require(r.inputSent==0&&r.decoder.writes.isEmpty()&&r.log.isEmpty());
   } else if(mode.equals("cancel_active")) {
    r.decoder.hold=true;require(r.sendText("owned","offline",true));require(r.decoder.entered.await(1,TimeUnit.SECONDS));
    r.queueRelease("owned",true);r.decoder.proceed.countDown();r.idle();
    require(r.inputSent==0&&r.inputFailed==0&&!r.decoder.writes.contains("text"));
    require(r.log.equals(Arrays.asList("text_entry_dispatch","text_entry_cancelled")));
   } else if(mode.equals("ordered")) {
    r.inputWorker.execute(()->{try{blocker.await();}catch(InterruptedException ignored){}});
    require(r.queueInput("owned",(a,e)->a.writes.add("field_tap"),true));r.queueRelease("owned",false);
    require(r.sendText("owned","offline",true));r.queueRelease("owned",false);require(r.requestEnter("owned"));
    blocker.countDown();r.idle();require(r.decoder.writes.equals(Arrays.asList("field_tap","release","text","release","enter")));
   } else {
    r.inputWorker.execute(()->{try{blocker.await();}catch(InterruptedException ignored){}});
    require(r.sendText("owned","offline",true));
    if(mode.equals("foreign_session"))r.session="foreign";
    else if(mode.equals("foreign_pid"))r.observedClientPid=999;
    else if(mode.equals("foreign_decoder"))r.decoder=new InteractiveRfbClient();
    else if(mode.equals("cancel_queued"))r.queueRelease("owned",true);
    else throw new AssertionError();
    blocker.countDown();r.idle();require(r.inputSent==0&&r.inputFailed==0&&!r.decoder.writes.contains("text"));
   }
  }finally{blocker.countDown();r.decoder.proceed.countDown();r.close();}
  System.out.println("PASS");
 }
'''


class TextEntryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.directory = tempfile.TemporaryDirectory(prefix='coh-text-entry-')
        cls.path = Path(cls.directory.name)
        source = UI.replace('UI_METHOD', production_method((JAVA/'ClientActivity.java').read_text(), 'private void showTextInput('))
        source = source.replace('SERVICE_METHOD', production_method((JAVA/'ClientService.java').read_text(), 'public boolean sendText('))
        (cls.path/'TextEntryUiHost.java').write_text(source)
        runtime = harness().replace('  void world(){', production_method((JAVA/'ClientRuntime.java').read_text(), 'public synchronized boolean sendText(') + '\n  void world(){')
        runtime = runtime.replace(' void sendEnter(long epoch)', ' void sendText(String value,boolean replace,long epoch)throws IOException {sendPerformanceCommand("text",epoch); }\n void sendEnter(long epoch)')
        runtime = runtime.replace(' public static void main(String[] args)throws Exception {', TEXT_RUNTIME + '\n public static void main(String[] args)throws Exception {if(args.length>0){textScenario(args[0]);return;}')
        (cls.path/'SidebarRuntimeHost.java').write_text(runtime)
        subprocess.run(['java','-m','jdk.compiler/com.sun.tools.javac.Main','--release','8','-d',str(cls.path),str(JAVA/'ClientInput.java'),str(JAVA/'ClientAcceptance.java'),str(ZONING_JAVA),str(cls.path/'TextEntryUiHost.java'),str(cls.path/'SidebarRuntimeHost.java')],check=True,capture_output=True,text=True)

    @classmethod
    def tearDownClass(cls):
        cls.directory.cleanup()

    def ui(self, mode): self.run_case('TextEntryUiHost', mode)
    def runtime(self, mode): self.run_case('io.github.russianranger.cohclientinteractive.SidebarRuntimeHost', mode)
    def run_case(self, host, mode):
        result = subprocess.run(['java','-cp',str(self.path),host,mode],check=True,capture_output=True,text=True,timeout=10)
        self.assertIn('PASS',result.stdout)

    def test_dialog_replace_is_one_owned_text_request_without_exposing_value(self): self.ui('replace')
    def test_dialog_append_remains_available_for_login_password(self): self.ui('append')
    def test_cancel_clears_editor_without_transmitting(self): self.ui('cancel')
    def test_invalid_text_never_reaches_service(self): self.ui('bounds')
    def test_l3_while_dialog_open_cannot_open_another_editor(self): self.ui('duplicate_dialog')
    def test_rejected_text_releases_inputs_and_keeps_a_retry_diagnostic(self): self.ui('rejection')
    def test_dialog_cannot_send_to_a_different_session(self): self.ui('foreign')
    def test_editor_from_previous_session_cannot_submit_into_new_owned_session(self): self.ui('replaced_session')
    def test_dialog_cannot_send_after_input_closes(self): self.ui('inactive')
    def test_service_enforces_active_visible_owned_nonending_session(self): self.ui('service_gates')
    def test_runtime_submits_one_transaction_and_logs_no_typed_value(self): self.runtime('delivered')
    def test_runtime_rejects_invalid_foreign_unready_and_pending_command(self): self.runtime('rejected')
    def test_runtime_cancellation_during_send_is_not_a_false_transport_failure(self): self.runtime('cancel_active')
    def test_field_tap_text_and_enter_are_delivered_in_order(self): self.runtime('ordered')
    def test_queued_text_cannot_cross_session_replacement(self): self.runtime('foreign_session')
    def test_queued_text_cannot_cross_client_process_replacement(self): self.runtime('foreign_pid')
    def test_queued_text_cannot_cross_decoder_replacement(self): self.runtime('foreign_decoder')
    def test_focus_loss_discards_queued_text(self): self.runtime('cancel_queued')


if __name__ == '__main__':
    unittest.main()
