#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import locale
import logging
import os
import sys

# this is required for Ubuntu which seems to
# have a broken PyQt5 OpenGL implementation
# noinspection PyUnresolvedReferences
from OpenGL import GL

from PyQt5.QtCore import pyqtSignal, pyqtSlot, Qt
from PyQt5.QtOpenGL import QGLContext
from PyQt5.QtWidgets import QOpenGLWidget

# noinspection PyUnresolvedReferences
import vidcutter.libs.mpv as mpv


def get_proc_address(proc):
    glctx = QGLContext.currentContext()
    if glctx is None:
        return None
    return glctx.getProcAddress(str(proc, 'utf-8'))


class mpvWidget(QOpenGLWidget):
    positionChanged = pyqtSignal(float, int)
    durationChanged = pyqtSignal(float, int)

    def __init__(self, parent=None, **mpv_opts):
        super(mpvWidget, self).__init__(parent)
        self.parent = parent
        self.logger = logging.getLogger(__name__)
        locale.setlocale(locale.LC_NUMERIC, 'C')
        self.shuttingdown = False
        self.mpv = mpv.Context()

        if os.getenv('DEBUG', False):
            self.mpv.set_log_level('terminal-default')

        def _istr(o):
            return ('yes' if o else 'no') if type(o) is bool else str(o)

        # do not break on non-existant properties/options
        for opt, val in mpv_opts.items():
            try:
                self.mpv.set_option(opt.replace('_', '-'), _istr(val))
            except:
                pass

        self.mpv.initialize()
        self.opengl = self.mpv.opengl_cb_api()
        self.opengl.set_update_callback(self.updateHandler)
        # ignore expection thrown by older versions of libmpv that do not implement the option
        try:
            self.mpv.set_option('opengl-hwdec-interop', 'auto')
            if sys.platform == 'win32':
                self.mpv.set_option('opengl-backend', 'angle')
        except:
            pass

        self.frameSwapped.connect(self.swapped, Qt.DirectConnection)

        self.mpv.observe_property('time-pos')
        self.mpv.observe_property('duration')
        self.mpv.set_wakeup_callback(self.eventHandler)

    def shutdown(self):
        self.shuttingdown = True
        self.mpv.command('quit')
        self.makeCurrent()
        if self.opengl:
            self.opengl.uninit_gl()

    def initializeGL(self):
        if self.opengl:
            self.opengl.init_gl(None, get_proc_address)

    def paintGL(self):
        if self.opengl:
            self.opengl.draw(self.defaultFramebufferObject(), self.width(), -self.height())

    @pyqtSlot()
    def swapped(self):
        if self.opengl:
            self.opengl.report_flip(0)

    def updateHandler(self):
        if self.window().isMinimized():
            self.makeCurrent()
            self.paintGL()
            self.context().swapBuffers(self.context().surface())
            self.swapped()
            self.doneCurrent()
        else:
            self.update()

    def eventHandler(self):
        if not self.shuttingdown:
            while self.mpv:
                try:
                    event = self.mpv.wait_event(.01)
                    if event.id == mpv.Events.none:
                        continue
                    elif event.id in {mpv.Events.shutdown, mpv.Events.end_file}:
                        break
                    elif event.id == mpv.Events.log_message:
                        event_log = event.data
                        log_msg = '[%s] %s' % (event_log.prefix, event_log.text.strip())
                        if event_log.level in (mpv.LogLevels.fatal, mpv.LogLevels.error):
                            self.logger.critical(log_msg)
                            sys.stderr.write(log_msg)
                            if event_log.level == mpv.LogLevels.fatal or 'file format' in event_log.text:
                                self.parent.errorOccurred.emit(log_msg)
                                self.parent.initMediaControls(False)
                        else:
                            self.logger.debug(log_msg)
                    elif event.id == mpv.Events.property_change:
                        event_prop = event.data
                        if event_prop.name == 'time-pos':
                            self.positionChanged.emit(event_prop.data, self.mpv.get_property('estimated-frame-number'))
                        elif event_prop.name == 'duration':
                            self.durationChanged.emit(event_prop.data, self.mpv.get_property('estimated-frame-count'))
                except mpv.MPVError as e:
                    if e.code != -10:
                        raise e

    def showText(self, msg: str, duration: int, level: int = None):
        self.mpv.command('show-text', msg, duration * 1000, level)

    def play(self, filepath):
        if not os.path.exists(filepath):
            return
        self.mpv.command('loadfile', filepath, 'replace')

    def frameStep(self):
        self.mpv.command('frame-step')

    def frameBackStep(self):
        self.mpv.command('frame-back-step')

    def seek(self, pos, method='absolute+exact'):
        self.mpv.command('seek', pos, method)

    def pause(self):
        self.mpv.set_property('pause', not self.mpv.get_property('pause'))

    def mute(self):
        self.mpv.set_property('mute', not self.mpv.get_property('mute'))

    def volume(self, vol: int):
        self.mpv.set_property('volume', vol)