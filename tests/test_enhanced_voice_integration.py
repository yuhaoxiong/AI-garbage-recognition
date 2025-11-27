import unittest
from unittest.mock import MagicMock, patch
import sys
import os
from typing import Dict, Any

# Ensure project root is in path
sys.path.append(os.getcwd())

from utils.enhanced_voice_guide import EnhancedVoiceGuide, VoiceEngineType
from utils.serial_voice_engine import SerialVoiceEngine

class TestEnhancedVoiceIntegration(unittest.TestCase):
    def setUp(self):
        # Mock ConfigManager
        self.config_patcher = patch('utils.enhanced_voice_guide.get_config_manager')
        self.mock_get_config_manager = self.config_patcher.start()
        self.mock_config_manager = MagicMock()
        self.mock_get_config_manager.return_value = self.mock_config_manager

        # Mock AudioConfig
        self.mock_audio_config = MagicMock()
        self.mock_audio_config.enable_voice = True
        self.mock_audio_config.voice_language = 'zh'
        self.mock_audio_config.volume = 0.8
        self.mock_audio_config.speech_rate = 150
        # Serial voice config
        self.mock_audio_config.serial_voice = {
            'enable': True,
            'port': 'COM3',  # Mock port
            'baudrate': 9600,
            'encoding': 'gb2312'
        }
        self.mock_config_manager.get_audio_config.return_value = self.mock_audio_config

        # Mock SerialVoiceEngine
        self.serial_engine_patcher = patch('utils.enhanced_voice_guide.SerialVoiceEngine')
        self.mock_serial_engine_class = self.serial_engine_patcher.start()
        self.mock_serial_engine_instance = MagicMock()
        self.mock_serial_engine_class.return_value = self.mock_serial_engine_instance
        self.mock_serial_engine_instance.initialize.return_value = True
        self.mock_serial_engine_instance.speak.return_value = True

        # Mock other engines to avoid actual initialization
        self.linux_tts_patcher = patch('utils.enhanced_voice_guide.LinuxTTSManager')
        self.linux_tts_patcher.start()
        
        self.pyttsx3_patcher = patch('utils.enhanced_voice_guide.Pyttsx3Engine')
        self.pyttsx3_patcher.start()

    def tearDown(self):
        self.config_patcher.stop()
        self.serial_engine_patcher.stop()
        self.linux_tts_patcher.stop()
        self.pyttsx3_patcher.stop()
        
        # Reset singleton
        import utils.enhanced_voice_guide
        utils.enhanced_voice_guide._enhanced_voice_guide = None

    def test_initialization_with_serial_voice(self):
        """Test that EnhancedVoiceGuide initializes SerialVoiceEngine when configured"""
        try:
            guide = EnhancedVoiceGuide()
            
            # Check if SerialVoiceEngine was initialized
            self.mock_serial_engine_class.assert_called_once()
            
            # Check if it's in the engines list
            self.assertIn(VoiceEngineType.SERIAL, guide.engines)
            
            # Check if it's set as current engine
            self.assertEqual(guide.current_engine, VoiceEngineType.SERIAL)
            
            # Check priority
            self.assertEqual(guide.engine_priority[0], VoiceEngineType.SERIAL)
        except Exception as e:
            with open('error_log.txt', 'a') as f:
                f.write(f"test_initialization_with_serial_voice failed: {e}\n")
            raise e

    def test_speak_uses_serial_engine(self):
        """Test that speak method uses the SerialVoiceEngine"""
        try:
            guide = EnhancedVoiceGuide()
            
            # Call speak
            guide.speak("Hello")
            
            # Wait for worker thread to process (mocking worker loop or just checking queue)
            # Since speak is async and puts to queue, we can check if _execute_task calls speak
            # But _execute_task is internal. 
            # Let's mock _speak_with_engine to verify flow, or just call _speak_with_engine directly
            
            result = guide._speak_with_engine("Hello")
            self.assertTrue(result)
            self.mock_serial_engine_instance.speak.assert_called_with("Hello")
        except Exception as e:
            with open('error_log.txt', 'a') as f:
                f.write(f"test_speak_uses_serial_engine failed: {e}\n")
            raise e

if __name__ == '__main__':
    unittest.main()
