import pandas as pd
import re
import os

# 读取parquet文件
df = pd.read_parquet("/Users/cg/川哥英语资料库Qbank-本地数据中心/data/parquet/quiz.parquet")

# 指定的编号列表
task_ids = [
    "task-import-20260315-405706", "task-import-20260315-0b0a29", "task-import-20260315-fccf9a",
    "task-import-20260315-257276", "task-import-20260315-be13cd", "task-import-20260315-162093",
    "task-import-20260315-aa59dd", "task-import-20260315-f7cb0e", "task-import-20260315-44846f",
    "task-import-20260315-722854", "task-import-20260315-2a2375", "task-import-20260315-9a8969",
    "task-import-20260315-481830", "task-import-20260315-dbca6d", "task-import-20260315-abd037",
    "task-import-20260315-88b63b", "task-import-20260315-05ce3e", "task-import-20260315-a22cd6",
    "task-import-20260315-5b56d2", "task-import-20260315-34dc72", "task-import-20260315-d2774c",
    "task-import-20260315-6dbbad", "task-import-20260315-841ab9", "task-import-20260315-d9f8cb",
    "task-import-20260315-a82c52", "task-import-20260315-1da650", "task-import-20260315-c6e6b7",
    "task-import-20260315-21b44d", "task-import-20260315-a33c68", "task-import-20260315-80db6e",
    "task-import-20260315-a1a583", "task-import-20260315-c96ca2", "task-import-20260315-99d1bf",
    "task-import-20260315-31d5a2", "task-import-20260315-dbb5e5", "task-import-20260315-45fc4c",
    "task-import-20260315-9708c3", "task-import-20260315-f24bcb", "task-import-20260315-e638a4",
    "task-import-20260315-6df632", "task-import-20260315-a83695", "task-import-20260315-fe3814",
    "task-import-20260315-ca4a94", "task-import-20260315-d762ef", "task-import-20260315-df0660",
    "task-import-20260315-5a91de", "task-import-20260315-950c95", "task-import-20260315-d40d95",
    "task-import-20260315-4718bd", "task-import-20260315-c7d213", "task-import-20260315-4834b7",
    "task-import-20260315-d0da1d", "task-import-20260315-62d357", "task-import-20260315-dc5a5a",
    "task-import-20260315-34fc7e", "task-import-20260315-fc8c83", "task-import-20260315-06cafe",
    "task-import-20260315-75408d", "task-import-20260315-9afc2b", "task-import-20260315-af4f2a",
    "task-import-20260315-b9bde7", "task-import-20260315-8d23a4", "task-import-20260315-ef5641",
    "task-import-20260315-f7496d", "task-import-20260315-c9e22c", "task-import-20260315-84e415",
    "task-import-20260315-6681ee", "task-import-20260315-31bf20", "task-import-20260315-71c703",
    "task-import-20260315-ff4059", "task-import-20260315-b3f38b", "task-import-20260315-4e8c86",
    "task-import-20260315-0697da", "task-import-20260315-fa3611", "task-import-20260315-776042",
    "task-import-20260315-def5e5", "task-import-20260315-cf5426", "task-import-20260315-3348e6",
    "task-import-20260315-44dba9", "task-import-20260315-6ee9a6"
]

# 筛选数据
df_filtered = df[df['编号'].isin(task_ids)].copy()
print(f"找到 {len(df_filtered)} 条记录")

def is_dialogue(text):
    """判断是否为对话格式"""
    if pd.isna(text) or text == '':
        return False
    # 如果包含两个或以上的破折号，可能是对话
    dash_count = text.count('—') + text.count('--')
    return dash_count >= 2

def format_dialogue(text):
    """格式化对话：在—前换行，—后加空格"""
    if pd.isna(text) or text == '':
        return text
    
    # 先处理 — 前面没有换行的情况
    # 匹配非换行符后面的—
    text = re.sub(r'([^\n])—', r'\1\n—', text)
    
    # 确保 — 后面有一个空格
    text = re.sub(r'—([^\s])', r'— \1', text)
    
    return text

