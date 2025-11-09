import streamlit as st
import edge_tts
import os
import shutil
import zipfile
import asyncio
import threading
from typing import List

# -------------------------------------------------
# 1. 清理函数（安全删除）
# -------------------------------------------------
def clear_output_files(audio_files, text_file, html_files):
    for f in audio_files + html_files + [text_file]:
        try:
            if os.path.isfile(f):
                os.unlink(f)
        except Exception:
            pass

# -------------------------------------------------
# 2. 常量
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

# -------------------------------------------------
# 4. 异步生成单条音频（核心）
# -------------------------------------------------
async def generate_one_audio(text: str, voice: str, speed: str, output_file: str) -> None:
    if not text.strip():
        raise ValueError("文本为空，无法生成音频")
    text = expand_abbreviations(text)
    # 加上 pitch 参数可避免部分语音返回空音频
    communicate = edge_tts.Communicate(text, voice, rate=speed, pitch="+0Hz")
    await communicate.save(output_file)

# -------------------------------------------------
# 5. 在后台线程里批量生成音频
# -------------------------------------------------
@st.experimental_singleton
def _event_loop():
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    return loop

def run_async_in_thread(coro):
    """把 async 函数放到独立线程的事件循环里执行"""
    loop = _event_loop()
    future = asyncio.run_coroutine_threadsafe(coro, loop)
    return future.result()   # 阻塞等待结果

def generate_audios_batch(text_list: List[str], voice: str, speed: str, start_idx: int = 100):
    async def _inner():
        audio_files = []
        for idx, txt in enumerate(text_list, start=start_idx):
            out_file = f"{idx}.mp3"
            await generate_one_audio(txt, voice, speed, out_file)
            audio_files.append(out_file)
        return audio_files
    return run_async_in_thread(_inner())

# -------------------------------------------------
# 6. HTML 生成
# -------------------------------------------------
def generate_flashcard_html(audio_files, text_lines, is_txt_input=False):
    html = """<!DOCTYPE html>
<html lang="zh-CN">
<head><meta charset="UTF-8"><title>点读卡</title>
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
            html += f"""<div class="card" onclick="document.getElementById('a{i}').play()">
<h1>{eng}</h1><div class="chinese">{chn}</div>
<audio id="a{i}" src="{os.path.basename(audio)}"></audio>
<div class="watermark">设计制作: 川哥</div></div>"""
    else:
        for i, (audio, txt) in enumerate(zip(audio_files, text_lines), start=100):
            html += f"""<div class="card" onclick="document.getElementById('a{i}').play()">
<h1>{txt}</h1><audio id="a{i}" src="{os.path.basename(audio)}"></audio>
<div class="watermark">设计制作: 川哥</div></div>"""
    html += """</div></body></html>"""
    path = "flashcard.html"
    with open(path, "w", encoding="utf-8") as f:
        f.write(html)
    return path

def generate_text_list_html(text_lines, is_txt_input=False):
    html = """<!DOCTYPE html>
