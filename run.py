import streamlit as st
from gtts import gTTS
import os
import zipfile
from typing import List
import time
import io  # 用于内存中生成音频

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
# 2. 常量（移除 VOICES 中的 zh-CN，gTTS 支持有限；英文优先）
# -------------------------------------------------
VOICES = {  # gTTS 语音选项（英文为主，lang='en' 或 'zh'）
    "en-US (Female)": "en",
    "en-GB (Female)": "en",
    "en-US (Male)": "en",  # gTTS 无严格男女区分，但可通过 tld 调整
    "zh-CN (Female)": "zh",
}

SPEED_OPTIONS = {  # gTTS 无直接速度控制，用 slow=True 模拟慢速
    "Normal": False,
    "Slow": True,
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
# 4. 生成单条音频（gTTS 同步，简单可靠）
# -------------------------------------------------
def generate_one_audio(text: str, lang: str, slow: bool, output_file: str) -> bool:
    if not text.strip():
        return False
    try:
        text = expand_abbreviations(text)
        tts = gTTS(text=text, lang=lang, slow=slow)
        # 保存到文件
        tts.save(output_file)
        # 检查文件是否生成且非空
        if os.path.exists(output_file) and os.path.getsize(output_file) > 0:
            return True
        else:
            if os.path.exists(output_file):
                os.remove(output_file)
            return False
    except Exception as e:
        st.error(f"生成音频失败（{output_file}）：{str(e)}")
        return False

# -------------------------------------------------
# 5. 批量生成音频（同步，带进度条）
# -------------------------------------------------
def generate_audios_batch(text_list: List[str], lang: str, slow: bool, start_idx: int = 100, progress_bar=None) -> List[str]:
    audio_files = []
    for i, text in enumerate(text_list):
        out_file = f"{start_idx + i}.mp3"
        if progress_bar:
            progress_bar.progress((i + 1) / len(text_list))
            st.rerun()  # 刷新 UI 更新进度
        success = generate_one_audio(text, lang, slow, out_file)
        if success:
            audio_files.append(out_file)
        time.sleep(0.5)  # 避免请求过频（Google 有率限）
    return audio_files

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
    st.title("英语点读卡生成器")

    voice_name = st.selectbox("选择语言（语音）", list(VOICES.keys()))
    lang = VOICES[voice_name]

    speed_name = st.selectbox("选择速度", list(SPEED_OPTIONS.keys()))
    slow = SPEED_OPTIONS[speed_name]

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
                lines = [l.strip() for l in user_input.split("\n") if l.strip()]
                if lines:
                    progress_bar = st.progress(0)
                    status_text = st.empty()
                    status_text.text("开始生成音频...")
                    try:
                        audio_files = generate_audios_batch(lines, lang, slow, progress_bar=progress_bar)
                        text_lines = lines
                        zip_filename = "英语单词点读卡-设计制作：川哥.zip"
                        if audio_files:
                            st.success(f"成功生成 {len(audio_files)} 个音频文件！")
                        else:
                            st.error("所有音频生成失败，请检查网络或文本内容。")
                    except Exception as e:
                        st.error(f"生成失败：{str(e)}")
                    progress_bar.empty()
                    status_text.empty()

    # ------------------- TXT 文件 -------------------
    else:
        txt_files = get_txt_files()
        if not txt_files:
            st.warning("当前目录下没有找到 TXT 文件！")
        else:
            selected_file = st.selectbox("选择一个 TXT 文件", txt_files)
            if st.button("生成音频"):
                try:
                    with open(selected_file, "r", encoding="utf-8") as f:
                        raw_lines = [l.strip() for l in f.readlines() if l.strip()]

                    if len(raw_lines) % 2 != 0:
                        st.error("TXT 文件行数必须为偶数（每两行一组：英文+中文）")
                    else:
                        eng_lines = raw_lines[::2]
                        if eng_lines:
                            progress_bar = st.progress(0)
                            status_text = st.empty()
                            status_text.text("开始生成音频...")
                            try:
                                audio_files = generate_audios_batch(eng_lines, lang, slow, progress_bar=progress_bar)
                                text_lines = raw_lines
                                zip_filename = f"{os.path.splitext(selected_file)[0]}.zip"
                                if audio_files:
                                    st.success(f"成功生成 {len(audio_files)} 个音频文件！")
                                else:
                                    st.error("所有音频生成失败，请检查网络或文本内容。")
                            except Exception as e:
                                st.error(f"生成失败：{str(e)}")
                            progress_bar.empty()
                            status_text.empty()
                except Exception as e:
                    st.error(f"读取或生成失败：{str(e)}")

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
        try:
            is_txt = (input_method != "直接输入")
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
                st.download_button(
                    label="下载所有文件（音频+列表+HTML）",
                    data=f,
                    file_name=zip_filename,
                    mime="application/zip",
                )
        except Exception as e:
            st.error(f"打包失败：{e}")

        # ------------------- 清理 -------------------
        clear_output_files(audio_files, "text_list.txt", ["flashcard.html", "text_list.html"])

if __name__ == "__main__":
    main()
