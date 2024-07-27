import pyaudio

def list_audio_devices():
    p = pyaudio.PyAudio()
    for i in range(p.get_device_count()):
        info = p.get_device_info_by_index(i)
        print(f"Device {i}: {info['name']} ({info['hostApi']}) - Inputs: {info['maxInputChannels']} Outputs: {info['maxOutputChannels']}")
    p.terminate()

if __name__ == "__main__":
    list_audio_devices()