<html lang="zh-CN">
<head><meta charset="UTF-8"><title>文本列表</title>
<style>
body{font-family:"Times New Roman",serif;background:#f0f0f0;margin:0;padding:20px}
.list-container{max-width:800px;margin:auto}
h1{font-size:2rem;color:#333}
.chinese{font-size:1.5rem;color:#555;margin-top:5px}
hr{border:0;border-top:1px solid #ccc;margin:10px 0}
</style></head><body><div class="list-container">"""
    if is_txt_input:
        for i in range(0, len(text_lines), 2):
            html += f"<h1>{text_lines[i]}</h1><div class=\"chinese\">{text_lines[i+1]}</div><hr>"
    else:
        for t in text_lines:
            html += f"<h1>{t}</h1><hr>"
    html += """</div></body></html>"""
    path = "text_list.html"
    with open(path, "w", encoding="utf-8") as f:
        f.write(html)
    return path

# -------------------------------------------------
# 7. 主函数
# -------------------------------------------------
def main():
    st.title("英语点读卡生成器")

    voice_name = st.selectbox("选择音色", list(VOICES.keys()))
    voice = VOICES[voice_name]

    speed_name = st.selectbox("选择速度", list(SPEED_OPTIONS.keys()))
    speed = SPEED_OPTIONS[speed_name]

    input_method = st.radio("选择输入方式", ("直接输入", "从TXT文件读取"))

    audio_files = []
    text_lines = []
    zip_filename = "英语单词点读卡-设计制作：川哥.zip"

    # ------------------- 直接输入 -------------------
    if input_method == "直接输入":
        user_input = st.text_area("输入你的文本（每行生成一个音频文件）", height=200)
        if st.button("生成音频"):
            if not user_input.strip():
                st.error("请输入至少一行文字！")
            else:
                with st.spinner("正在生成音频…"):
                    lines = [l.strip() for l in user_input.split("\n") if l.strip()]
                    audio_files = generate_audios_batch(lines, voice, speed)
                    text_lines = lines
                st.success("音频生成完成！")

    # ------------------- TXT 文件 -------------------
    else:
        txt_files = get_txt_files()
        if not txt_files:
            st.warning("当前目录下没有找到 TXT 文件！")
        else:
            selected_file = st.selectbox("选择一个 TXT 文件", txt_files)
            if st.button("生成音频"):
                with open(selected_file, "r", encoding="utf-8") as f:
                    raw_lines = [l.strip() for l in f.readlines() if l.strip()]

                if len(raw_lines) % 2 != 0:
                    st.error("TXT 文件行数必须为偶数（每两行一组：英文+中文）")
                else:
                    with st.spinner("正在生成音频…"):
                        eng_lines = raw_lines[::2]
                        audio_files = generate_audios_batch(eng_lines, voice, speed)
                        text_lines = raw_lines
                        zip_filename = f"{os.path.splitext(selected_file)[0]}.zip"
                    st.success("音频生成完成！")

    # ------------------- 展示音频 -------------------
    if audio_files:
        st.subheader("生成的音频文件")
        if input_method == "直接输入":
            for i, audio in enumerate(audio_files, start=100):
                txt = text_lines[i - 100]
                st.markdown(f"<h1 style='font-family:\"Times New Roman\",serif;'>{txt}</h1>", unsafe_allow_html=True)
                st.audio(audio)
        else:
            for i, audio in enumerate(audio_files, start=100):
                eng = text_lines[(i - 100) * 2]
                chn = text_lines[(i - 100) * 2 + 1]
                st.markdown(
                    f"<h1 style='font-family:\"Times New Roman\",serif;'>{eng}</h1>"
                    f"<div style='font-family:\"Times New Roman\",serif;font-size:1.5rem;color:#555;margin-top:5px;'>{chn}</div>",
                    unsafe_allow_html=True,
                )
                st.audio(audio)

        # ------------------- 生成 HTML & ZIP -------------------
        flashcard_html = generate_flashcard_html(audio_files, text_lines, is_txt_input=(input_method != "直接输入"))
        text_list_html = generate_text_list_html(text_lines, is_txt_input=(input_method != "直接输入"))

        txt_list_file = "text_list.txt"
        with open(txt_list_file, "w", encoding="utf-8") as f:
            f.write("\n".join(text_lines))

        with zipfile.ZipFile(zip_filename, "w") as z:
            for f in audio_files + [txt_list_file, flashcard_html, text_list_html]:
                if os.path.isfile(f):
                    z.write(f)

        with open(zip_filename, "rb") as f:
            st.download_button(
                label="下载所有文件（音频+列表+HTML）",
                data=f,
                file_name=zip_filename,
                mime="application/zip",
            )

        # ------------------- 清理 -------------------
        clear_output_files(audio_files, txt_list_file, [flashcard_html, text_list_html])

if __name__ == "__main__":
    main()
