#!/usr/bin/env python2.7
#
#   PiCam SSTV Transmitterf
#
#   Copyright (C) 2018  Mark Jessop <vk5qi@rfhead.net>
#   Released under GNU GPL v3 or later
#
#   PiCamera API: https://picamera.readthedocs.io/en/release-1.12/api_camera.html
#
#   This script is hacked together from the WenetPiCam class out of the Wenet project.
#
#   Dependencies: picamera, pySSTV

from picamera import PiCamera
from time import sleep
from threading import Thread
from dra818 import *
from PIL import Image
from PIL import ImageDraw
from PIL import ImageFont
import glob
import os
import os.path
import datetime
import traceback


class SSTVPiCam(object):
    """ PiCam Wrapper Class """

    def __init__(self,
                tx_mode="m1", 
                num_images=1,
                image_delay=0.5,
                vertical_flip = False, 
                horizontal_flip = False,
                temp_filename_prefix = 'picam_temp',
                ptt_locked = False,
                post_image_function = None,
                debug_ptr = None
                ):

        """ Instantiate a SSTVPiCam Object
            used to capture images from a PiCam using 'optimal' capture techniques.

            Keyword Arguments:
            callsign: The callsign to be used when converting images to SSTV. Must be <=6 characters in length.
            tx_mode: SSTV Mode to transmit using. 
                    Valid Modes:
                    s1: Scottie 1
                    r36: Robot 36
                    pd120: PD120

            num_images: Number of images to capture in sequence when the 'capture' function is called.
                        The 'best' (largest filesize) image is selected and saved.
            image_delay: Delay time (seconds) between each captured image.

            vertical_flip: Flip captured images vertically.
            horizontal_flip: Flip captured images horizontally.
                            Used to correct for picam orientation.

            temp_filename_prefix: prefix used for temporary files.

            debug_ptr:  'pointer' to a function which can handle debug messages.
                        This function needs to be able to accept a string.
                        Used to get status messages into the downlink.

            ptt_locked: If True, lock the PTT on.

        """

        self.debug_ptr = debug_ptr
        self.temp_filename_prefix = temp_filename_prefix
        self.num_images = num_images
        self.image_delay = image_delay
        self.post_image_function = post_image_function
        self.tx_mode = tx_mode
        self.ptt_locked = ptt_locked


        # Default capture resolution is full-frame Picam 2 images
        self.src_resolution=(3280,2464)

        if self.tx_mode == "r36":
            # Robot 36
            self.tx_resolution = (320,240)
        elif self.tx_mode == "pd120":
            # PD120
            self.tx_resolution = (640,496)
        else:
            # Scottie 2
            self.tx_resolution = (320,256)


        # Attempt to start picam.
        self.cam = PiCamera()

        # Configure camera.
        try:
            self.cam.resolution = self.src_resolution
        except:
            # Default to Picam 1 max resolution if we cannot set the higher PiCam 2 resolution.
            self.cam.resolution = (2592,1944)
        
        # These may need to be changed depending on camera orientation.
        self.cam.hflip = horizontal_flip
        self.cam.vflip = vertical_flip
        self.cam.exposure_mode = 'auto'
        self.cam.awb_mode = 'sunlight' # Fixed white balance compensation. 
        self.cam.meter_mode = 'matrix'

        # Start the 'preview' mode, effectively opening the 'shutter'.
        # This lets the camera gain control algs start to settle.
        self.cam.start_preview()


    def debug_message(self, message):
        """ Write a debug message.
        If debug_ptr was set to a function during init, this will
        pass the message to that function, else it will just print it.
        This is used mainly to get updates on image capture into the Wenet downlink.

        """
        message = datetime.datetime.utcnow().isoformat() + " PiCam Debug: " + message
        if self.debug_ptr != None:
            self.debug_ptr(message)
        else:
            print(message)


    def close(self):
        self.cam.close()


    def capture(self, filename='picam.jpg'):
        """ Capture an image using the PiCam
            
            Keyword Arguments:
            filename:   destination filename.
        """

        # Attempt to capture a set of images.
        for i in range(self.num_images):
            self.debug_message("Capturing Image %d of %d" % (i+1,self.num_images))
            # Wrap this in error handling in case we lose the camera for some reason.
            try:
                self.cam.capture("%s_%d.jpg" % (self.temp_filename_prefix,i))
                if self.image_delay > 0:
                    sleep(self.image_delay)
            except Exception as e: # TODO: Narrow this down...
                self.debug_message("ERROR: %s" % str(e))
                # Immediately return false. Not much point continuing to try and capture images.
                return False

        
        # Otherwise, continue to pick the 'best' image based on filesize.
        self.debug_message("Choosing Best Image.")
        pic_list = glob.glob("%s_*.jpg" % self.temp_filename_prefix)
        pic_sizes = []
        # Iterate through list of images and get the file sizes.
        for pic in pic_list:
            pic_sizes.append(os.path.getsize(pic))
        largest_pic = pic_list[pic_sizes.index(max(pic_sizes))]

        # Copy best image to target filename.
        self.debug_message("Copying image to storage with filename %s" % filename)
        os.system("cp %s %s" % (largest_pic, filename))
        # Clean up temporary images.
        os.system("rm %s_*.jpg" % self.temp_filename_prefix)

        return True 


    def resize(self, filename="output.jpg", dest_filename="picam_temp.png"):
        """ Resize the supplied image to a resolution suitable for SSTV encoding.


        """
        self.debug_message("Resizing image.")
        return_code = os.system("convert %s -resize %dx%d\! %s" % (filename, self.tx_resolution[0], self.tx_resolution[1], dest_filename))
        if return_code != 0:
            self.debug_message("Resize operation failed!")
            return False
        
        return True


    def sstvify(self, filename, temp_filename="picam_temp.png"):
        """ Convert a supplied PNG image to SSTV Audio.
        Returns the filename of the converted SSTV file.

        Keyword Arguments:
        filename:   Source PNG filename.
                    Output SSTV image will be saved to to a temporary file (output.wav) which should be
                    transmitted immediately.

        """

        # Copy out file, since pisstv doesnt have an output filename argument...
        os.system("cp %s %s" % (filename, temp_filename))

        # Convert to sstv
        sstv_convert_command = "./pisstv -p %s -r 22050 %s" % (self.tx_mode, temp_filename)

        self.debug_message("Converting image to SSTV.")
        return_code = os.system(sstv_convert_command)
        if return_code != 0:
            self.debug_message("Failed to convert image to SSTV!")
            return "FAIL"
        else:
            return temp_filename + ".wav"


    def transmit_image(self, filename="output.wav"):
        ''' Transmit an image '''
        # TODO: Make a non-blocking transmit function.

        # PTT On
        dra818_ptt(True)
        # Delay slightly.
        sleep(2)

        self.debug_message("Transmitting...")
        tx_command = "aplay %s" % filename
        return_code = os.system(tx_command)

        # If we are not locking the PTT on, stop the transmitter.
        if self.ptt_locked == False:
            dra818_ptt(False)

        if return_code != 0:
            self.debug_message("Error playing SSTV file.")


    auto_capture_running = False
    def auto_capture(self, destination_directory, post_process_ptr=None, post_process_ptr_small=None, post_tx_function=None, delay = 0):
        """ Automatically capture and transmit images in a loop.
        Images are automatically saved to a supplied directory, with file-names
        defined using a timestamp.

        Use the run() and stop() functions to start/stop this running.
        
        Keyword Arguments:
        destination_directory:  Folder to save images to. Raw JPG images are saved here.
        post_process_ptr: An optional function which is called after the image is captured. This function
                          will be passed the path/filename of the captured image.
                          This can be used to add overlays, etc to the image before it is SSDVified and transmitted.
                          NOTE: This function need to modify the image in-place.
        post_process_ptr_small: An optional function which is called after the image is captured. This function
                          will be passed the path/filename of the captured image.
                          As above, but performed after the image has been resized to the SSTV mode resolution.
                          NOTE: This function needs to modify the image in-place.
        post_tx_function: An optional function which is called after the image has been transmitted.
        delay:  An optional delay in seconds between capturing images. Defaults to 0.
                This delay is added on top of any delays caused while waiting for the transmit queue to empty.
        """


        while self.auto_capture_running:

            # Grab current timestamp.
            capture_time = datetime.datetime.utcnow().strftime("%Y%m%d-%H%M%SZ")
            capture_filename_full = destination_directory + "/%s_picam.jpg" % capture_time
            capture_filename_small = destination_directory + "/%s_picam_small.png" % capture_time

            # Attempt to capture.
            capture_successful = self.capture(capture_filename_full)

			# If capture was unsuccessful, try again in a little bit
            if not capture_successful:
                sleep(5)

                self.debug_message("Capture failed! Attempting to reset camera...")

                try:
                    self.cam.close()
                except:
                    self.debug_message("Closing camera object failed.")

                try:
                    self.init_camera()
                except:
                    self.debug_message("Error initializing camera!")
                    sleep(1)

                continue

            # Otherwise, proceed to post-processing step.
            if post_process_ptr != None:
                try:
                    self.debug_message("Running Image Post-Processing (Full Size)")
                    post_process_ptr(capture_filename_full)
                except:
                    error_str = traceback.format_exc()
                    self.debug_message("Image Post-Processing Failed: %s" % error_str)

            # Resize the image.
            resize_successful = self.resize(capture_filename_full, capture_filename_small)

            if not resize_successful:
                continue

            # Otherwise, proceed to post-processing step.
            if post_process_ptr_small != None:
                try:
                    self.debug_message("Running Image Post-Processing (Resized)")
                    post_process_ptr_small(capture_filename_small)
                except:
                    error_str = traceback.format_exc()
                    self.debug_message("Image Post-Processing Failed: %s" % error_str)

            # SSTV'ify the image.
            sstv_filename = self.sstvify(capture_filename_small)

            # Check the SSDV Conversion has completed properly. If not, break.
            if sstv_filename == "FAIL":
                continue

            # Transmit the image. TODO: Make this non-blocking.
            self.transmit_image(sstv_filename)

            if post_tx_function != None:
                post_tx_function()

            # Sleep before capturing next image.
            sleep(delay)
        # Loop!

        self.debug_message("Exited auto capture thread!")


    def run(self, destination_directory, post_process_ptr=None, post_process_ptr_small=None, post_tx_function=None, delay = 0):
        """ Start auto-capturing images in a thread.

        Refer auto_capture function above.
        
        Keyword Arguments:
        destination_directory:  Folder to save images to.
        post_process_ptr: An optional function which is called after the image is captured. This function
                          will be passed the path/filename of the captured image.
                          This can be used to add overlays, etc to the image before it is SSDVified and transmitted.
                          NOTE: This function needs to modify the image in-place.
        post_process_ptr_small: An optional function which is called after the image is captured. This function
                          will be passed the path/filename of the captured image.
                          As above, but performed after the image has been resized to the SSTV mode resolution.
                          NOTE: This function needs to modify the image in-place.
        delay:  An optional delay in seconds between capturing images. Defaults to 0.
                This delay is added on top of any delays caused while waiting for the transmit queue to empty.
        """     

        self.auto_capture_running = True

        capture_thread = Thread(target=self.auto_capture, kwargs=dict(
            destination_directory=destination_directory,
            post_process_ptr=post_process_ptr,
            post_process_ptr_small=post_process_ptr_small,
            post_tx_function=post_tx_function,
            delay=delay))

        capture_thread.start()

    def stop(self):
        self.auto_capture_running = False



