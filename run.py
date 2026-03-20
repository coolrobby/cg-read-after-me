import streamlit as st
import edge_tts
import os
import zipfile
import asyncio
from typing import List
import time
import io
from shutil import which
from pydub import AudioSegment

# -------------------------------------------------
# 1. 清理函数
# -------------------------------------------------
def clear_output_files(audio_files, text_file, html_files):
    for f in audio_files + html_files + [text_file]:
        try:
            if os.path.isfile(f):
                os.unlink(f)
        except Exception:
            pass

def cleanup_after_download():
    """下载完成后的清理回调函数"""
    audio_files = st.session_state.audio_files
    zip_filename = st.session_state.zip_filename
    
    clear_output_files(audio_files, "text_list.txt", ["flashcard.html", "text_list.html"])
    for f in [zip_filename] + audio_files:
        try:
            if os.path.isfile(f):
                os.unlink(f)
        except:
            pass
    
    st.session_state.audio_files = []
    st.session_state.text_lines = []
    st.session_state.zip_data = None
    st.session_state.merged_mp3_data = None
    st.session_state.merged_mp3_filename = "merged_audio.mp3"
    st.session_state.merged_mp3_signature = None
    st.session_state.generated_input_method = "直接输入"

# -------------------------------------------------
# 2. 常量（不变）
# -------------------------------------------------
VOICES = {
    "Guy (en-US)": "en-US-GuyNeural",
    "Jenny (en-US)": "en-US-JennyNeural",
    "Ana (en-US)": "en-US-AnaNeural",
    "Emma (en-GB)": "en-GB-EmmaNeural",
    "Ryan (en-GB)": "en-GB-RyanNeural",
    "Xiaoxiao (zh-CN)": "zh-CN-XiaoxiaoNeural",
    "Yunyang (zh-CN)": "zh-CN-YunyangNeural",
    "Yunxi (zh-CN)": "zh-CN-YunxiNeural",
    "Xiaohan (zh-CN)": "zh-CN-XiaohanNeural",
    "Yunjian (zh-CN)": "zh-CN-YunjianNeural",
    "Ava (en-US Multilingual)": "en-US-AvaMultilingualNeural",
    "Emma (en-US Multilingual)": "en-US-EmmaMultilingualNeural",
    "Sonia (en-GB)": "en-GB-SoniaNeural",
    "Carly (en-AU)": "en-AU-CarlyMultilingualNeural",
    "Xiaoyi (zh-CN)": "zh-CN-XiaoyiNeural",
    "Yunye (zh-CN)": "zh-CN-YunyeNeural",
    "Xiaomeng (zh-CN)": "zh-CN-XiaomengNeural",
    "Tom (en-US)": "en-US-TomNeural",
    "Amy (en-GB)": "en-GB-AmyNeural",
    "David (en-GB)": "en-GB-DavidNeural",
    "Linda (en-US)": "en-US-LindaNeural",
    "Mark (en-US)": "en-US-MarkNeural",
}

SPEED_OPTIONS = {
    "Normal": "+0%",
    "Slow": "-20%",
}

ABBREVIATIONS = {
    "sb.": "somebody",
    "sth.": "something",
    "smb.": "somebody",
    "smt.": "something",
    "e.g.": "for example",
    "i.e.": "that is",
}

# -------------------------------------------------
# 3. 辅助函数
# -------------------------------------------------
def expand_abbreviations(text: str) -> str:
    for abbr, full in ABBREVIATIONS.items():
        text = text.replace(abbr, full)
    return text

def get_txt_files() -> List[str]:
    return [f for f in os.listdir() if f.endswith(".txt") and f != "requirements.txt"]

_FFMPEG_READY = None
_SILENCE_SEGMENT_CACHE = {}

