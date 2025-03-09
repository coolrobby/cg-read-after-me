import streamlit as st
import edge_tts
import os
import shutil
from pydub import AudioSegment
import zipfile
import asyncio

# 设置输出目录
OUTPUT_DIR = "output_audio"
if not os.path.exists(OUTPUT_DIR):
    os.makedirs(OUTPUT_DIR)

# 清理输出目录
def clear_output_dir():
    for file in os.listdir(OUTPUT_DIR):
        file_path = os.path.join(OUTPUT_DIR, file)
        if os.path.isfile(file_path):
            os.unlink(file_path)

# 常见的英文音色选项
VOICES = {
    "Guy (en-US)": "en-US-GuyNeural",
    "Jenny (en-US)": "en-US-JennyNeural",
    "Ana (en-US)": "en-US-AnaNeural",
    "Emma (en-GB)": "en-GB-EmmaNeural",
    "Ryan (en-GB)": "en-GB-RyanNeural"
}

# 速度选项（edge-tts支持的百分比格式）
SPEED_OPTIONS = {
    "Normal": "+0%",   # 默认速度
    "Slow": "-20%"     # 慢速（减慢20%）
}

# 生成语音文件
async def text_to_speech(text, voice, speed, output_file):
    communicate = edge_tts.Communicate(text, voice, rate=speed)
    await communicate.save(output_file)

# 获取当前目录下的所有txt文件
def get_txt_files():
    return [f for f in os.listdir() if f.endswith(".txt")]

# 主程序
def main():
    st.title("文字转语音 - Edge-TTS")
    
    # 清空之前的输出
    clear_output_dir()
    
    # 音色选择
    voice_name = st.selectbox("选择音色", list(VOICES.keys()))
    voice = VOICES[voice_name]
    
    # 速度选择
    speed_name = st.selectbox("选择速度", list(SPEED_OPTIONS.keys()))
    speed = SPEED_OPTIONS[speed_name]
    
    # 输入方式选择
    input_method = st.radio("选择输入方式", ("直接输入", "从TXT文件读取"))
    
    audio_files = []
    text_lines = []
    
    if input_method == "直接输入":
        user_input = st.text_area("输入你的文本（每行生成一个音频文件）")
        if st.button("生成音频"):
            if user_input:
                lines = user_input.strip().split("\n")
                for i, line in enumerate(lines):
                    if line.strip():
                        output_file = os.path.join(OUTPUT_DIR, f"audio_{i+1}.mp3")
                        asyncio.run(text_to_speech(line.strip(), voice, speed, output_file))
                        audio_files.append(output_file)
                        text_lines.append(line.strip())
                        
    else:
        txt_files = get_txt_files()
        if not txt_files:
            st.warning("当前目录下没有找到TXT文件！")
        else:
            selected_file = st.selectbox("选择一个TXT文件", txt_files)
            if st.button("生成音频"):
                with open(selected_file, "r", encoding="utf-8") as f:
                    lines = f.readlines()
                for i, line in enumerate(lines):
                    if line.strip():
                        output_file = os.path.join(OUTPUT_DIR, f"audio_{i+1}.mp3")
                        asyncio.run(text_to_speech(line.strip(), voice, speed, output_file))
                        audio_files.append(output_file)
                        text_lines.append(line.strip())
    
    # 显示和播放单独的音频文件
    if audio_files:
        st.subheader("生成的音频文件")
        for i, audio_file in enumerate(audio_files):
            st.markdown(f"<h1>{text_lines[i]}</h1>", unsafe_allow_html=True)
            st.audio(audio_file)
        
        # 合并音频文件
        combined = AudioSegment.empty()
        for audio_file in audio_files:
            sound = AudioSegment.from_mp3(audio_file)
            combined += sound
        
        combined_file = os.path.join(OUTPUT_DIR, "combined_audio.mp3")
        combined.export(combined_file, format="mp3")
        
        st.subheader("合并后的音频")
        st.audio(combined_file)
        
        # 创建下载包
        zip_file = "audio_package.zip"
        with zipfile.ZipFile(zip_file, 'w') as zipf:
            # 添加单独的音频文件
            for audio_file in audio_files:
                zipf.write(audio_file)
            # 添加合并的音频文件
            zipf.write(combined_file)
            # 添加文本列表
            with open(os.path.join(OUTPUT_DIR, "text_list.txt"), "w", encoding="utf-8") as f:
                f.write("\n".join(text_lines))
            zipf.write(os.path.join(OUTPUT_DIR, "text_list.txt"))
        
        # 提供下载按钮
        with open(zip_file, "rb") as f:
            st.download_button(
                label="下载所有音频文件",
                data=f,
                file_name="audio_package.zip",
                mime="application/zip"
            )

if __name__ == "__main__":
    main()
