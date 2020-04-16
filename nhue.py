#!/usr/local/bin/python3

# open a microphone in pyAudio and listen for taps

import pyaudio
import struct
import math
import requests
import time

INITIAL_TAP_THRESHOLD = 0.010
FORMAT = pyaudio.paInt16 
SHORT_NORMALIZE = (1.0/32768.0)
CHANNELS = 2
RATE = 44100  
INPUT_BLOCK_TIME = 0.05
INPUT_FRAMES_PER_BLOCK = int(RATE*INPUT_BLOCK_TIME)

URL1 = "https://192.168.1.155/api/J0MI-Nq9atyix1DHYpk9OBdKKSRUxLG5lpB3LZEx/lights/1/state"
URL2 = "https://192.168.1.155/api/J0MI-Nq9atyix1DHYpk9OBdKKSRUxLG5lpB3LZEx/lights/2/state"
URL3 = "https://192.168.1.155/api/J0MI-Nq9atyix1DHYpk9OBdKKSRUxLG5lpB3LZEx/lights/3/state"
        
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.14; rv:74.0) Gecko/20100101 Firefox/74.0',
    'Accept': '*/*',
    'Accept-Language': 'en-US,en;q=0.5',
    'Content-Type': 'text/plain;charset=UTF-8',
    'Origin': 'https://192.168.1.155',
    'DNT': '1',
    'Connection': 'keep-alive',
    'Referer': 'https://192.168.1.155/debug/clip.html'
}

# # if we get this many noisy blocks in a row, increase the threshold
# OVERSENSITIVE = 15.0/INPUT_BLOCK_TIME                    
# # if we get this many quiet blocks in a row, decrease the threshold
# UNDERSENSITIVE = 120.0/INPUT_BLOCK_TIME 
# # if the noise was longer than this many blocks, it's not a 'tap'
# MAX_TAP_BLOCKS = 0.15/INPUT_BLOCK_TIME

toggleLight = False

def get_rms( block ):
    # RMS amplitude is defined as the square root of the 
    # mean over time of the square of the amplitude.
    # so we need to convert this string of bytes into 
    # a string of 16-bit samples...

    # we will get one short out for each 
    # two chars in the string.
    count = len(block)/2
    format = "%dh"%(count)
    shorts = struct.unpack( format, block )

    # iterate over the block.
    sum_squares = 0.0
    for sample in shorts:
        # sample is a signed short in +/- 32768. 
        # normalize it to 1.0
        n = sample * SHORT_NORMALIZE
        sum_squares += n*n

    return math.sqrt( sum_squares / count )

class NhueListener(object):
    def __init__(self):
        self.pa = pyaudio.PyAudio()
        self.stream = self.open_mic_stream()
        self.lastBrightness = 10
        self.timestampOfLastUpdate = time.monotonic_ns()
        

    def stop(self):
        self.stream.close()

    def find_input_device(self):
        device_index = None            
        for i in range( self.pa.get_device_count() ):     
            devinfo = self.pa.get_device_info_by_index(i)   
            print( "Device %d: %s"%(i,devinfo["name"]) )

            for keyword in ["mic","input"]:
                if keyword in devinfo["name"].lower():
                    print( "Found an input: device %d - %s"%(i,devinfo["name"]) )
                    device_index = i
                    return device_index

        if device_index == None:
            print( "No preferred input found; using default input device." )

        return device_index

    def open_mic_stream( self ):
        device_index = self.find_input_device()

        stream = self.pa.open(   format = FORMAT,
                                 channels = CHANNELS,
                                 rate = RATE,
                                 input = True,
                                 input_device_index = device_index,
                                 frames_per_buffer = INPUT_FRAMES_PER_BLOCK)

        return stream
    
    def updateLight(self, brightness):
        global HEADERS
        global URL
        payload = "{\"bri\":" + str(brightness) + "}"
        print("Brightness: {}".format(brightness))
        print("Payload: {}".format(payload))
        response = requests.request("PUT", URL1, headers=HEADERS, data = payload, verify=False)
        response = requests.request("PUT", URL2, headers=HEADERS, data = payload, verify=False)
        response = requests.request("PUT", URL3, headers=HEADERS, data = payload, verify=False)

    def listen(self):
        try:
            block = self.stream.read(INPUT_FRAMES_PER_BLOCK, exception_on_overflow = False)
        except IOError as e:
            # dammit. 
            print( "(%d) Error recording: %s"%(self.errorcount,e) )
            return

        amplitude = get_rms( block )
        brightness = math.ceil(amplitude * 2000)
        brightness = 254 if brightness > 254 else brightness
        # print("Amplitude: {}".format(amplitude))
        # print("Brightness: {}".format(brightness))
        if (abs(brightness - self.lastBrightness) > 10):
            # change light
            self.lastBrightness = brightness
            currTimestamp = time.monotonic_ns()
            diff = currTimestamp - self.timestampOfLastUpdate
            if (diff > 50000000):
                print("Diff: {}".format(diff))
                self.timestampOfLastUpdate = currTimestamp
                self.updateLight(brightness)
        # time.sleep(0.05)
        print()
        

if __name__ == "__main__":
    nl = NhueListener()

    for i in range(10000):
        nl.listen()