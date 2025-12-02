import os
import sys
import queue
import sounddevice as sd
import vosk
import json

# Set model path
MODEL_PATH = "models/vosk-model-small-cn-0.22"

def test_mic_stt():
    if not os.path.exists(MODEL_PATH):
        print(f"Please download the model from https://alphacephei.com/vosk/models and unpack as {MODEL_PATH}")
        sys.exit(1)

    print(f"Loading model from {MODEL_PATH}...")
    model = vosk.Model(MODEL_PATH)
    
    # Create a queue to communicate between the audio callback and main thread
    q = queue.Queue()

    def callback(indata, frames, time, status):
        """This is called (from a separate thread) for each audio block."""
        if status:
            print(status, file=sys.stderr)
        q.put(bytes(indata))

    print("\n请说话 (按 Ctrl+C 停止)...")
    
    try:
        with sd.RawInputStream(samplerate=16000, blocksize=8000, device=None, dtype='int16',
                               channels=1, callback=callback):
            rec = vosk.KaldiRecognizer(model, 16000)
            while True:
                data = q.get()
                if rec.AcceptWaveform(data):
                    result = json.loads(rec.Result())
                    text = result.get("text", "")
                    if text:
                        print(f"识别结果: {text}")
                else:
                    # Partial result
                    partial = json.loads(rec.PartialResult())
                    # print(f"Partial: {partial.get('partial', '')}")
                    pass

    except KeyboardInterrupt:
        print("\n停止录音")
    except Exception as e:
        print(f"\n发生错误: {e}")

if __name__ == "__main__":
    test_mic_stt()

