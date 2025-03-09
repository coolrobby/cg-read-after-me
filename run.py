import streamlit as st
import edge_tts
import os
import shutil
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

# 缩写转换字典
ABBREVIATIONS = {
    "sb.": "somebody",
    "sth.": "something",
    "smb.": "somebody",
    "smt.": "something",
    "e.g.": "for example",
    "i.e.": "that is"
}

# 转换缩写为全写
def expand_abbreviations(text):
    for abbr, full in ABBREVIATIONS.items():
        text = text.replace(abbr, full)
    return text

# 生成语音文件
async def text_to_speech(text, voice, speed, output_file):
    communicate = edge_tts.Communicate(text, voice, rate=speed)
    await communicate.save(output_file)

# 获取当前目录下的所有txt文件，排除requirements.txt
def get_txt_files():
    return [f for f in os.listdir() if f.endswith(".txt") and f != "requirements.txt"]

# 生成HTML点读卡页面
def generate_flashcard_html(audio_files, text_lines):
    html_content = """
    <!DOCTYPE html>
    <html lang="zh-CN">
    <head>
        <meta charset="UTF-8">
        <title>点读卡</title>
        <style>
            body {
                font-family: "Times New Roman", serif;
                background-color: #f0f0f0;
                margin: 0;
                padding: 20px;
            }
            .card-container {
                max-width: 800px;
                margin: 0 auto;
            }
            .card {
                position: relative;
                background-color: white;
                border-radius: 10px;
                box-shadow: 0 4px 8px rgba(0,0,0,0.1);
                margin-bottom: 20px;
                padding: 20px;
                cursor: pointer;
                transition: transform 0.2s;
            }
            .card:hover {
                transform: scale(1.02);
                background-color: #e0f7fa;
            }
            h1 {
                margin: 0;
                font-size: 2rem;
                color: #333;
            }
            audio {
                display: none;
            }
            .watermark {
                position: absolute;
                bottom: 5px;
                right: 15px; /* 增加右边距 */
                font-size: 1rem; /* 修改为1rem */
                color: #888;
                font-family: "Times New Roman", serif;
            }
        </style>
    </head>
    <body>
        <div class="card-container">
    """
    
    for i, (audio_file, text) in enumerate(zip(audio_files, text_lines)):
        audio_path = os.path.basename(audio_file)
        html_content += f"""
            <div class="card" onclick="document.getElementById('audio_{i}').play()">
                <h1>{text}</h1>
                <audio id="audio_{i}" src="{audio_path}"></audio>
                <div class="watermark">设计制作: 川哥</div>
            </div>
        """
    
    html_content += """
        </div>
    </body>
    </html>
    """
    
    with open(os.path.join(OUTPUT_DIR, "flashcard.html"), "w", encoding="utf-8") as f:
        f.write(html_content)
    return os.path.join(OUTPUT_DIR, "flashcard.html")

# 生成text_list.html页面
def generate_text_list_html(text_lines):
    html_content = """
    <!DOCTYPE html>
    <html lang="zh-CN">
    <head>
        <meta charset="UTF-8">
        <title>文本列表</title>
        <style>
            body {
                font-family: "Times New Roman", serif;
                background-color: #f0f0f0;
                margin: 0;
                padding: 20px;
            }
            .list-container {
                max-width: 800px;
                margin: 0 auto;
            }
            h1 {
                font-size: 2rem;
                color: #333;
            }
            hr {
                border: 0;
                border-top: 1px solid #ccc;
                margin: 10px 0;
            }
        </style>
    </head>
    <body>
        <div class="list-container">
    """
    
    for text in text_lines:
        html_content += f"""
            <h1>{text}</h1>
            <hr>
        """
    
    html_content += """
        </div>
    </body>
    </html>
    """
    
    with open(os.path.join(OUTPUT_DIR, "text_list.html"), "w", encoding="utf-8") as f:
        f.write(html_content)
    return os.path.join(OUTPUT_DIR, "text_list.html")

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
                        expanded_line = expand_abbreviations(line.strip())
                        output_file = os.path.join(OUTPUT_DIR, f"audio_{i+1}.mp3")
                        asyncio.run(text_to_speech(expanded_line, voice, speed, output_file))
                        audio_files.append(output_file)
                        text_lines.append(line.strip())  # 显示原始文本
                        
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
                        expanded_line = expand_abbreviations(line.strip())
                        output_file = os.path.join(OUTPUT_DIR, f"audio_{i+1}.mp3")
                        asyncio.run(text_to_speech(expanded_line, voice, speed, output_file))
                        audio_files.append(output_file)
                        text_lines.append(line.strip())  # 显示原始文本
    
    # 显示和播放单独的音频文件
    if audio_files:
        st.subheader("生成的音频文件")
        for i, audio_file in enumerate(audio_files):
            st.markdown(f"<h1 style='font-family: \"Times New Roman\", serif;'>{text_lines[i]}</h1>", unsafe_allow_html=True)
            st.audio(audio_file)
        
        # 生成两个HTML文件
        flashcard_html = generate_flashcard_html(audio_files, text_lines)
        text_list_html = generate_text_list_html(text_lines)
        
        # 创建下载包
        zip_file = "audio_package_设计制作：川哥.zip"
        with zipfile.ZipFile(zip_file, 'w') as zipf:
            # 添加单独的音频文件
            for audio_file in audio_files:
                zipf.write(audio_file)
            # 添加文本列表
            with open(os.path.join(OUTPUT_DIR, "text_list.txt"), "w", encoding="utf-8") as f:
                f.write("\n".join(text_lines))
            zipf.write(os.path.join(OUTPUT_DIR, "text_list.txt"))
            # 添加两个HTML文件
            zipf.write(flashcard_html)
            zipf.write(text_list_html)
        
        # 提供下载按钮
        with open(zip_file, "rb") as f:
            st.download_button(
                label="下载所有文件（音频+单词列表+HTML）",
                data=f,
                file_name="audio_package_设计制作：川哥.zip",
                mime="application/zip"
            )

if __name__ == "__main__":
    main()
