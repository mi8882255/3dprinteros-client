import os
import base64
import thread
import logging
import collections

import log
import http_client
from app import App

class BaseSender:

    def __init__(self, profile, usb_info):
        self.stop_flag = False
        self.profile = profile
        self.usb_info = usb_info
        self.error_code = None
        self.error_message = ''
        self.temps = [0,0]
        self.target_temps = [0,0]
        self.total_gcodes = None
        self.buffer = collections.deque()
        self.downloading_flag = False
        self.downloader = None

    def set_total_gcodes(self, length):
        raise NotImplementedError

    def load_gcodes(self, gcodes):
        raise NotImplementedError

    def download_gcodes_and_print(self, gcodes):
        self.downloader = http_client.File_Downloader(self)
        self.downloading_flag = True
        thread.start_new_thread(self.download_thread, (gcodes,))

    def preprocess_gcodes(self, gcodes):
        gcodes = gcodes.split("\n")
        while gcodes[-1] in ("\n", "\r\n", "\t", " ", "", None):
            line = gcodes.pop()
            self.logger.info("Removing corrupted line '%s' from gcodes tail" % line)
        length = len(gcodes)
        self.set_total_gcodes(length)
        self.logger.info('Got %i gcodes to print.')
        return gcodes

    def gcodes(self, gcodes, is_link = False, job_id=None):
        if job_id:
            self.job_id = job_id
        if is_link:
            if self.downloading_flag:
                self.logger.warning('Download command received while downloading processing. Aborting...')
                return False
            else:
                self.download_gcodes_and_print(gcodes)
        else:
            gcodes = base64.decode(gcodes)
            self.load_gcodes(gcodes)

    def download_thread(self, link):
        if not self.stop_flag:
            self.logger.info('Starting download thread')
            gcode_file_name = self.downloader.async_download(link)
            if gcode_file_name:
                with open(gcode_file_name, 'rb') as f:
                    gcodes = f.read()
                try:
                    self.load_gcodes(gcodes)  # Derived class method call, for example makerbot_sender.load_gcodes(gcodes)
                except Exception as e:
                    self.error_code = 37
                    self.error_message = "Exception occured when printrun was parsing gcodes. Corrupted gcodes? " + str(e)
                self.downloading_flag = False  # TODO: For now it should be after gcodes() due to status error on site
                self.logger.info('Gcodes loaded to memory, deleting temp file')
            try:
                os.remove(gcode_file_name)
            except:
                self.logger.warning("Error while removing temporary gcodes file: " + gcode_file_name)
            self.downloader = None
            self.logger.info('Download thread has been closed')

    def is_downloading(self):
        return self.downloading_flag

    def cancel_download(self):
        self.downloading_flag = False
        self.logger.info("File downloading has been cancelled")

    def get_temps(self):
        return self.temps

    def get_target_temps(self):
        return self.target_temps

    def pause(self):
        self.pause_flag = True

    def unpause(self):
        self.pause_flag = False

    def close(self):
        self.stop_flag = True
        self.job_id = None

    def get_error_code(self):
        return self.error_code

    def get_error_message(self):
        return self.error_message

    def is_error(self):
        return self.error_code != None

    def is_paused(self):
        return self.pause_flag

    def is_operational(self):
        return False

    def upload_logs(self):
        log.make_full_log_snapshot()
        self.logger.info("Sending logs")
        log.send_all_snapshots(App.instance().user_login.user_token)
        self.logger.info("Done")

    def switch_camera(self, module):
        self.logger.info('Changing camera module to %s due to server request' % module)
        App.instance().switch_camera(module)

    def update_software(self):
        self.logger.info('Executing update command from server')
        App.instance().updater.update()

    def quit_application(self):
        self.logger.info('Received quit command from server!')
        App.instance().stop_flag = True