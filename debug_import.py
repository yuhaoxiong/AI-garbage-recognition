import sys
import os

sys.path.append(os.getcwd())

try:
    from utils.enhanced_voice_guide import VoiceEngineType
    print("VoiceEngineType imported successfully")
    print(f"SERIAL in VoiceEngineType: {'SERIAL' in VoiceEngineType.__members__}")
    for member in VoiceEngineType:
        print(f"Member: {member.name} = {member.value}")
except Exception as e:
    print(f"Import failed: {e}")
