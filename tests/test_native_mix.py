import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

import numpy as np
import soundfile as sf

SCRIPTS = Path(__file__).resolve().parents[1] / 'scripts'


@unittest.skipUnless(shutil.which('ffmpeg') and shutil.which('ffprobe'), 'requires FFmpeg/FFprobe')
class NativeMixTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        cls.root = Path(cls.temp.name) / '音乐 & 路径'
        cls.root.mkdir()
        cls.duration = 3.2
        t = np.arange(round(44100*cls.duration))/44100
        for name, frequency in [('bgm', 440), ('vo', 180), ('original', 330)]:
            signal = .15*np.sin(2*np.pi*frequency*t)
            sf.write(cls.root/(name+'.wav'), np.column_stack([signal, signal]), 44100)
        cls.video = cls.root/'silent video.mp4'
        subprocess.run(['ffmpeg', '-v', 'error', '-y', '-f', 'lavfi', '-i',
                        f'color=c=black:s=160x120:r=25:d={cls.duration}', '-c:v', 'libx264',
                        '-pix_fmt', 'yuv420p', str(cls.video)], check=True)
        cls.with_audio = cls.root/'video with audio.mp4'
        subprocess.run(['ffmpeg', '-v', 'error', '-y', '-i', str(cls.video), '-i',
                        str(cls.root/'original.wav'), '-map', '0:v', '-map', '1:a',
                        '-c:v', 'copy', '-c:a', 'aac', '-shortest', str(cls.with_audio)], check=True)

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def render(self, name, video=None, extra=()):
        output = self.root/(name+'.mp4')
        result = subprocess.run([sys.executable, '-I', '-B', str(SCRIPTS/'mix.py'),
                                 '--video', str(video or self.video), '--bgm', str(self.root/'bgm.wav'),
                                 '--out', str(output), *extra], capture_output=True)
        self.assertEqual(result.returncode, 0, result.stderr.decode('utf-8', 'replace'))
        info = json.loads(subprocess.check_output(['ffprobe', '-v', 'error', '-show_streams',
                                                  '-of', 'json', str(output)]))
        audio = next(s for s in info['streams'] if s['codec_type'] == 'audio')
        self.assertEqual((audio['channels'], int(audio['sample_rate'])), (2, 48000))
        self.assertAlmostEqual(float(audio['duration']), self.duration, delta=.06)
        data = subprocess.check_output(['ffmpeg', '-v', 'error', '-i', str(output), '-vn', '-f', 'f32le', '-'])
        pcm = np.frombuffer(data, dtype=np.float32).reshape(-1, 2)
        self.assertTrue(np.isfinite(pcm).all())
        self.assertGreater(np.abs(pcm).max(), .01)
        self.assertLess(np.abs(pcm).max(), .999)
        return output, pcm, result

    def test_all_foreground_combinations_and_video_copy(self):
        cases = [('none', self.video, [], []),
                 ('vo', self.video, ['--vo', str(self.root/'vo.wav')], [180]),
                 ('keep', self.with_audio, ['--keep-audio'], [330]),
                 ('both', self.with_audio, ['--vo', str(self.root/'vo.wav'), '--keep-audio'], [180, 330])]
        hashes = []
        for name, video, extra, frequencies in cases:
            with self.subTest(name=name):
                output, pcm, _ = self.render(name, video, extra)
                def video_hash(path):
                    return subprocess.check_output(['ffmpeg', '-v', 'error', '-i', str(path),
                                                    '-map', '0:v', '-c', 'copy', '-f', 'hash', '-'])
                self.assertEqual(video_hash(video), video_hash(output))
                # Detect both retained foreground tones, rather than just checking file existence.
                segment = pcm[48000:96000, 0]
                spectrum = np.abs(np.fft.rfft(segment))
                for frequency in [440, *frequencies]:
                    self.assertGreater(spectrum[frequency], 10*np.median(spectrum))
                hashes.append(pcm.tobytes())
        self.assertEqual(len(set(hashes)), 4)

    def test_keep_audio_on_silent_video_matches_bgm_only(self):
        _, plain, _ = self.render('plain')
        _, kept, result = self.render('keep-silent', extra=['--keep-audio'])
        self.assertIn('忽略 --keep-audio', result.stderr.decode('utf-8'))
        np.testing.assert_array_equal(plain, kept)

    def test_custom_levels_and_explicit_fade(self):
        output, pcm, _ = self.render('custom', extra=['--bgm-db', '-12', '--duck-ratio', '3',
                                                     '--lufs', '-16', '--tp', '-3', '--fade-out', '.5'])
        self.assertLess(np.sqrt(np.mean(pcm[-4800:]**2)), np.sqrt(np.mean(pcm[48000:52800]**2))*.4)
        result = subprocess.run([sys.executable, '-I', '-B', str(SCRIPTS/'verify.py'), str(output),
                                 '--lufs', '-16', '--tp', '-3'], capture_output=True)
        self.assertEqual(result.returncode, 0)
        text = result.stdout.decode('utf-8')
        self.assertIn('[OK] 综合响度', text)
        self.assertIn('[OK] 真峰值', text)

    def test_failed_input_returns_nonzero_without_output(self):
        output = self.root/'missing-output.mp4'
        result = subprocess.run([sys.executable, '-I', '-B', str(SCRIPTS/'mix.py'),
                                 '--video', str(self.root/'missing.mp4'), '--bgm', str(self.root/'bgm.wav'),
                                 '--out', str(output)], capture_output=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse(output.exists())


class NativeDependencyTests(unittest.TestCase):
    def test_missing_required_tools_returns_nonzero(self):
        env = os.environ.copy()
        with tempfile.TemporaryDirectory() as directory:
            env['PATH'] = directory
            result = subprocess.run([sys.executable, '-I', '-B', str(SCRIPTS/'check_deps.py')],
                                    env=env, capture_output=True)
        self.assertEqual(result.returncode, 1, result.stderr.decode('utf-8', 'replace'))
        self.assertIn('[MISSING] ffmpeg', result.stdout.decode('utf-8'))
        self.assertIn('[MISSING] ffprobe', result.stdout.decode('utf-8'))


if __name__ == '__main__':
    unittest.main()
