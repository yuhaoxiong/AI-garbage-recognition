import sys
import os
from unittest.mock import MagicMock, patch

sys.path.append(os.getcwd())

try:
    print("Starting manual test...")
    from utils.enhanced_voice_guide import EnhancedVoiceGuide, VoiceEngineType
    print("Import successful")
    
    # Mocking
    with patch('utils.enhanced_voice_guide.get_config_manager') as mock_get_config:
        mock_config = MagicMock()
        mock_get_config.return_value = mock_config
        
        # Setup mock config
        # Simulate ConfigManager structure: no .config, but has ._system_config
        del mock_config.config  # Ensure accessing .config raises AttributeError (or we just don't set it)
        mock_config._system_config = {
            'system': {
                'audio': {
                    'serial_voice': {'enable': True, 'port': 'COM3', 'baudrate': 9600}
                }
            }
        }
        
        mock_audio = MagicMock()
        mock_audio.enable_voice = True
        mock_audio.voice_language = 'zh'
        mock_audio.volume = 0.8
        mock_audio.speech_rate = 150
        mock_audio.serial_voice = None  # Trigger fallback to dictionary lookup
        
        mock_config.get_audio_config.return_value = mock_audio
        
        # Mock SerialVoiceEngine
        with patch('utils.enhanced_voice_guide.SerialVoiceEngine') as mock_serial:
            mock_instance = MagicMock()
            mock_serial.return_value = mock_instance
            mock_instance.initialize.return_value = True
            mock_instance.speak.return_value = True
            
            # Mock other engines to avoid noise
            with patch('utils.enhanced_voice_guide.Pyttsx3Engine'):
                # Conditionally patch LinuxTTSManager if it exists
                patcher = None
                if hasattr(sys.modules['utils.enhanced_voice_guide'], 'LinuxTTSManager'):
                    patcher = patch('utils.enhanced_voice_guide.LinuxTTSManager')
                    patcher.start()
                
                try:
                    print("Initializing guide...")
                    guide = EnhancedVoiceGuide()
                    print(f"Current engine: {guide.current_engine}")
                    
                    if guide.current_engine == VoiceEngineType.SERIAL:
                        print("SUCCESS: Serial engine selected")
                    else:
                        print(f"FAILURE: Current engine is {guide.current_engine}")
                        print(f"Engines: {guide.engines.keys()}")
                        print(f"Priority: {guide.engine_priority}")
                finally:
                    if patcher:
                        patcher.stop()

except Exception as e:
    import traceback
    traceback.print_exc()
