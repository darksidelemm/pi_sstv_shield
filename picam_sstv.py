#!/usr/bin/env python2.7
#
#	PiCam SSTV Transmitterf
#
#	Copyright (C) 2018  Mark Jessop <vk5qi@rfhead.net>
#	Released under GNU GPL v3 or later
#
#	PiCamera API: https://picamera.readthedocs.io/en/release-1.12/api_camera.html
#
#	This script is hacked together from the WenetPiCam class out of the Wenet project.
#
#	Dependencies: picamera, pySSTV

from picamera import PiCamera
from time import sleep
from threading import Thread
from dra818 import *
import glob
import os
import datetime
import traceback


class SSTVPiCam(object):
	""" PiCam Wrapper Class	"""

	def __init__(self,
				tx_mode="PD120", 
				num_images=1,
				image_delay=0.5, 
				vertical_flip = False, 
				horizontal_flip = False,
				temp_filename_prefix = 'picam_temp',
				ptt_locked = False,
				debug_ptr = None
				):

		""" Instantiate a SSTVPiCam Object
			used to capture images from a PiCam using 'optimal' capture techniques.

			Keyword Arguments:
			callsign: The callsign to be used when converting images to SSTV. Must be <=6 characters in length.
			tx_mode: SSTV Mode to transmit using. 
					Currently only PD120 and PD160 are supported.

			num_images: Number of images to capture in sequence when the 'capture' function is called.
						The 'best' (largest filesize) image is selected and saved.
			image_delay: Delay time (seconds) between each captured image.

			vertical_flip: Flip captured images vertically.
			horizontal_flip: Flip captured images horizontally.
							Used to correct for picam orientation.

			temp_filename_prefix: prefix used for temporary files.

			debug_ptr:	'pointer' to a function which can handle debug messages.
						This function needs to be able to accept a string.
						Used to get status messages into the downlink.

			ptt_locked: If True, lock the PTT on.

		"""

		self.debug_ptr = debug_ptr
		self.temp_filename_prefix = temp_filename_prefix
		self.num_images = num_images
		self.image_delay = image_delay
		self.tx_mode = tx_mode
		self.ptt_locked = ptt_locked

		if self.tx_mode == "PD120":
			self.tx_resolution = (640,496)
		elif self.tx_mode == "PD160":
			self.tx_resolution = (512,400)
		else:
			self.tx_resolution = (640,496)
			self.tx_mode = "PD120"


		# Attempt to start picam.
		self.cam = PiCamera()

		# Configure camera.
		self.cam.resolution = self.tx_resolution
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
		message = "PiCam Debug: " + message
		if self.debug_ptr != None:
			self.debug_ptr(message)
		else:
			print(message)


	def close(self):
		self.cam.close()


	def capture(self, filename='picam.jpg'):
		""" Capture an image using the PiCam
			
			Keyword Arguments:
			filename:	destination filename.
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


	def sstvify(self, filename="output.jpg"):
		""" Convert a supplied JPEG image to SSTV Audio.
		Returns the filename of the converted SSTV file.

		Keyword Arguments:
		filename:	Source JPEG filename.
					Output SSTV image will be saved to to a temporary file (output.wav) which should be
					transmitted immediately.

		"""

		# Convert to PNG.
		self.debug_message("Converting image to PNG.")
		return_code = os.system("convert %s picam_temp.png" % filename)
		if return_code != 0:
			self.debug_message("Convert operation failed!")
			return "FAIL"

		sstv_convert_command = "python -m pysstv --mode=%s picam_temp.png output.wav" % self.tx_mode

		self.debug_message("Converting image to SSTV.")
		return_code = os.system(sstv_convert_command)
		if return_code != 0:
			self.debug_message("Failed to convert image to SSTV!")
			return "FAIL"
		else:
			return "output.wav"


	def transmit_image(self, filename="output.wav"):
		''' Transmit an image '''
		# TODO: Make a non-blocking transmit function.

		# PTT On
		dra818_ptt(True)
		# Delay slightly.
		sleep(0.5)

		self.debug_message("Transmitting...")
		tx_command = "aplay %s" % filename
		return_code = os.system(tx_command)

		# If we are not locking the PTT on, stop the transmitter.
		if self.ptt_locked == False:
			dra818_ptt(False)

		if return_code != 0:
			self.debug_message("Error playing SSTV file.")


	auto_capture_running = False
	def auto_capture(self, destination_directory, post_process_ptr=None, delay = 0):
		""" Automatically capture and transmit images in a loop.
		Images are automatically saved to a supplied directory, with file-names
		defined using a timestamp.

		Use the run() and stop() functions to start/stop this running.
		
		Keyword Arguments:
		destination_directory:	Folder to save images to. Raw JPG images are saved here.
		post_process_ptr: An optional function which is called after the image is captured. This function
						  will be passed the path/filename of the captured image.
						  This can be used to add overlays, etc to the image before it is SSDVified and transmitted.
						  NOTE: This function need to modify the image in-place.
		delay:	An optional delay in seconds between capturing images. Defaults to 0.
				This delay is added on top of any delays caused while waiting for the transmit queue to empty.
		"""


		while self.auto_capture_running:
			# Sleep before capturing next image.
			sleep(delay)

			# Grab current timestamp.
			capture_time = datetime.datetime.utcnow().strftime("%Y%m%d-%H%M%SZ")
			capture_filename = destination_directory + "/%s_picam.jpg" % capture_time

			# Attempt to capture.
			capture_successful = self.capture(capture_filename)

			# If capture was unsuccessful, exit out of this thead, as clearly
			# the camera isn't working.
			if not capture_successful:
				return

			# Otherwise, proceed to post-processing step.
			if post_process_ptr != None:
				try:
					self.debug_message("Running Image Post-Processing")
					post_process_ptr(capture_filename)
				except:
					error_str = traceback.format_exc()
					self.debug_message("Image Post-Processing Failed: %s" % error_str)

			# SSTV'ify the image.
			sstv_filename = self.sstvify(capture_filename)

			# Check the SSDV Conversion has completed properly. If not, break.
			if sstv_filename == "FAIL":
				return

			# Transmit the image. TODO: Make this non-blocking.
			self.transmit_image(sstv_filename)
		# Loop!


	def run(self, destination_directory, post_process_ptr=None, delay = 0):
		""" Start auto-capturing images in a thread.

		Refer auto_capture function above.
		
		Keyword Arguments:
		destination_directory:	Folder to save images to.
		post_process_ptr: An optional function which is called after the image is captured. This function
						  will be passed the path/filename of the captured image.
						  This can be used to add overlays, etc to the image before it is SSDVified and transmitted.
						  NOTE: This function need to modify the image in-place.
		delay:	An optional delay in seconds between capturing images. Defaults to 0.
				This delay is added on top of any delays caused while waiting for the transmit queue to empty.
		"""		

		self.auto_capture_running = True

		capture_thread = Thread(target=self.auto_capture, kwargs=dict(
			destination_directory=destination_directory,
			post_process_ptr=post_process_ptr,
			delay=delay))

		capture_thread.start()

	def stop(self):
		self.auto_capture_running = False



# Basic transmission test script.
if __name__ == "__main__":

	def post_process(filename):
		print("Doing nothing with %s" % filename)

	# Configure IO lines for DRA818
	dra818_setup_io()

	picam = SSTVPiCam()

	picam.run(destination_directory="./tx_images/", 
		post_process_ptr = post_process
		)
	try:
		while True:
			sleep(5)
	except KeyboardInterrupt:
		print("Closing")
		picam.stop()

