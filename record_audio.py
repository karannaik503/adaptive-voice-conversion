import wave
import pyaudio
import argparse
import sys
from contextlib import contextmanager

if sys.platform == 'linux':
    from ctypes import *

    ERROR_HANDLER_FUNC = CFUNCTYPE(None, c_char_p, c_int, c_char_p, c_int, c_char_p)

    def py_error_handler(filename, line, function, err, fmt):
        pass

    c_error_handler = ERROR_HANDLER_FUNC(py_error_handler)

    @contextmanager
    def noalsaerr():
        asound = cdll.LoadLibrary('libasound.so')
        asound.snd_lib_error_set_handler(c_error_handler)
        yield
        asound.snd_lib_error_set_handler(None)
else:
    @contextmanager
    def noalsaerr():
        yield

if __name__ == '__main__':

    parser = argparse.ArgumentParser("Configuration for recording audio")
    parser.add_argument("--channels", default="2", type=int, help='number of supported channels')  # Adjust as necessary
    parser.add_argument("--rate", default="48000", type=int, help='sampling rate')
    parser.add_argument("--duration", default="5", type=int, help='duration (in seconds) of audio to record')
    parser.add_argument("--device_index", default="46", type=int, help='device index')  # Use Device 46 for your microphone
    parser.add_argument("--output", default="output.wav", type=str, help='output wav file name')
    config = parser.parse_args()

    CHANNELS = config.channels
    RATE = config.rate
    RECORD_SECONDS = config.duration
    INPUT_DEVICE_INDEX = config.device_index
    FORMAT = pyaudio.paInt16
    CHUNK = int(0.010 * RATE)

    with noalsaerr():
        p = pyaudio.PyAudio()

    try:
        stream = p.open(format=FORMAT, channels=CHANNELS, rate=RATE, input=True, input_device_index=INPUT_DEVICE_INDEX)
    except OSError as e:
        print(f"Error opening stream: {e}")
        p.terminate()
        sys.exit(1)

    with wave.open(config.output, 'wb') as wf:
        wf.setnchannels(CHANNELS)
        wf.setsampwidth(p.get_sample_size(FORMAT))
        wf.setframerate(RATE)

        print('Recording...')
        for _ in range(0, RATE // CHUNK * RECORD_SECONDS):
            data = stream.read(CHUNK)
            wf.writeframes(data)
        print('Done')

    stream.close()
    p.terminate()

    print(f"Recording saved as {config.output}!")
