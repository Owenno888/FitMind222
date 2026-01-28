import streamlit as st
import google.generativeai as genai
from PIL import Image
import os

# --- 1. 页面配置 ---
st.set_page_config(
    page_title="FitMind AI Coach",
    page_icon="🧠",
    layout="centered",
    initial_sidebar_state="expanded"
)

# --- 2. 核心 Prompt 逻辑封装 ---
# 这里我们将 React 代码中的两个 Prompt 逻辑合并为一个强大的 System Instruction
SYSTEM_PROMPT = """
You are FitMind AI, an expert fitness coach and nutritionist. 
Your goal is to help users lose fat and build muscle through data-driven analysis.

You have two main capabilities based on the input:

### 1. FOOD ANALYSIS (Visual Input)
If the user provides an image of food:
- Analyze the food image visually.
- Estimate the nutritional content accurately.
- Provide the output in this format:
  * **Food Name**: [Name]
  * **Calories**: [Value] kcal
  * **Macros**: P: [Value]g | C: [Value]g | F: [Value]g

### 2. WEEKLY COACHING & PLANNING (Text/Data Input)
If the user asks for a weekly plan or analysis, follow this strict logic:

**Analysis Logic:**
1. **Calorie Deficit Calculation**: Calculate `Deficit = (Resting Burn + Active Burn) - Intake`.
   - Note: Resting Burn (BMR) is calculated via Mifflin-St Jeor.
   - Active Burn is from Apple Watch/Wearables.
2. **Rating**: Rate the user's week 1-10 based on their deficit consistency and workout intensity.

**Planning Logic (Next Week):**
- **Strength Training**: Descriptions MUST be simple: "Target Body Part - Target Calories". 
  - Example: "Chest & Triceps - 300kcal". (Do NOT specify weights/reps).
- **Cardio**: Descriptions MUST be "Distance (km)" or "Time (min)". 
  - Example: "5km Run" or "45 min Run".
- Plan must balance Long Run, Strength, and Athletic Performance.

**Tone**: Professional, encouraging, but data-focused.
"""

# --- 3. 初始化与鉴权 ---
if "GOOGLE_API_KEY" in st.secrets:
    api_key = st.secrets["GOOGLE_API_KEY"]
else:
    st.error("🚨 未找到 API Key。请在 .streamlit/secrets.toml 中配置 GOOGLE_API_KEY。")
    st.stop()

genai.configure(api_key=api_key)

# 初始化 Session State
if "messages" not in st.session_state:
    st.session_state.messages = []
    # 添加一条欢迎语
    st.session_state.messages.append({
        "role": "assistant", 
        "content": "你好！我是 FitMind 教练。我可以帮你分析食物热量，或者为你制定下周的训练计划。请直接上传图片或输入你的身体数据。"
    })

if "chat_session" not in st.session_state:
    try:
        # 使用 gemini-1.5-flash，它在视觉和文本响应速度上都很快，适合此类应用
        model = genai.GenerativeModel(
            model_name="gemini-1.5-flash", 
            system_instruction=SYSTEM_PROMPT
        )
        st.session_state.chat_session = model.start_chat(history=[])
    except Exception as e:
        st.error(f"模型连接失败: {e}")
        st.stop()

# --- 4. 侧边栏 (图片上传与控制) ---
with st.sidebar:
    st.title("FitMind 控制台")
    st.markdown("### 📸 食物分析")
    uploaded_file = st.file_uploader("上传食物照片", type=["jpg", "jpeg", "png"])
    
    image_preview = None
    if uploaded_file:
        image_preview = Image.open(uploaded_file)
        st.image(image_preview, caption="待分析图片", use_column_width=True)
        st.info("👆 图片已就绪，请在聊天框发送指令 (例如：'分析这个')")

    st.markdown("---")
    if st.button("🗑️ 清除对话历史"):
        st.session_state.messages = []
        # 重置 Session
        model = genai.GenerativeModel(
            model_name="gemini-1.5-flash",
            system_instruction=SYSTEM_PROMPT
        )
        st.session_state.chat_session = model.start_chat(history=[])
        st.rerun()

# --- 5. 主聊天界面 ---
st.title("🧠 FitMind AI")

# 显示历史消息
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# 处理用户输入
if prompt := st.chat_input("输入你的问题，或上传图片后输入'分析'..."):
    
    # 1. 组合用户输入 (文本 + 可选的图片)
    user_content_display = prompt
    user_input_to_model = [prompt]
    
    if uploaded_file and image_preview:
        user_content_display = f"🖼️ [上传了图片] {prompt}"
        user_input_to_model = [prompt, image_preview]

    # 2. 显示用户消息
    st.chat_message("user").markdown(user_content_display)
    st.session_state.messages.append({"role": "user", "content": user_content_display})

    # 3. 调用 AI
    with st.chat_message("assistant"):
        message_placeholder = st.empty()
        try:
            # 流式传输回答
            response_stream = st.session_state.chat_session.send_message(
                user_input_to_model, 
                stream=True
            )
            
            full_response = ""
            for chunk in response_stream:
                if chunk.text:
                    full_response += chunk.text
                    message_placeholder.markdown(full_response + "▌")
            
            message_placeholder.markdown(full_response)
            
            # 记录 AI 回复
            st.session_state.messages.append({"role": "assistant", "content": full_response})
            
            # 如果处理完了图片，可以在这里清除上传状态（可选，Streamlit 中清除比较麻烦，通常保留）
            
        except Exception as e:
            st.error(f"发生错误: {str(e)}")
            st.markdown("如果遇到图片报错，请检查图片格式是否为 JPG/PNG。")
