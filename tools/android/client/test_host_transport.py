"""Actual-client RFB resize and post-readiness freshness boundaries."""
import importlib.util
import json
import struct
import tempfile
import unittest
from pathlib import Path
from unittest import mock

spec=importlib.util.spec_from_file_location('client_host_transport_test',Path(__file__).with_name('host_smoke.py'))
host=importlib.util.module_from_spec(spec)
spec.loader.exec_module(host)


def update(*rectangles):
    return struct.pack('!BH',0,len(rectangles))+b''.join(rectangles)


def rectangle(x,y,w,h,encoding=0,pixels=b''):
    return struct.pack('!HHHHi',x,y,w,h,encoding)+pixels


class Connection:
    def __init__(self,data=b''):
        self.data=bytearray(data)
        self.sent=[]

    def recv(self,size):
        result=bytes(self.data[:size]);del self.data[:size]
        return result

    def sendall(self,data):self.sent.append(data)


class TransportTests(unittest.TestCase):
    def test_raw_resize_raw_discards_old_pixels_and_negotiates_android_bounds(self):
        connection=Connection()
        with mock.patch.object(host.transport,'rfb_handshake',return_value='desktop'):
            self.assertEqual(host.client_rfb_handshake(connection),'desktop')
        self.assertEqual(connection.sent,[struct.pack('!BBHii',2,0,2,0,-223)])
        frame=host.ClientFramebuffer()
        connection.data.extend(update(rectangle(0,0,1,1,pixels=b'abcd')))
        self.assertEqual(frame.read_update(connection),(True,False))
        self.assertEqual(frame.pixels[:4],b'abcd')
        # Old-size Raw and resize share an update; neither may supply a capture.
        connection.data.extend(update(rectangle(0,0,1,1,pixels=b'efgh'),rectangle(0,0,1024,768,-223)))
        self.assertEqual(frame.read_update(connection),(False,True))
        self.assertFalse(frame.fresh)
        self.assertEqual(frame.updates,0)
        self.assertEqual(len(frame.pixels),1024*768*4)
        self.assertFalse(any(frame.pixels))
        connection.data.extend(update(rectangle(1023,767,1,1,pixels=b'wxyz')))
        self.assertEqual(frame.read_update(connection),(True,False))
        self.assertEqual(frame.pixels[-4:],b'wxyz')
        self.assertTrue(frame.fresh)

    def test_resize_bounds_placement_and_raw_bounds_fail(self):
        for rects in [
            (rectangle(0,0,1025,600,-223),),
            (rectangle(0,0,800,769,-223),),
            (rectangle(0,0,0,600,-223),),
            (rectangle(1,0,800,600,-223),),
            (rectangle(0,0,800,600,-223),rectangle(0,0,1,1,pixels=b'abcd')),
            (rectangle(799,599,2,1,pixels=b'abcdefgh'),),
        ]:
            with self.subTest(rects=rects),self.assertRaises(ValueError):
                host.ClientFramebuffer().read_update(Connection(update(*rects)))

    def test_event_lines_are_incremental_session_bound_and_bounded(self):
        with tempfile.TemporaryDirectory() as temp:
            path=Path(temp)/'events';path.write_bytes(b'')
            events=host.ClientEvents(path,'session')
            ready=json.dumps({'type':'client_startup_observed','session_id':'session','client_pid':460}).encode()
            path.write_bytes(ready[:20]);events.poll();self.assertFalse(events.active)
            with path.open('ab') as out:out.write(ready[20:]+b'\n')
            events.poll();self.assertTrue(events.active);self.assertEqual(events.client_pid,460)
            events.poll();self.assertEqual(events.generation,1)
            with path.open('ab') as out:out.write(b'x'*65537)
            with self.assertRaises(ValueError):events.poll()

    def test_frames_requested_before_event_cannot_qualify_and_early_eof_fails(self):
        for terminal in (True,False):
            with self.subTest(terminal=terminal),tempfile.TemporaryDirectory() as temp:
                directory=Path(temp);events=directory/'events';events.write_bytes(b'')
                clock=[0.0]
                ready={'type':'client_startup_observed','session_id':'session','client_pid':460}
                done={'type':'stage','stage':'actual_client_startup','status':'passed'}
                class Frames(Connection):
                    def sendall(self,data):
                        super().sendall(data)
                        self.requests=getattr(self,'requests',0)+1
                        if self.requests==1:events.write_text(json.dumps(ready)+'\n')
                        if self.requests==7:
                            if terminal:
                                with events.open('a') as out:out.write(json.dumps(done)+'\n')
                                # Fullscreen cleanup may resize after the guest
                                # closes its accepted observation interval.
                                self.data.extend(b'\0'+update(rectangle(0,0,1024,768,-223)))
                                return
                            raise BrokenPipeError()
                        if self.requests==8:raise BrokenPipeError()
                        self.data.extend(b'\0'+update(rectangle(0,0,8,1,pixels=b''.join(bytes((x,x,x,0)) for x in range(8)))))
                connection=Frames()
                process=mock.Mock();process.poll.return_value=None
                def sleep(seconds):clock[0]+=seconds
                def save(path,pixels,*geometry):path.write_bytes(b'png')
                with mock.patch.object(host,'client_rfb_handshake',return_value='desktop'), \
                     mock.patch.object(host.time,'monotonic',side_effect=lambda:clock[0]), \
                     mock.patch.object(host.time,'sleep',side_effect=sleep), \
                     mock.patch.object(host,'save_png',side_effect=save):
                    result=host.observe_rfb(connection,'session',process,20,directory,events)
                captures=result['post_startup_captures']
                self.assertEqual([c['frame_sequence'] for c in captures],[2,4,6])
                self.assertEqual(captures[-1]['elapsed_seconds']-captures[0]['elapsed_seconds'],2)
                self.assertEqual(result['terminal_event_observed'],terminal)
                self.assertEqual(result['failure'] is None,terminal)
                if terminal:self.assertFalse(result['final_frame']['fresh_after_resize'])


if __name__=='__main__':unittest.main()