def fix_spelling_and_punctuation(text):
    """修复拼写和标点错误"""
    if pd.isna(text) or text == '':
        return text
    
    original = text
    
    # 常见拼写错误修复
    fixes = [
        (r'justcome', 'just come'),
        (r'alreadyintheir', 'already in their'),
        (r'can\'t', "can't"),
        (r'won\'t', "won't"),
        (r'don\'t', "don't"),
        (r'doesn\'t', "doesn't"),
        (r'didn\'t', "didn't"),
        (r'isn\'t', "isn't"),
        (r'aren\'t', "aren't"),
        (r'wasn\'t', "wasn't"),
        (r'weren\'t', "weren't"),
        (r'hasn\'t', "hasn't"),
        (r'haven\'t', "haven't"),
        (r'hadn\'t', "hadn't"),
        (r'wouldn\'t', "wouldn't"),
        (r'couldn\'t', "couldn't"),
        (r'shouldn\'t', "shouldn't"),
        (r'mustn\'t', "mustn't"),
        (r'needn\'t', "needn't"),
        (r'daren\'t', "daren't"),
        (r'I\'m', "I'm"),
        (r'I\'ve', "I've"),
        (r'I\'d', "I'd"),
        (r'I\'ll', "I'll"),
        (r'you\'re', "you're"),
        (r'you\'ve', "you've"),
        (r'you\'d', "you'd"),
        (r'you\'ll', "you'll"),
        (r'he\'s', "he's"),
        (r'she\'s', "she's"),
        (r'it\'s', "it's"),
        (r'we\'re', "we're"),
        (r'we\'ve', "we've"),
        (r'we\'d', "we'd"),
        (r'we\'ll', "we'll"),
        (r'they\'re', "they're"),
        (r'they\'ve', "they've"),
        (r'they\'d', "they'd"),
        (r'they\'ll', "they'll"),
        (r'that\'s', "that's"),
        (r'what\'s', "what's"),
        (r'who\'s', "who's"),
        (r'where\'s', "where's"),
        (r'when\'s', "when's"),
        (r'why\'s', "why's"),
        (r'how\'s', "how's"),
        (r'let\'s', "let's"),
        (r'there\'s', "there's"),
        (r'here\'s', "here's"),
        # 常见连写词拆分
        (r'\btothe\b', 'to the'),
        (r'\bofthe\b', 'of the'),
        (r'\binthe\b', 'in the'),
        (r'\batthe\b', 'at the'),
        (r'\bonthe\b', 'on the'),
        (r'\bforthe\b', 'for the'),
        (r'\bwiththe\b', 'with the'),
        (r'\bbythe\b', 'by the'),
        (r'\bfromthe\b', 'from the'),
        (r'\baboutthe\b', 'about the'),
        (r'\bintothe\b', 'into the'),
        (r'\bontothe\b', 'onto the'),
        (r'\bthroughthe\b', 'through the'),
        (r'\boverthe\b', 'over the'),
        (r'\bunderthe\b', 'under the'),
        (r'\babove\bthe', 'above the'),
        (r'\bbelowthe\b', 'below the'),
        (r'\bbetweenthe\b', 'between the'),
        (r'\bamongthe\b', 'among the'),
        (r'\baroundthe\b', 'around the'),
        (r'\bbehindthe\b', 'behind the'),
        (r'\bbeforethe\b', 'before the'),
        (r'\bafterthe\b', 'after the'),
        (r'\bduringthe\b', 'during the'),
        (r'\bsincethe\b', 'since the'),
        (r'\buntilthe\b', 'until the'),
        (r'\bwhilethe\b', 'while the'),
        (r'\basa', 'as a'),
        (r'\bis a\b', 'is a'),
        (r'\bina\b', 'in a'),
        (r'\bona\b', 'on a'),
        (r'\bata\b', 'at a'),
        (r'\btoa\b', 'to a'),
        (r'\bfora\b', 'for a'),
        (r'\bwitha\b', 'with a'),
        (r'\bbya\b', 'by a'),
        (r'\bfroma\b', 'from a'),
        (r'\babouta\b', 'about a'),
        (r'\bintoa\b', 'into a'),
        (r'\bontoa\b', 'onto a'),
        # 修复多个空格为单空格
        (r'  +', ' '),
        # 修复标点前多余的空格
        (r'\s+([.,!?;:])', r'\1'),
        # 修复标点后缺少空格
        (r'([.,!?;:])([A-Za-z])', r'\1 \2'),
    ]
    
    for pattern, replacement in fixes:
        text = re.sub(pattern, replacement, text, flags=re.IGNORECASE)
    
    return text