def ensure_ffmpeg_for_pydub() -> bool:
    global _FFMPEG_READY
    if _FFMPEG_READY is not None:
        return _FFMPEG_READY

    system_ffmpeg = which("ffmpeg")
    if system_ffmpeg:
        AudioSegment.converter = system_ffmpeg
        AudioSegment.ffmpeg = system_ffmpeg
        _FFMPEG_READY = True
        return True

    _FFMPEG_READY = False
    return False

def _strip_id3v1_tag(mp3_bytes: bytes) -> bytes:
    if len(mp3_bytes) >= 128 and mp3_bytes[-128:-125] == b"TAG":
        return mp3_bytes[:-128]
    return mp3_bytes

def _strip_leading_id3v2_tag(mp3_bytes: bytes) -> bytes:
    if len(mp3_bytes) < 10 or mp3_bytes[:3] != b"ID3":
        return mp3_bytes
    tag_size = (
        ((mp3_bytes[6] & 0x7F) << 21)
        | ((mp3_bytes[7] & 0x7F) << 14)
        | ((mp3_bytes[8] & 0x7F) << 7)
        | (mp3_bytes[9] & 0x7F)
    )
    data_start = 10 + tag_size
    if data_start >= len(mp3_bytes):
        return b""
    return mp3_bytes[data_start:]

def _parse_mp3_frames(mp3_bytes: bytes):
    frame_info = []
    idx = 0
    while idx + 4 <= len(mp3_bytes):
        b1, b2, b3, _ = mp3_bytes[idx], mp3_bytes[idx + 1], mp3_bytes[idx + 2], mp3_bytes[idx + 3]
        if b1 != 0xFF or (b2 & 0xE0) != 0xE0:
            idx += 1
            continue

        version_bits = (b2 >> 3) & 0x03
        layer_bits = (b2 >> 1) & 0x03
        bitrate_index = (b3 >> 4) & 0x0F
        sample_rate_index = (b3 >> 2) & 0x03
        padding = (b3 >> 1) & 0x01

        if (
            layer_bits != 0x01
            or version_bits == 0x01
            or bitrate_index in (0, 0x0F)
            or sample_rate_index == 0x03
        ):
            idx += 1
            continue

        if version_bits == 0x03:  # MPEG1, Layer III
            sample_rates = [44100, 48000, 32000]
            bitrates = [0, 32, 40, 48, 56, 64, 80, 96, 112, 128, 160, 192, 224, 256, 320, 0]
            samples_per_frame = 1152
            sample_rate = sample_rates[sample_rate_index]
            bitrate = bitrates[bitrate_index] * 1000
            frame_length = int((144 * bitrate) / sample_rate + padding)
        elif version_bits == 0x02:  # MPEG2, Layer III
            sample_rates = [22050, 24000, 16000]
            bitrates = [0, 8, 16, 24, 32, 40, 48, 56, 64, 80, 96, 112, 128, 144, 160, 0]
            samples_per_frame = 576
            sample_rate = sample_rates[sample_rate_index]
            bitrate = bitrates[bitrate_index] * 1000
            frame_length = int((72 * bitrate) / sample_rate + padding)
        else:  # MPEG2.5, Layer III
            sample_rates = [11025, 12000, 8000]
            bitrates = [0, 8, 16, 24, 32, 40, 48, 56, 64, 80, 96, 112, 128, 144, 160, 0]
            samples_per_frame = 576
            sample_rate = sample_rates[sample_rate_index]
            bitrate = bitrates[bitrate_index] * 1000
            frame_length = int((72 * bitrate) / sample_rate + padding)

        if frame_length <= 0 or idx + frame_length > len(mp3_bytes):
            idx += 1
            continue

        frame_info.append((idx, idx + frame_length, samples_per_frame / sample_rate))
        idx += frame_length

    return frame_info

