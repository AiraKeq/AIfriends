import os
import struct

import requests
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView


def pcm_to_wav(pcm_data, sample_rate=16000):
    """前端送的是裸 PCM（16 位、单声道、16kHz），包上 WAV 头再交给识别接口。

    为什么不在前端转：
      WebAudio 能直接出 PCM，WAV 头只是 44 字节，后端拼一下最省事；
      前端拿不到录音的时长/采样率时，自己拼容易写错。
    """
    byte_rate = sample_rate * 2
    header = b'RIFF' + struct.pack('<I', 36 + len(pcm_data)) + b'WAVE'
    header += b'fmt ' + struct.pack('<IHHIIHH', 16, 1, 1, sample_rate, byte_rate, 2, 16)
    header += b'data' + struct.pack('<I', len(pcm_data))
    return header + pcm_data


class ASRView(APIView):
    """POST /api/friend/message/asr/asr/

    接收前端 VAD 切出来的 PCM，转成 WAV 交给识别接口，返回纯文本。
    识别失败要给出人能看懂的 `result`，前端会把原文吞掉而不是崩掉。
    """

    permission_classes = [IsAuthenticated]

    def post(self, request):
        audio = request.FILES.get('audio')
        if not audio:
            return Response({'result': '音频不存在'})

        wav_data = pcm_to_wav(audio.read())
        asr_url = os.getenv('ASR_URL', 'https://api.deepseek.com/v1/tools/asr')
        headers = {
            'Authorization': f"Bearer {os.getenv('API_KEY')}",
        }

        try:
            response = requests.post(
                asr_url,
                headers=headers,
                files={'file': ('voice.wav', wav_data, 'audio/wav')},
                timeout=120,
            )
            data = response.json()
        except Exception as exc:  # noqa: BLE001
            return Response({'result': f'识别失败：{exc}'})

        text = data.get('text')
        if text is None:
            return Response({'result': '识别失败', 'detail': data})
        return Response({
            'result': 'success',
            'text': text,
        })
