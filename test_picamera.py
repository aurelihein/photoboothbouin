import picamera
import time

def how_long(start, op):
    print('%s took %.2fs' % (op, time.time() - start))
    return time.time()

start = time.time()
with picamera.PiCamera() as camera:
    start = how_long(start, 'init')
    camera.resolution = (1920, 1080)
    start = how_long(start, 'set resolution')
    camera.brightness = 50
    start = how_long(start, 'set brightness')
    camera.preview_fullscreen = True
    start = how_long(start, 'set preview_fullscreen')
    #camera.preview_alpha = 120
    #start = how_long(start, 'set preview_alpha')
    camera.framerate = 90
    start = how_long(start, 'set framerate')
    #camera.video_stabilization = True
    #start = how_long(start, 'set video_stabilization')
    #camera.shutter_speed = 800
    #start = how_long(start, 'set shutter_speed')
    camera.start_preview()
    start = how_long(start, 'start_preview')
    time.sleep(4)
    start = time.time()
    #camera.capture('img14.jpg', 'jpeg', use_video_port=True)
    camera.capture('img14.png')
    start = how_long(start, 'capture')
    camera.stop_preview()
    start = how_long(start, 'stop_preview')
    camera.close()
    start = how_long(start, 'close')