def build_silence_mp3_segment(gap_seconds: float) -> bytes:
    if gap_seconds <= 0:
        return b""

    cache_key = round(gap_seconds, 3)
    if cache_key in _SILENCE_SEGMENT_CACHE:
        return _SILENCE_SEGMENT_CACHE[cache_key]

    silence_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "silence_1s.mp3")
    if not os.path.isfile(silence_path):
        raise ValueError("缺少 silence_1s.mp3，无法在无 ffmpeg 环境插入间隔。")

    with open(silence_path, "rb") as f:
        silence_bytes = f.read()

    silence_bytes = _strip_id3v1_tag(_strip_leading_id3v2_tag(silence_bytes))
    frames = _parse_mp3_frames(silence_bytes)
    if not frames:
        raise ValueError("silence_1s.mp3 无有效 MP3 帧，无法用于间隔拼接。")

    base_duration = sum(frame_duration for _, _, frame_duration in frames)
    if base_duration <= 0:
        raise ValueError("silence_1s.mp3 时长异常，无法用于间隔拼接。")

    output = bytearray()
    full_repeats = int(gap_seconds // base_duration)
    remainder = max(gap_seconds - (full_repeats * base_duration), 0.0)

    for _ in range(full_repeats):
        output.extend(silence_bytes)

    if remainder > 0:
        elapsed = 0.0
        end_pos = 0
        for _, frame_end, frame_duration in frames:
            end_pos = frame_end
            elapsed += frame_duration
            if elapsed >= remainder:
                break
        output.extend(silence_bytes[:end_pos])

    segment = bytes(output)
    _SILENCE_SEGMENT_CACHE[cache_key] = segment
    return segment

def merge_audio_files_to_mp3(
    audio_files: List[str],
    repeat_times: int = 3,
    gap_seconds: float = 2.0,
    repeat_gap_seconds: float = 1.0,
) -> bytes:
    if not audio_files:
        raise ValueError("没有可合并的音频文件。")
    if repeat_times < 1:
        raise ValueError("每行朗读次数必须大于等于 1。")
    if gap_seconds < 0:
        raise ValueError("行间间隔不能小于 0 秒。")
    if repeat_gap_seconds < 0:
        raise ValueError("重复间隔不能小于 0 秒。")

    gap_ms = int(round(gap_seconds * 1000))
    repeat_gap_ms = int(round(repeat_gap_seconds * 1000))

    ffmpeg_ready = ensure_ffmpeg_for_pydub()
    if ffmpeg_ready:
        # 优先使用 pydub 重新编码，保证兼容性并支持行间静音。
        try:
            merged_audio = AudioSegment.empty()
            line_silence_segment = AudioSegment.silent(duration=gap_ms) if gap_ms > 0 else None
            repeat_silence_segment = AudioSegment.silent(duration=repeat_gap_ms) if repeat_gap_ms > 0 else None

            for i, file_path in enumerate(audio_files):
                one_line_audio = AudioSegment.from_file(file_path, format="mp3")
                for repeat_index in range(repeat_times):
                    merged_audio += one_line_audio
                    if repeat_silence_segment is not None and repeat_index < repeat_times - 1:
                        merged_audio += repeat_silence_segment
                if line_silence_segment is not None and i < len(audio_files) - 1:
                    merged_audio += line_silence_segment

            buffer = io.BytesIO()
            merged_audio.export(buffer, format="mp3")
            return buffer.getvalue()
        except Exception:
            # 回退到二进制拼接，避免 ffmpeg 路径存在但处理失败时完全不可用。
            pass

    # 无可用 ffmpeg 时，回退到二进制拼接，并通过 silence_1s.mp3 插入行间静音。
    line_gap_bytes = b""
    repeat_gap_bytes = b""
    if gap_ms > 0:
        line_gap_bytes = build_silence_mp3_segment(gap_seconds)
    if repeat_gap_ms > 0:
        repeat_gap_bytes = build_silence_mp3_segment(repeat_gap_seconds)

    merged_bytes = bytearray()
    for file_index, file_path in enumerate(audio_files):
        with open(file_path, "rb") as f:
            chunk = f.read()
        chunk = _strip_id3v1_tag(chunk)
        for repeat_index in range(repeat_times):
            chunk_to_append = chunk
            if file_index > 0 or repeat_index > 0:
                chunk_to_append = _strip_leading_id3v2_tag(chunk_to_append)
            merged_bytes.extend(chunk_to_append)
            if repeat_gap_bytes and repeat_index < repeat_times - 1:
                merged_bytes.extend(repeat_gap_bytes)
        if line_gap_bytes and file_index < len(audio_files) - 1:
            merged_bytes.extend(line_gap_bytes)
    if not merged_bytes:
        raise ValueError("合并失败：无法读取任何音频数据。")
    return bytes(merged_bytes)

# -------------------------------------------------
# 4. 异步生成单条音频（带重试）
# -------------------------------------------------
async def generate_one_audio(text: str, voice: str, speed: str, output_file: str) -> bool:
    if not text.strip() or len(text) > 100:  # 截断长文本
        text = text[:100] + "..."
    text = expand_abbreviations(text)
    try:
        communicate = edge_tts.Communicate(text, voice, rate=speed, pitch="+0Hz")
        await communicate.save(output_file)
        if os.path.exists(output_file) and os.path.getsize(output_file) > 0:
            return True
        else:
            if os.path.exists(output_file):
                os.remove(output_file)
            return False
    except Exception as e:
        st.error(f"生成 {output_file} 失败：{str(e)}")
        return False

# -------------------------------------------------
# 5. 批量生成（一次性异步，无 rerun）
# -------------------------------------------------
async def generate_audios_async(text_list: List[str], voice: str, speed: str, start_idx: int = 100):
    tasks = []
    for i, text in enumerate(text_list):
        out_file = f"{start_idx + i}.mp3"
        tasks.append(generate_one_audio(text, voice, speed, out_file))
    results = await asyncio.gather(*tasks, return_exceptions=True)
    audio_files = [f"{start_idx + i}.mp3" for i, res in enumerate(results) if isinstance(res, bool) and res]
    return audio_files

def generate_audios_batch(text_list: List[str], voice: str, speed: str, start_idx: int = 100):
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        audio_files = loop.run_until_complete(generate_audios_async(text_list, voice, speed, start_idx))
        return audio_files
    finally:
        loop.close()

# -------------------------------------------------
# 6. HTML 生成（不变）
# -------------------------------------------------
def generate_flashcard_html(audio_files, text_lines, is_txt_input=False):
    html = """<!DOCTYPE html>
<html lang="zh-CN"><head><meta charset="UTF-8"><title>点读卡</title>
<style>
body{font-family:"Times New Roman",serif;background:#f0f0f0;margin:0;padding:20px}
.card-container{max-width:800px;margin:auto}
.card{position:relative;background:white;border-radius:10px;box-shadow:0 4px 8px rgba(0,0,0,.1);
margin-bottom:20px;padding:20px;cursor:pointer;transition:.2s}
.card:hover{transform:scale(1.02);background:#e0f7fa}
h1{margin:0;font-size:2rem;color:#333}
.chinese{font-size:1.5rem;color:#555;margin-top:5px}
audio{display:none}
.watermark{position:absolute;bottom:5px;right:15px;font-size:1rem;color:#888}
</style></head><body><div class="card-container">"""

    if is_txt_input:
        for i, audio in enumerate(audio_files, start=100):
            eng = text_lines[(i - 100) * 2]
            chn = text_lines[(i - 100) * 2 + 1]
            html += f'<div class="card" onclick="document.getElementById(\'a{i}\').play()">'
            html += f"<h1>{eng}</h1><div class='chinese'>{chn}</div>"
            html += f"<audio id='a{i}' src='{os.path.basename(audio)}'></audio>"
            html += "<div class='watermark'>设计制作: 川哥</div></div>"
    else:
        for i, (audio, txt) in enumerate(zip(audio_files, text_lines), start=100):
            html += f'<div class="card" onclick="document.getElementById(\'a{i}\').play()">'
            html += f"<h1>{txt}</h1>"
            html += f"<audio id='a{i}' src='{os.path.basename(audio)}'></audio>"
            html += "<div class='watermark'>设计制作: 川哥</div></div>"

    html += "</div></body></html>"
    path = "flashcard.html"
    with open(path, "w", encoding="utf-8") as f:
        f.write(html)
    return path

def generate_text_list_html(text_lines, is_txt_input=False):
    html = """<!DOCTYPE html>
<html lang="zh-CN"><head><meta charset="UTF-8"><title>文本列表</title>
<style>
body{font-family:"Times New Roman",serif;background:#f0f0f0;margin:0;padding:20px}
.list-container{max-width:800px;margin:auto}
h1{font-size:2rem;color:#333}
.chinese{font-size:1.5rem;color:#555;margin-top:5px}
hr{border:0;border-top:1px solid #ccc;margin:10px 0}
</style></head><body><div class="list-container">"""

    if is_txt_input:
        for i in range(0, len(text_lines), 2):
            html += f"<h1>{text_lines[i]}</h1><div class='chinese'>{text_lines[i+1]}</div><hr>"
    else:
        for t in text_lines:
            html += f"<h1>{t}</h1><hr>"

    html += "</div></body></html>"
    path = "text_list.html"
    with open(path, "w", encoding="utf-8") as f:
        f.write(html)
    return path

# -------------------------------------------------
# 7. 主函数
# -------------------------------------------------
def main():
    st.set_page_config(page_title="川哥文本转语音", layout="wide", initial_sidebar_state="expanded")
    st.markdown(
        """
        <style>
        .main .block-container {max-width: 1200px; padding-top: 1.2rem; padding-bottom: 2.5rem;}
        [data-testid="stSidebar"] {background: linear-gradient(180deg, #f5f8ff 0%, #f4fbf8 100%);}
        .hero-box {
            border: 1px solid #dbe5f6;
            border-radius: 18px;
            padding: 18px 20px;
            background: linear-gradient(135deg, #f7fbff 0%, #f2f8ff 45%, #f5fff8 100%);
            margin-bottom: 14px;
        }
        .hero-title {font-size: 2rem; font-weight: 800; color: #1a365d; margin: 0;}
        .hero-subtitle {font-size: 0.98rem; color: #395575; margin-top: 6px;}
        .preview-card {
            border: 1px solid #dfe8ef;
            border-radius: 14px;
            background: #fbfdff;
            padding: 12px 14px 10px 14px;
            margin: 12px 0 8px 0;
        }
        .preview-title {
            font-family: "Times New Roman", serif;
            font-size: 1.9rem;
            color: #243b53;
            margin: 0;
        }
        .preview-subtitle {
            font-family: "Times New Roman", serif;
            font-size: 1.2rem;
            color: #486581;
            margin-top: 4px;
        }
        .empty-box {
            border: 1px dashed #c7d7eb;
            border-radius: 14px;
            background: #f8fbff;
            padding: 22px;
            color: #4d6480;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

    st.markdown(
        """
        <div class="hero-box">
            <h1 class="hero-title">川哥文本转语音</h1>
            <div class="hero-subtitle">左侧功能区负责设置与输入，右侧显示区查看音频预览并下载结果。</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    if "audio_files" not in st.session_state:
        st.session_state.audio_files = []
    if "text_lines" not in st.session_state:
        st.session_state.text_lines = []
    if "zip_filename" not in st.session_state:
        st.session_state.zip_filename = "英语单词点读卡-设计制作：川哥.zip"
    if "zip_data" not in st.session_state:
        st.session_state.zip_data = None
    if "merged_mp3_data" not in st.session_state:
        st.session_state.merged_mp3_data = None
    if "merged_mp3_filename" not in st.session_state:
        st.session_state.merged_mp3_filename = "merged_audio.mp3"
    if "merged_mp3_signature" not in st.session_state:
        st.session_state.merged_mp3_signature = None
    if "merged_repeat_times" not in st.session_state:
        st.session_state.merged_repeat_times = 3
    if "merged_gap_seconds" not in st.session_state:
        st.session_state.merged_gap_seconds = 2.0
    if "merged_repeat_gap_seconds" not in st.session_state:
        st.session_state.merged_repeat_gap_seconds = 1.0
    if "generated_input_method" not in st.session_state:
        st.session_state.generated_input_method = "直接输入"

    with st.sidebar:
        st.markdown("## 功能区")
        voice_name = st.selectbox("选择音色", list(VOICES.keys()))
        speed_name = st.selectbox("选择速度", list(SPEED_OPTIONS.keys()))
        input_method = st.radio("选择输入方式", ("直接输入", "从TXT文件读取"))

        user_input = ""
        selected_file = None
        disable_generate = False

        st.markdown("### 输入区")
        if input_method == "直接输入":
            user_input = st.text_area("文本内容（每行生成一个音频）", height=220, placeholder="例如：\nhello\nthank you")
        else:
            txt_files = get_txt_files()
            if not txt_files:
                st.warning("当前目录下没有找到 TXT 文件。")
                disable_generate = True
            else:
                selected_file = st.selectbox("选择一个 TXT 文件", txt_files)

        st.markdown("### 合并设置")
        repeat_times = int(
            st.number_input(
                "每行朗读次数",
                min_value=1,
                max_value=10,
                step=1,
                key="merged_repeat_times",
            )
        )
        repeat_gap_seconds = float(
            st.number_input(
                "重复间隔（秒）",
                min_value=0.0,
                max_value=10.0,
                step=0.5,
                key="merged_repeat_gap_seconds",
            )
        )
        gap_seconds = float(
            st.number_input(
                "行间间隔（秒）",
                min_value=0.0,
                max_value=10.0,
                step=0.5,
                key="merged_gap_seconds",
            )
        )

        generate_audio = st.button("生成音频", type="primary", use_container_width=True, disabled=disable_generate)

    voice = VOICES[voice_name]
    speed = SPEED_OPTIONS[speed_name]

    if generate_audio:
        st.write("🔄 开始处理...")
        if input_method == "直接输入":
            if not user_input.strip():
                st.error("请输入至少一行文字！")
            else:
                lines = [l.strip() for l in user_input.split("\n") if l.strip()]
                if lines:
                    with st.spinner(f"生成音频中（共 {len(lines)} 行）..."):
                        try:
                            audio_files = generate_audios_batch(lines, voice, speed)
                            st.session_state.audio_files = audio_files
                            st.session_state.text_lines = lines
                            st.session_state.zip_filename = "英语单词点读卡-设计制作：川哥.zip"
                            st.session_state.generated_input_method = "直接输入"
                            st.session_state.merged_mp3_data = None
                            st.session_state.merged_mp3_signature = None
                            if audio_files:
                                st.success(f"✅ 成功生成 {len(audio_files)} 个音频！")
                            else:
                                st.error("❌ 生成失败：检查 edge_tts API 或网络。")
                        except Exception as e:
                            st.error(f"❌ 异常：{str(e)}")
        else:
            if not selected_file:
                st.error("请先选择 TXT 文件。")
            else:
                try:
                    with open(selected_file, "r", encoding="utf-8") as f:
                        raw_lines = [l.strip() for l in f.readlines() if l.strip()]

                    if len(raw_lines) % 2 != 0:
                        st.error("TXT 文件行数必须为偶数（每两行一组：英文+中文）")
                    else:
                        eng_lines = raw_lines[::2]
                        with st.spinner(f"生成音频中（共 {len(eng_lines)} 行英文）..."):
                            audio_files = generate_audios_batch(eng_lines, voice, speed)
                            st.session_state.audio_files = audio_files
                            st.session_state.text_lines = raw_lines
                            st.session_state.zip_filename = f"{os.path.splitext(selected_file)[0]}.zip"
                            st.session_state.generated_input_method = "从TXT文件读取"
                            st.session_state.merged_mp3_data = None
                            st.session_state.merged_mp3_signature = None
                            if audio_files:
                                st.success(f"✅ 成功生成 {len(audio_files)} 个音频！")
                            else:
                                st.error("❌ 生成失败：检查 edge_tts API 或网络。")
                except Exception as e:
                    st.error(f"❌ 读取/生成失败：{str(e)}")

    audio_files = st.session_state.audio_files
    text_lines = st.session_state.text_lines
    zip_filename = st.session_state.zip_filename
    display_input_method = st.session_state.generated_input_method

    st.markdown("### 显示区")
    if not audio_files:
        st.markdown(
            """
            <div class="empty-box">
                还没有生成音频。请在左侧功能区完成设置并点击“生成音频”。
            </div>
            """,
            unsafe_allow_html=True,
        )
        return

    if display_input_method == "直接输入":
        for i, audio in enumerate(audio_files, start=100):
            txt = text_lines[i - 100]
            st.markdown(
                f"""
                <div class="preview-card">
                    <h3 class="preview-title">{txt}</h3>
                </div>
                """,
                unsafe_allow_html=True,
            )
            st.audio(audio)
    else:
        for i, audio in enumerate(audio_files, start=100):
            eng = text_lines[(i - 100) * 2]
            chn = text_lines[(i - 100) * 2 + 1]
            st.markdown(
                f"""
                <div class="preview-card">
                    <h3 class="preview-title">{eng}</h3>
                    <div class="preview-subtitle">{chn}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )
            st.audio(audio)

    merge_signature = (tuple(audio_files), repeat_times, repeat_gap_seconds, gap_seconds)
    if (
        st.session_state.merged_mp3_data is None
        or st.session_state.merged_mp3_signature != merge_signature
    ):
        try:
            st.session_state.merged_mp3_data = merge_audio_files_to_mp3(
                audio_files,
                repeat_times=repeat_times,
                gap_seconds=gap_seconds,
                repeat_gap_seconds=repeat_gap_seconds,
            )
            st.session_state.merged_mp3_signature = merge_signature
            repeat_gap_label = str(repeat_gap_seconds).replace(".", "p")
            gap_label = str(gap_seconds).replace(".", "p")
            st.session_state.merged_mp3_filename = (
                f"{os.path.splitext(zip_filename)[0]}-x{repeat_times}-rgap{repeat_gap_label}s-gap{gap_label}s.mp3"
            )
        except Exception as e:
            st.session_state.merged_mp3_data = None
            st.error(f"合并 MP3 失败：{e}")

    try:
        is_txt = (display_input_method != "直接输入")
        flashcard_html = generate_flashcard_html(audio_files, text_lines, is_txt_input=is_txt)
        text_list_html = generate_text_list_html(text_lines, is_txt_input=is_txt)

        txt_list_file = "text_list.txt"
        with open(txt_list_file, "w", encoding="utf-8") as f:
            f.write("\n".join(text_lines))

        with zipfile.ZipFile(zip_filename, "w") as z:
            for f in [txt_list_file, flashcard_html, text_list_html] + audio_files:
                if os.path.isfile(f):
                    z.write(f)

        with open(zip_filename, "rb") as f:
            st.session_state.zip_data = f.read()

    except Exception as e:
        st.error(f"打包失败：{e}")

    download_col1, download_col2 = st.columns(2)
    if st.session_state.merged_mp3_data:
        download_col1.download_button(
            label="生成MP3",
            data=st.session_state.merged_mp3_data,
            file_name=st.session_state.merged_mp3_filename,
            mime="audio/mpeg",
            use_container_width=True,
        )

    if st.session_state.zip_data:
        download_col2.download_button(
            label="下载所有文件（音频+列表+HTML）",
            data=st.session_state.zip_data,
            file_name=zip_filename,
            mime="application/zip",
            on_click=cleanup_after_download,
            use_container_width=True,
        )

if __name__ == "__main__":
    main()