# Basic transmission test script.
if __name__ == "__main__":
    import subprocess
    import ublox

    # Try and start up the GPS rx thread.
    try:
        gps = ublox.UBloxGPS(port="/dev/ttyACM0", 
            dynamic_model = ublox.DYNAMIC_MODEL_AIRBORNE1G, 
            update_rate_ms = 1000,
            log_file = 'gps_data.log'
            )
    except Exception as e:
        print("ERROR: Could not Open GPS - %s" % str(e))
        gps = None

    def post_process(filename):
        # Post-Process the full-size image.
        # Currently not doing anything in post-processing
        # This is where we might add overlays, if we consider it worthwhile.
        pass

    def post_process_small(filename):
        # Post-Process the resized image
        global gps

        # Try and grab current GPS data snapshot
        try:
            if gps != None:
                gps_state = gps.read_state()
                print("Current GPS State: " + str(gps_state))

                # Format time
                short_time = gps_state['datetime'].strftime("%Y-%m-%d %H:%M:%S")

                # Construct string which we will add onto the image.
                if gps_state['numSV'] < 3:
                    # If we don't have enough sats for a lock, don't display any data.
                    # TODO: Use the GPS fix status values here instead.
                    gps_string = " HIGH ALTITUDE BALLOON"
                else:
                    gps_string = " %.5f, %.5f  %dm" % (
                        gps_state['latitude'],
                        gps_state['longitude'],
                        int(gps_state['altitude']))
            else:
                gps_string = " HIGH ALTITUDE BALLOON"
        except:
            error_str = traceback.format_exc()
            print("GPS Data Access Failed: %s" % error_str)
            gps_string = " HIGH ALTITUDE BALLOON"


        # Add text overlay.
        textoverlay="VK5ARG " + gps_string
        print("Adding text overlay: " + textoverlay)
        img = Image.open(filename)
        I1 = ImageDraw.Draw(img)
        overlayFont = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSansMono-Bold.ttf', 24)
        I1.rectangle([(0,0),(639,25)], fill=(0,0,0), outline=None)
        I1.text((20, 1), "%s" % (textoverlay), font=overlayFont, fill=(255, 255, 255))
        img.save(filename)

    # Transmit ident.wav every 4th image, if it exists.
    tx_count = 0

    def post_tx():
        global tx_count

        if tx_count % 4 == 0:
            if os.path.isfile('ident.wav'):
                # Transmit ident.
                print("Transmitting ident.")
                # PTT on
                dra818_ptt(True)
                time.sleep(0.3)
                # Send ident
                _ident_cmd = "aplay ident.wav"
                subprocess.call(_ident_cmd, shell=True)
                time.sleep(0.3)
                # PTT off
                dra818_ptt(False)

        tx_count += 1


    # Configure IO lines for DRA818
    dra818_setup_io()

    # Set the DRA818 into high power mode.
    dra818_high_power(False)

    # Initialize the SSTV Image Capture/Encode class.
    picam = SSTVPiCam(
        tx_mode = "pd120", # Valid modes: s2, r36, pd120
        num_images = 5
        )

    picam.run(destination_directory="./tx_images/",
        post_process_ptr = post_process,
        post_process_ptr_small = post_process_small,
        post_tx_function = post_tx,
        delay = 15
        )
    try:
        while True:
            sleep(5)
    except KeyboardInterrupt:
        print("Closing")
        picam.stop()