def standardize_blanks(text):
    """标准化填空格式为 ______ 前后各一个空格"""
    if pd.isna(text) or text == '':
        return text
    
    # 各种填空格式统一为 ______
    # 匹配各种下划线形式：_ __ ___ ____ _____ ______ _______ 等
    text = re.sub(r'_{2,}', '______', text)
    # 单个下划线且周围没有其他下划线时，扩展为六个
    text = re.sub(r'(?<!_)_(?!_)', '______', text)
    
    # 确保 ______ 前后各有且只有一个空格
    # 先移除 ______ 前后的所有空格
    text = re.sub(r'\s*______\s*', ' ______ ', text)
    
    # 移除可能产生的首尾多余空格
    text = text.strip()
    
    return text

def process_field(text, is_question=False):
    """处理单个字段"""
    if pd.isna(text) or text == '':
        return text, False
    
    original = str(text)
    processed = str(text)
    
    # 如果是题干，检查是否为对话并格式化
    if is_question:
        if is_dialogue(processed):
            processed = format_dialogue(processed)
    
    # 修复拼写和标点
    processed = fix_spelling_and_punctuation(processed)
    
    # 标准化填空（只对题干）
    if is_question:
        processed = standardize_blanks(processed)
    
    modified = (processed != original)
    return processed, modified

# 处理数据
results = []
for idx, row in df_filtered.iterrows():
    result = {'编号': row['编号']}
    has_modification = False
    
    # 处理题干
    if pd.notna(row['题干']) and row['题干'] != '':
        new_val, modified = process_field(row['题干'], is_question=True)
        if modified:
            result['题干'] = new_val
            has_modification = True
    
    # 处理HTML题干
    if pd.notna(row['HTML题干']) and row['HTML题干'] != '':
        new_val, modified = process_field(row['HTML题干'], is_question=True)
        if modified:
            result['HTML题干'] = new_val
            has_modification = True
    
    # 处理选项
    for opt in ['选项A', '选项B', '选项C', '选项D']:
        if pd.notna(row[opt]) and row[opt] != '':
            new_val, modified = process_field(row[opt], is_question=False)
            if modified:
                result[opt] = new_val
                has_modification = True
    
    if has_modification:
        results.append(result)

print(f"\n发现 {len(results)} 条有修改的记录")

# 创建输出目录
output_dir = "/Users/cg/github/cg-read-after-me/output"
os.makedirs(output_dir, exist_ok=True)

# 输出结果
if results:
    df_result = pd.DataFrame(results)
    # 确保列顺序
    columns = ['编号', '题干', 'HTML题干', '选项A', '选项B', '选项C', '选项D']
    for col in columns:
        if col not in df_result.columns:
            df_result[col] = None
    df_result = df_result[[col for col in columns if col in df_result.columns]]
    
    output_file = os.path.join(output_dir, "quiz_星火专升本-非谓语动词.xlsx")
    df_result.to_excel(output_file, index=False)
    print(f"\n已保存到: {output_file}")
    
    # 打印修改示例
    print("\n修改示例:")
    for i, r in enumerate(results[:3]):
        print(f"\n编号: {r['编号']}")
        for key, val in r.items():
            if key != '编号':
                print(f"  {key}: {val}")
else:
    print("没有发现需要修改的内容")
