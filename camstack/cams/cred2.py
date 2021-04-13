'''
    Chuck, Rajni, GLINT
'''
import time
from typing import Union

from camstack.cams.edt_base import EDTCamera

from camstack.core.utilities import CameraMode

# CameraModes: copy, ...

# Camera: reloadshm, populatekeywords


class CRED2(EDTCamera):

    INTERACTIVE_SHELL_METHODS = [
        'set_synchro', 'set_gain','get_gain', 'set_NDR', 'get_NDR', 'set_fps',
        'get_fps', 'set_tint', 'get_tint', 'get_temperature', 'toggle_cooling',
        'set_temperature_setpoint'] + \
        EDTCamera.INTERACTIVE_SHELL_METHODS

    MODES = {
        # FULL 640 x 512
        'full':
        CameraMode(x0=0, x1=639, y0=0, y1=511),
        # 320x256 half frame, centered
        0:
        CameraMode(x0=160,
                   x1=479,
                   y0=128,
                   y1=383,
                   fps=1500.082358000,
                   tint=0.000663336),
    }

    KEYWORDS = {}
    KEYWORDS.update(EDTCamera.KEYWORDS)

    def __init__(self,
                 name: str,
                 stream_name: str,
                 mode_id: int = 1,
                 unit: int = 0,
                 channel: int = 0):

        # Allocate and start right in the appropriate binning mode
        self.synchro = False
        basefile = '/home/scexao/src/camstack/config/cred2_14bit.cfg'
        self.NDR = None  # Grabbed in prepare_camera_finalize

        # Call EDT camera init
        # This should pre-kill dependent sessions
        # But we should be able to "prepare" the camera before actually starting
        EDTCamera.__init__(self, name, stream_name, mode_id, unit, channel,
                           basefile)

        # ======
        # AD HOC
        # ======

        # Issue a few standards for CRED2
        self.send_command('set fan mode manual')
        self.send_command('set fan speed 0')
        self.send_command('set led off')
        self.set_gain('high')
        self.set_temperature_setpoint(-40.0)

    # =====================
    # AD HOC PREPARE CAMERA
    # =====================

    def prepare_camera(self, mode_id):

        if mode_id is None:
            mode_id = self.current_mode_id

        # Not really handling fps/tint for the OCAM, we just assume an ext trigger
        if mode_id == 'full':  #TODO
            self.send_command('set cropping off')
        else:
            self.send_command('set cropping on')

        mode = self.MODES[mode_id]
        self._set_check_cropping(mode.x0, mode.x1, mode.y0, mode.y1)

        # Changing the binning trips the external sync (at lest on OCAM ?)
        # TODO Do I need to set fps and tint ?
        self.set_synchro(self.synchro)

    def prepare_camera_finalize(self, mode_id: int = None):

        if mode_id is None:
            mode_id = self.current_mode_id
        cm = self.MODES[mode_id]

        # Initialization of the camera: reset the NDR to 1.
        if self.NDR is None:
            self.set_NDR(1)

        if cm.fps is not None:
            self.set_fps(cm.fps)
        if cm.tint is not None:
            self.set_tint(cm.tint)

    def send_command(self, cmd, format=True):
        # Just a little bit of parsing to handle the CRED2 format
        res = EDTCamera.send_command(self, cmd)
        if format:
            return res.split(':')
        else:
            return res

    def _fill_keywords(self):
        # Do a little more filling than the subclass after changing a mode
        # And call the thread-polling function
        #TODO: thread temp polling

        EDTCamera._fill_keywords(self)

        self.camera_shm.update_keyword('DETECTOR', 'CRED2')
        self.camera_shm.update_keyword('CROPPED',
                                       self.current_mode_id != 'full')
        self.camera_shm.update_keyword('CROP_OR1', self.current_mode.x0)
        self.camera_shm.update_keyword('CROP_OR2', self.current_mode.y0)
        self.get_NDR()  # Sets 'NDR'
        self.get_tint()  # Sets 'EXPTIME'
        self.get_fps()  # Sets 'FRATE'

        # Additional fill-up of the camera state
        self.get_gain()  # Sets 'DETGAIN'

        # Call the stuff that we can't know otherwise
        self.poll_camera_for_keywords()  # Sets 'DET-TMP'

    def poll_camera_for_keywords(self):
        self.get_temperature()

    # ===========================================
    # AD HOC METHODS - TO BE BOUND IN THE SHELL ?
    # ===========================================

    def _get_cropping(self):
        xx, yy = self.send_command('cropping raw')[1:]
        x0, x1 = xx.split('-')
        y0, y1 = yy.split('-')
        return int(x0), int(x1), int(y0), int(y1)

    def _set_check_cropping(self, x0, x1, y0, y1):
        for _ in range(3):
            gx0, gx1, gy0, gy1 = self._get_cropping()
            if gx0 == x0 and gx1 == x1 and gy0 == y0 and gy1 == y1:
                return x0, x1, y0, y1
            if gx0 != x0 or gx1 != x1:
                self.send_command('set cropping columns %u-%u') % (x0, x1)
                # CRED2s are finnicky with cropping, we'll add a wait
                time.sleep(.5)
            if gy0 != y0 or gy1 != y1:
                self.send_command('set cropping rows %u-%u') % (x0, x1)
                time.sleep(.5)
        raise AssertionError(
            f'Cannot set desired crop {x0}-{x1} {y0}-{y1} after 3 tries')

    def set_synchro(self, synchro: bool):
        val = ('off', 'on')[synchro]
        _ = self.send_command(f'set extsynchro {val}')
        res = self.send_command('extsynchro raw')
        self.synchro = {'off': False, 'on': True}[res]
        self.camera_shm.update_keyword('EXTTRIG',
                                       ('False', 'True')[self.synchro])
        return self.synchro

    def set_gain(self, gain: Union[int, str]):
        if type(gain) is int:
            gain = ('low', 'medium', 'high')[gain]
        self.send_command(f'set sensibility {gain}')
        return self.get_gain()

    def get_gain(self):
        res = self.send_command('sensibility raw')
        # res is high, medium or low
        self.camera_shm.update_keyword('DETGAIN', res)
        return res

    def set_NDR(self, NDR: int):
        self.send_command('set nbreadworeset {NDR}')
        return self.get_NDR()

    def get_NDR(self):
        self.NDR = int(self.send_command('nbreadworeset raw'))
        self.camera_shm.update_keyword('NDR', self.NDR)
        self.camera_shm.update_keyword('DETMODE',
                                       ('Single', 'IMRO')[self.NDR > 1])
        return self.NDR

    def set_fps(self, fps: float):
        self.send_command(f'set fps {fps}')
        return self.get_fps()

    def get_fps(self):
        fps = float(self.send_command('fps raw'))
        self.camera_shm.update_keyword('FRATE', fps)
        return fps

    def max_fps(self):
        return float(self.send_command('maxfps raw'))

    def set_tint(self, tint: float):
        self.send_command(f'set tint {tint}')
        return self.get_tint()

    def get_tint(self):
        tint = float(self.send_command('tint raw'))
        self.camera_shm.update_keyword('EXPTIME', tint)
        return tint

    def max_tint(self):
        return float(self.send_command('maxtint raw'))

    def get_temperature(self):
        temp = float(self.send_command('temp snake raw'))
        self.camera_shm.update_keyword('DET-TMP', temp + 273.15)
        return temp

    def set_temperature_setpoint(self, temp: float):
        self.send_command(f'set temp snake {temp:.1f}')
        return float(self.send_command('temp snake setpoint raw'))

    def _shutdown(self):
        res = self.send_command('shutdown')
        if 'OK' in res:
            while True:
                time.sleep(5)
                print('Camera shutdown was acknowledged.')
                print('Processes on this end were killed.')
                print('You should quit this shell.')
                print('You\'ll need to power cycle the CRED2 to reboot it.')


