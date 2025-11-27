import unittest
from unittest.mock import MagicMock, patch
import sys
import os

# 添加项目根目录到路径
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from utils.serial_voice_engine import SerialVoiceEngine
from utils.voice_guide import VoiceGuide

class TestSerialVoice(unittest.TestCase):
    def setUp(self):
        # Mock serial
        self.serial_patcher = patch('serial.Serial')
        self.mock_serial = self.serial_patcher.start()
        self.mock_serial_instance = MagicMock()
        self.mock_serial.return_value = self.mock_serial_instance
        self.mock_serial_instance.is_open = True

    def tearDown(self):
        self.serial_patcher.stop()

    def test_serial_engine_speak(self):
        """测试串口引擎发送数据"""
        config = {
            'port': 'COM3',
            'baudrate': 9600,
            'encoding': 'gb2312'
        }
        engine = SerialVoiceEngine(config)
        engine.initialize()
        
        text = "你好"
        engine.speak(text)
        
        # 验证发送的数据
        # #你好 -> GB2312: 23 C4 FA BA C3
        expected_bytes = b'#' + "你好".encode('gb2312')
        self.mock_serial_instance.write.assert_called_with(expected_bytes)

    @patch('utils.voice_guide.get_config_manager')
    def test_voice_guide_integration(self, mock_get_config):
        """测试VoiceGuide集成"""
        # Mock配置
        mock_config = MagicMock()
        mock_get_config.return_value = mock_config
        
        # 模拟音频配置
        mock_audio_config = MagicMock()
        mock_audio_config.enable_voice = True
        mock_audio_config.serial_voice = {
            'enable': True,
            'port': 'COM3',
            'baudrate': 9600,
            'encoding': 'gb2312'
        }
        mock_config.get_audio_config.return_value = mock_audio_config
        
        # 初始化VoiceGuide
        guide = VoiceGuide()
        
        # 验证是否使用了SerialVoiceEngine
        self.assertIsInstance(guide.tts_engine, SerialVoiceEngine)
        
        # 测试播放
        guide.speak("测试")
        
        # 验证串口写入
        # 由于是异步播放，需要等待一下或者mock队列处理
        # 这里我们直接检查 _speak_sync_safe 是否被调用比较困难，
        # 但我们可以检查 tts_engine.speak 是否被调用
        # 不过 VoiceGuide 的 worker 是在线程中运行的
        
        # 简单起见，我们直接调用 _speak_sync_safe 来验证
        guide._speak_sync_safe("测试")
        
        expected_bytes = b'#' + "测试".encode('gb2312')
        self.mock_serial_instance.write.assert_called_with(expected_bytes)

if __name__ == '__main__':
    unittest.main()
