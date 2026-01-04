import streamlit as st
import pdfplumber
import google.generativeai as genai
import time

# --- 页面配置 ---
st.set_page_config(
    page_title="万字综述生成器 (Pro版)",
    page_icon="📚",
    layout="wide"
)

# --- 侧边栏：配置区 ---
with st.sidebar:
    st.header("⚙️ 核心配置")
    
    # 1. 输入 Key
    api_key = st.text_input("第一步: 输入 Google API Key", type="password")
    
    # 2. 自动检测模型逻辑
    valid_models = []
    if api_key:
        try:
            genai.configure(api_key=api_key)
            # 获取所有支持 generateContent 的模型
            all_models = genai.list_models()
            for m in all_models:
                if 'generateContent' in m.supported_generation_methods:
                    # 只筛选 gemini 系列
                    if 'gemini' in m.name:
                        valid_models.append(m.name)
            st.success(f"✅ 连接成功! 检测到 {len(valid_models)} 个可用模型")
        except Exception as e:
            st.error(f"❌ 连接失败，请检查网络或Key: {e}")

    # 3. 模型选择器 (如果没有检测到，提供默认兜底)
    if not valid_models:
        valid_models = ["models/gemini-1.5-pro", "models/gemini-1.5-flash"]
        
    model_name = st.selectbox("第二步: 选择模型", valid_models, index=0)
    st.info("💡 推荐使用 **gemini-1.5-pro** 系列，逻辑更强，适合写长文。")
    
    st.markdown("---")
    st.markdown("### 📊 生成策略")
    st.write("为达到万字要求，系统将**分5次**请求模型，分别撰写不同章节，最后拼接。")

# --- 功能函数：提取文本 ---
def extract_text(uploaded_files):
    combined_text = ""
    total_pages = 0
    progress_bar = st.progress(0)
    
    for i, file in enumerate(uploaded_files):
        try:
            with pdfplumber.open(file) as pdf:
                for page in pdf.pages:
                    combined_text += page.extract_text() or ""
                    total_pages += 1
        except:
            pass # 跳过损坏文件
        progress_bar.progress((i + 1) / len(uploaded_files))
        
    progress_bar.empty()
    return combined_text, total_pages

# --- 核心函数：分章节生成器 ---
def generate_section(section_title, section_prompt, context_text, model_name, api_key):
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel(model_name)
    
    # 构建超级详细的 Prompt，强制扩写
    full_prompt = f"""
    你是一位严谨的学术研究员。我们要撰写一篇关于“工业机器人轨迹插补技术”的超长篇综述。
    
    当前任务：请**只撰写**【{section_title}】这一部分。
    
    【参考论文内容】
    {context_text[:50000]} 
    (注意：请综合以上文献内容，不要凭空捏造)

    【写作要求】
    1. **字数要求**：本部分必须极度详尽，字数尽量多，至少撰写 2000 字以上。
    2. **内容深度**：不要只写皮毛，要深入到数学公式原理、算法具体步骤、参数对比。
    3. **引用格式**：必须包含大量引用，格式为 (Author, Year)。
    4. **格式**：使用 Markdown，多级标题。
    
    【本章具体指令】
    {section_prompt}
    
    请开始撰写【{section_title}】：
    """
    
    try:
        # 使用 stream=True 可以看到实时进度，但为了便于拼接，这里用非流式等待完整结果
        # 增加 temperature 提高多样性，防止重复
        response = model.generate_content(full_prompt, generation_config={"temperature": 0.7})
        return response.text
    except Exception as e:
        return f"\n\n[该章节生成出错: {e}]\n\n"

# --- 主界面 ---
st.title("📚 万字级文献综述生成器 (分章深挖版)")
st.markdown("上传多篇 PDF，AI 将通过 **5轮深度思考**，为你构建一篇万字长文。")

files = st.file_uploader("拖拽上传论文 (建议上传 5-10 篇以上以保证素材充足)", type="pdf", accept_multiple_files=True)

if st.button("🚀 启动万字生成引擎", type="primary"):
    if not files or not api_key:
        st.warning("请先填写 API Key 并上传文件！")
    else:
        # 1. 解析文件
        with st.status("正在解析 PDF 文献...", expanded=True) as status:
            raw_text, page_count = extract_text(files)
            status.write(f"✅ 已提取 {len(files)} 个文件，共 {page_count} 页文献。")
            status.write("正在启动分章生成任务...")
            
        # 定义 5 个章节的生成计划
        sections = [
            {
                "title": "第一章：研究背景与起源",
                "prompt": "详细阐述工业机器人轨迹插补技术的起源、发展动机。分析从传统数控机床到现代机器人的技术迁移过程。详细介绍该技术在航空航天、汽车制造等领域的具体应用需求背景。"
            },
            {
                "title": "第二章：关键技术演进脉络 (1980s-2024)",
                "prompt": "按时间线极其详细地梳理技术突破。将时间划分为：萌芽期(80年代)、发展期(90-00年代)、成熟期(2010后)和智能化时期(2020后)。对每个时期的代表性算法（如梯形加减速、S型加减速、NURBS插补）进行深入剖析。"
            },
            {
                "title": "第三章：主流插补算法深度对比",
                "prompt": "这是核心章节，请花费最大篇幅。详细分类介绍：1. 直线与圆弧插补；2. 参数曲线插补(NURBS, B样条)；3. 连续小线段前瞻插补。对每种算法，必须详细解释其数学原理、速度规划策略、误差控制方法，并列表对比优缺点。"
            },
            {
                "title": "第四章：现存研究空白与技术瓶颈",
                "prompt": "基于文献，深入分析当前未解决的难点。例如：高速高精下的振动抑制问题、多轴联动的同步性问题、实时性与计算量的矛盾。请列出至少 5 个关键痛点并详细论述。"
            },
            {
                "title": "第五章：未来发展趋势与总结",
                "prompt": "结合人工智能、数字孪生等新技术，预测未来 5-10 年的发展方向。论述深度学习在插补算法中的应用潜力。最后对全文进行总结。"
            }
        ]
        
        full_review = "# 工业机器人轨迹插补技术研究综述\n\n"
        review_placeholder = st.empty()
        
        # 2. 循环生成
        total_steps = len(sections)
        my_bar = st.progress(0)
        
        for idx, sec in enumerate(sections):
            status_msg = f"正在撰写：{sec['title']} ({idx+1}/{total_steps})..."
            st.toast(status_msg)
            
            # 显示正在生成的内容占位符
            with st.chat_message("assistant"):
                st.write(f"✍️ **{status_msg}**")
                
                # 调用 AI
                sec_content = generate_section(
                    sec['title'], 
                    sec['prompt'], 
                    raw_text, 
                    model_name, 
                    api_key
                )
                
                st.markdown(sec_content) # 实时显示当前章节
                
                # 拼接到全文
                full_review += f"\n\n## {sec['title']}\n\n{sec_content}"
                
                # 更新进度条
                my_bar.progress((idx + 1) / total_steps)
            
            # 休息一下，防止触发 Google 速率限制
            if idx < total_steps - 1:
                time.sleep(5) 

        # 3. 完成
        st.success("🎉 万字综述生成完成！")
        
        # 下载按钮
        st.download_button(
            label="📥 下载完整综述 (.md)",
            data=full_review,
            file_name="Deep_Review_Robotics.md",
            mime="text/markdown"
        )
