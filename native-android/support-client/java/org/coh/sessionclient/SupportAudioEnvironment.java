package org.coh.sessionclient;

import android.content.Context;
import android.media.AudioAttributes;
import android.media.AudioDeviceCallback;
import android.media.AudioDeviceInfo;
import android.media.AudioFocusRequest;
import android.media.AudioManager;
import android.os.Handler;
import org.json.JSONObject;

/** Main-thread focus/route owner. Native sink receives only a bounded mailbox. */
final class SupportAudioEnvironment {
    interface Sink { void changed(boolean allowed, long routeGeneration); }
    private final AudioManager manager;
    private final Handler handler;
    private final Sink sink;
    private final AudioFocusRequest request;
    private boolean active, focused, registered;
    private long routeGeneration=1, focusChanges, routeChanges;
    private int requestResult=AudioManager.AUDIOFOCUS_REQUEST_FAILED;
    private final AudioDeviceCallback devices=new AudioDeviceCallback() {
        @Override public void onAudioDevicesAdded(AudioDeviceInfo[] added) { routeChanged(added); }
        @Override public void onAudioDevicesRemoved(AudioDeviceInfo[] removed) { routeChanged(removed); }
    };
    SupportAudioEnvironment(Context context, Handler handler, Sink sink) {
        this.manager=(AudioManager)context.getSystemService(Context.AUDIO_SERVICE);
        this.handler=handler; this.sink=sink;
        request=new AudioFocusRequest.Builder(AudioManager.AUDIOFOCUS_GAIN)
                .setAudioAttributes(new AudioAttributes.Builder().setUsage(AudioAttributes.USAGE_GAME)
                        .setContentType(AudioAttributes.CONTENT_TYPE_MUSIC).build())
                .setWillPauseWhenDucked(true)
                .setOnAudioFocusChangeListener(change -> {
                    if(!active)return;
                    focusChanges++;focused=change==AudioManager.AUDIOFOCUS_GAIN; publish();
                },handler).build();
    }
    private void routeChanged(AudioDeviceInfo[] changed) {
        if(!active)return;
        for(AudioDeviceInfo device:changed)if(device.isSink()) {
            routeChanges++;routeGeneration++;publish();break;
        }
    }
    private void publish() { sink.changed(active&&focused,routeGeneration); }
    void start() {
        if(active)return; active=true;
        if(manager!=null) {
            manager.registerAudioDeviceCallback(devices,handler);registered=true;
            requestResult=manager.requestAudioFocus(request);
            focused=requestResult==AudioManager.AUDIOFOCUS_REQUEST_GRANTED;
        }
        publish();
    }
    void stop() {
        active=false;focused=false;publish();
        if(manager!=null) {
            if(registered){manager.unregisterAudioDeviceCallback(devices);registered=false;}
            manager.abandonAudioFocusRequest(request);
        }
    }
    void apply() { publish(); }
    JSONObject report() throws Exception {
        return new JSONObject().put("active",active).put("focus_granted",focused)
                .put("request_result",requestResult).put("focus_changes",focusChanges)
                .put("route_changes",routeChanges).put("route_generation",routeGeneration)
                .put("route_policy","close/join then reopen on native backend owner");
    }
}