class Rajni(CRED2):

    INTERACTIVE_SHELL_METHODS = [] + CRED2.INTERACTIVE_SHELL_METHODS

    MODES = {}
    MODES.update(CRED2.MODES)

    KEYWORDS = {}  # TODO: see about that later.

    def __init__(self,
                 name: str,
                 stream_name: str,
                 mode_id: int,
                 unit: int = 0,
                 channel: int = 0):
        CRED2.__init__(self, name, stream_name, mode_id, unit, channel)


class GLINT(CRED2):
    MODES = {
        # GLINT
        12:
        CameraMode(x0=224,
                   x1=319,
                   y0=80,
                   y1=423,
                   fps=1394.833104000,
                   tint=0.000711851),
    }
    MODES.update(CRED2.MODES)


class Chuck(CRED2):
    MODES = {
        # 224 x 156, centered
        1:
        CameraMode(x0=192,
                   x1=415,
                   y0=160,
                   y1=347,
                   fps=2050.202611000,
                   tint=0.000483913),
        # 128 x 128, centered
        2:
        CameraMode(x0=256,
                   x1=383,
                   y0=192,
                   y1=319,
                   fps=4500.617741000,
                   tint=0.000218568),
        # 64 x 64, centered
        3:
        CameraMode(x0=288,
                   x1=351,
                   y0=224,
                   y1=287,
                   fps=9203.638201000,
                   tint=0.000105249),
        # 192 x 192, centered
        4:
        CameraMode(x0=224,
                   x1=415,
                   y0=160,
                   y1=351,
                   fps=2200.024157000,
                   tint=0.000449819),
        # 96 x 72, centered
        5:
        CameraMode(x0=256,
                   x1=351,
                   y0=220,
                   y1=291,
                   fps=8002.636203000,
                   tint=0.000121555),
    }
    MODES.update(CRED2.MODES)

    # Add modes 6-11 (0-5 offseted 32 pix)
    for i in range(6):
        cm = MODES[i]
        MODES[i + 6] = CameraMode(x0=cm.x0 - 32,
                                  x1=cm.x1 - 32,
                                  y0=cm.y0,
                                  y1=cm.y1,
                                  fps=cm.fps,
                                  tint=cm.tint)


# Quick shorthand for testing
if __name__ == "__main__":
    cam = Rajni('rajni', 'rajnicam', mode_id='full', unit=1, channel=0)
    from camstack.core.utilities import shellify_methods
    shellify_methods(cam, globals())

    ########
    '''
    IRCAM SERVER legacy mapping:
    
    ## Useful server commands (identified from chuck)
    gtint -> get_tint
    gNDR -> get_NDR
    gfps -> get_fps

    stint -> set_tint
    sfps -> set_fps
    sNDR -> set_NDR
    cropOFF -> set_mode('full') - (scrop_cols 0 639, scrop_rows 0 511)
    cropON - reverts to the last cropmode ??

    setcrop 1-N -> set modes

    ## Serial commands (identified from ircamserver.c)
    tint
    set tint
    fps
    set fps
    nbreadworeset
    set nbreadworeset
    temperatures snake
    set temperatures snake (redo a get after a set ?)

    reset
    shutdown

    '''