import streamlit as st
import edge_tts
import os
import shutil
import zipfile
import asyncio

# 清理输出文件（仅清理特定文件，避免影响其他文件）
def clear_output_files(audio_files, text_file, html_files):
    for file in audio_files:
        if os.path.isfile(file):
            os.unlink(file)
    for file in html_files:
        if os.path.isfile(file):
            os.unlink(file)
    if os.path.isfile(text_file):
        os.unlink(text_file)

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
def generate_flashcard_html(audio_files, text_lines, is_txt_input=False):
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
            .chinese {
                font-size: 1.5rem; /* 中文字体比英文小 */
                color: #555;
                margin-top: 5px;
            }
            audio {
                display: none;
            }
            .watermark {
                position: absolute;
                bottom: 5px;
                right: 15px;
                font-size: 1rem;
                color: #888;
                font-family: "Times New Roman", serif;
            }
        </style>
    </head>
    <body>
        <div class="card-container">
    """
    
    if is_txt_input:
        for i, audio_file in enumerate(audio_files):
            audio_path = os.path.basename(audio_file)
            english_text = text_lines[i * 2]  # 每组第一行（英文）
            chinese_text = text_lines[i * 2 + 1]  # 每组第二行（中文）
            html_content += f"""
                <div class="card" onclick="document.getElementById('audio_{i}').play()">
                    <h1>{english_text}</h1>
                    <div class="chinese">{chinese_text}</div>
                    <audio id="audio_{i}" src="{audio_path}"></audio>
                    <div class="watermark">设计制作: 川哥</div>
                </div>
            """
    else:
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
    
    flashcard_file = "flashcard.html"
    with open(flashcard_file, "w", encoding="utf-8") as f:
        f.write(html_content)
    return flashcard_file

# 生成text_list.html页面
def generate_text_list_html(text_lines, is_txt_input=False):
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
            .chinese {
                font-size: 1.5rem; /* 中文字体比英文小 */
                color: #555;
                margin-top: 5px;
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
    
    if is_txt_input:
        for i in range(0, len(text_lines), 2):
            english_text = text_lines[i]
            chinese_text = text_lines[i + 1]
            html_content += f"""
                <h1>{english_text}</h1>
                <div class="chinese">{chinese_text}</div>
                <hr>
            """
    else:
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
    
    text_list_file = "text_list.html"
    with open(text_list_file, "w", encoding="utf-8") as f:
        f.write(html_content)
    return text_list_file

# 主程序
def main():
    st.title("英语点读卡生成器")
    
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
    zip_filename = "英语单词点读卡-设计制作：川哥.zip"  # 默认文件名
    
    if input_method == "直接输入":
        user_input = st.text_area("输入你的文本（每行生成一个音频文件）")
        if st.button("生成音频"):
            if user_input:
                lines = user_input.strip().split("\n")
                for i, line in enumerate(lines):
                    if line.strip():
                        expanded_line = expand_abbreviations(line.strip())
                        output_file = f"audio_{i+1}.mp3"
                        asyncio.run(text_to_speech(expanded_line, voice, speed, output_file))
                        audio_files.append(output_file)
                        text_lines.append(line.strip())  # 显示原始文本
                zip_filename = "英语单词点读卡-设计制作：川哥.zip"
    
    else:
        txt_files = get_txt_files()
        if not txt_files:
            st.warning("当前目录下没有找到TXT文件！")
        else:
            selected_file = st.selectbox("选择一个TXT文件", txt_files)
            if st.button("生成音频"):
                with open(selected_file, "r", encoding="utf-8") as f:
                    lines = f.readlines()
                # 确保行数为偶数（每两行一组）
                if len(lines) % 2 != 0:
                    st.error("TXT文件行数必须为偶数（每两行一组：英文+中文）")
                else:
                    for i in range(0, len(lines), 2):
                        english_line = lines[i].strip()
                        chinese_line = lines[i + 1].strip()
                        if english_line and chinese_line:
                            expanded_english = expand_abbreviations(english_line)
                            output_file = f"audio_{i//2 + 1}.mp3"
                            asyncio.run(text_to_speech(expanded_english, voice, speed, output_file))
                            audio_files.append(output_file)
                            text_lines.append(english_line)  # 保存英文
                            text_lines.append(chinese_line)  # 保存中文
                    # 使用TXT文件名（去掉.txt）作为ZIP文件名
                    zip_filename = f"{os.path.splitext(selected_file)[0]}.zip"
    
    # 显示和播放单独的音频文件
    if audio_files:
        st.subheader("生成的音频文件")
        if input_method == "直接输入":
            for i, audio_file in enumerate(audio_files):
                st.markdown(f"<h1 style='font-family: \"Times New Roman\", serif;'>{text_lines[i]}</h1>", unsafe_allow_html=True)
                st.audio(audio_file)
        else:
            for i, audio_file in enumerate(audio_files):
                english_text = text_lines[i * 2]
                chinese_text = text_lines[i * 2 + 1]
                st.markdown(
                    f"<h1 style='font-family: \"Times New Roman\", serif;'>{english_text}</h1>"
                    f"<div style='font-family: \"Times New Roman\", serif; font-size: 1.5rem; color: #555; margin-top: 5px;'>{chinese_text}</div>",
                    unsafe_allow_html=True
                )
                st.audio(audio_file)
        
        # 生成两个HTML文件
        flashcard_html = generate_flashcard_html(audio_files, text_lines, is_txt_input=(input_method == "从TXT文件读取"))
        text_list_html = generate_text_list_html(text_lines, is_txt_input=(input_method == "从TXT文件读取"))
        
        # 创建文本列表文件
        text_list_txt = "text_list.txt"
        with open(text_list_txt, "w", encoding="utf-8") as f:
            f.write("\n".join(text_lines))
        
        # 创建下载包
        with zipfile.ZipFile(zip_filename, 'w') as zipf:
            # 添加单独的音频文件
            for audio_file in audio_files:
                zipf.write(audio_file)
            # 添加文本列表和HTML文件
            zipf.write(text_list_txt)
            zipf.write(flashcard_html)
            zipf.write(text_list_html)
        
        # 提供下载按钮
        with open(zip_filename, "rb") as f:
            st.download_button(
                label="下载所有文件（音频+单词列表+HTML）",
                data=f,
                file_name=zip_filename,
                mime="application/zip"
            )
        
        # 清理生成的文件（避免影响下次运行）
        clear_output_files(audio_files, text_list_txt, [flashcard_html, text_list_html])

if __name__ == "__main__":
    main()
