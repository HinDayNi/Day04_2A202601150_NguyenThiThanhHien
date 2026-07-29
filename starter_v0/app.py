from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any

import streamlit as st

from chat import run_model_tool_loop, write_transcript
from providers import make_provider
from tools import load_tool_declarations, to_openai_tools
from versioning import artifact_version_dict, build_artifact_version

ROOT = Path(__file__).parent
ARTIFACTS_DIR = ROOT / "artifacts"
TRANSCRIPTS_DIR = ROOT / "transcripts"
SYSTEM_PROMPT_PATH = ARTIFACTS_DIR / "system_prompt.md"
TOOLS_PATH = ARTIFACTS_DIR / "tools.yaml"
APP_TOOL_NAMES = {"clarify", "lookup", "fetch", "format"}

APP_SYSTEM_PROMPT = """
Bạn là SkillLens, trợ lý tư vấn kỹ năng nghề nghiệp bằng tiếng Việt.

Mục tiêu của bạn là giúp người dùng hiểu một job title cần những kỹ năng nào.
Khi trả lời:
- Phân nhóm rõ ràng thành kỹ năng chuyên môn, công cụ/công nghệ và kỹ năng mềm.
- Giải thích ngắn gọn vì sao từng kỹ năng quan trọng.
- Phân biệt mức nền tảng, thực hành và nâng cao khi phù hợp.
- Nếu người dùng cung cấp kinh nghiệm hoặc mục tiêu, hãy chỉ ra khoảng cách kỹ năng.
- Không khẳng định một danh sách là tuyệt đối; yêu cầu có thể khác theo công ty và cấp độ.
- Chỉ hỏi lại khi thiếu job title hoặc thông tin đó thực sự cần thiết.
- Có thể dùng công cụ tìm kiếm khi người dùng yêu cầu thông tin thị trường hiện tại.
- Mở đầu bằng một kết luận ngắn, sau đó dùng tiêu đề Markdown cấp 2.
- Mỗi bullet chỉ trình bày một ý; bôi đậm tên kỹ năng và tránh đoạn văn dài.
- Khi đề xuất lộ trình, dùng thứ tự ưu tiên và đầu ra thực hành cụ thể.
- Kết thúc bằng một câu hỏi tiếp nối ngắn, phù hợp với ngữ cảnh.
- Trả lời sáng rõ, thực tế; không lặp lại câu hỏi và không dùng lời dẫn sáo rỗng.
""".strip()

SUGGESTION_TEMPLATES = [
    ("Kỹ năng cốt lõi", "Những kỹ năng cốt lõi nào cần có cho vị trí {job}?"),
    ("Theo cấp độ", "So sánh kỹ năng Junior, Middle và Senior của vị trí {job}."),
    ("Lộ trình học", "Hãy đề xuất lộ trình học kỹ năng để trở thành {job}."),
    ("Khoảng cách kỹ năng", "Tạo checklist để tôi tự đánh giá khoảng cách kỹ năng cho vị trí {job}."),
]


def render_process(rounds: list[dict[str, Any]], tool_events: list[dict[str, Any]]) -> None:
    """Show an inspectable execution summary without exposing private model reasoning."""
    with st.expander("Quá trình xử lý", expanded=False):
        if not rounds:
            st.caption("Câu trả lời được tạo trực tiếp, không cần gọi công cụ.")
            return

        for round_item in rounds:
            round_number = round_item.get("round", "?")
            calls = round_item.get("tool_calls") or []
            if calls:
                names = ", ".join(call.get("name", "tool") for call in calls)
                st.markdown(f"**Bước {round_number}:** gọi `{names}`")
            else:
                st.markdown(f"**Bước {round_number}:** tổng hợp câu trả lời")

        if tool_events:
            st.caption("Chi tiết công cụ")
            st.json(tool_events, expanded=False)


def render_answer(content: str, *, collapse_long: bool) -> None:
    preview_limit = 1800
    if collapse_long and len(content) > preview_limit:
        preview = content[:preview_limit].rsplit(" ", 1)[0]
        st.markdown(f"{preview}…")
        with st.expander("Xem toàn bộ câu trả lời", expanded=False):
            st.markdown(content)
        return
    st.markdown(content)


def init_state() -> None:
    defaults: dict[str, Any] = {
        "messages": [],
        "turns": [],
        "pending_prompt": None,
        "transcript_id": datetime.now().strftime("skilllens_%Y%m%dT%H%M%S%f"),
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def clear_chat() -> None:
    st.session_state.messages = []
    st.session_state.turns = []
    st.session_state.pending_prompt = None
    st.session_state.transcript_id = datetime.now().strftime("skilllens_%Y%m%dT%H%M%S%f")


def save_transcript(provider_name: str, model: str | None) -> Path:
    artifact = build_artifact_version("ui", SYSTEM_PROMPT_PATH, TOOLS_PATH)
    transcript = {
        "transcript_id": st.session_state.transcript_id,
        **artifact_version_dict(artifact),
        "provider": provider_name,
        "model": model,
        "app": "SkillLens",
        "created_at": st.session_state.transcript_id.replace("skilllens_", ""),
        "turns": st.session_state.turns,
    }
    path = TRANSCRIPTS_DIR / f"{st.session_state.transcript_id}.transcript.json"
    write_transcript(path, transcript)
    return path


st.set_page_config(
    page_title="SkillLens · Job Skills Chat",
    page_icon="✦",
    layout="centered",
)

st.markdown(
    """
    <style>
    .stApp { background: #f6f8fc; color: #172033; }
    .block-container { max-width: 900px; padding-top: 2rem; padding-bottom: 7rem; }
    [data-testid="stHeader"] { background: transparent; }
    .hero {
        padding: .6rem 0 1.4rem;
        margin-bottom: .6rem;
    }
    .eyebrow {
        color: #2563eb;
        font-size: .78rem;
        font-weight: 700;
        letter-spacing: .1em;
        text-transform: uppercase;
    }
    .hero h1 {
        color: #15213a;
        font-size: clamp(1.8rem, 4vw, 2.6rem);
        letter-spacing: -.035em;
        line-height: 1.12;
        margin: .4rem 0 .6rem;
    }
    .hero p { color: #64748b; max-width: 680px; margin: 0; line-height: 1.7; }
    .stChatMessage {
        background: transparent;
        border: 0;
        border-radius: 0;
        box-shadow: none;
        padding: .65rem 0;
    }
    [data-testid="stChatMessageContent"] {
        font-size: 1rem;
        line-height: 1.72;
    }
    [data-testid="stChatMessageContent"] h2,
    [data-testid="stChatMessageContent"] h3 {
        color: #172033;
        letter-spacing: -.02em;
        margin-top: 1.15rem;
    }
    [data-testid="stChatMessageContent"] li { margin-bottom: .4rem; }
    [data-testid="stExpander"] {
        border: 1px solid #e3e9f2;
        border-radius: 12px;
        background: rgba(255,255,255,.55);
    }
    div[data-testid="stChatInput"] {
        border-color: #dbe4f0;
        box-shadow: 0 8px 28px rgba(37, 99, 235, .08);
    }
    div.stButton > button {
        border-radius: 999px;
        border-color: #dce4ef;
        background: #fff;
    }
    div.stButton > button:hover { border-color: #2563eb; color: #1d4ed8; }
    .small-note { color: #7b879b; font-size: .86rem; margin: .25rem 0 .8rem; }
    </style>
    """,
    unsafe_allow_html=True,
)

init_state()

with st.sidebar:
    st.subheader("Thiết lập")
    provider_name = st.selectbox(
        "API chatbot",
        ["deepseek", "openrouter", "openai", "anthropic", "gemini"],
        help="API key được đọc từ file .env.",
    )
    model = (
        st.text_input(
            "Model (không bắt buộc)",
            placeholder="Mặc định: deepseek-chat",
        ).strip()
        or None
    )
    show_process = st.toggle("Hiện quá trình xử lý", value=True)
    collapse_long = st.toggle("Thu gọn câu trả lời dài", value=True)
    st.divider()
    st.caption("API key chỉ được đọc ở máy chạy ứng dụng và không hiển thị trên giao diện.")
    st.button("Xóa hội thoại", use_container_width=True, on_click=clear_chat)

st.markdown(
    """
    <section class="hero">
      <div class="eyebrow">SkillLens · Career Assistant</div>
      <h1>Khám phá kỹ năng cho công việc bạn muốn</h1>
      <p>Nhập một vị trí để xem kỹ năng chuyên môn, công cụ cần biết,
      kỹ năng mềm và gợi ý phát triển phù hợp.</p>
    </section>
    """,
    unsafe_allow_html=True,
)

job_title = st.text_input(
    "Job title",
    value="Data Analyst",
    placeholder="Ví dụ: Data Analyst, Product Manager, Backend Developer",
)

st.markdown('<div class="small-note">Gợi ý câu hỏi</div>', unsafe_allow_html=True)
cols = st.columns(2)
for index, (label, template) in enumerate(SUGGESTION_TEMPLATES):
    if cols[index % 2].button(label, key=f"suggestion_{index}", use_container_width=True):
        title = job_title.strip() or "công việc này"
        st.session_state.pending_prompt = template.format(job=title)

st.divider()

if not st.session_state.messages:
    with st.chat_message("assistant"):
        st.markdown("Xin chào! Bạn muốn tìm hiểu kỹ năng cho vị trí nào? " "Bạn có thể chọn một gợi ý phía trên hoặc nhập câu hỏi bên dưới.")

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        render_answer(message["content"], collapse_long=collapse_long)
        if message["role"] == "assistant" and show_process:
            render_process(message.get("rounds", []), message.get("tool_events", []))

typed_prompt = st.chat_input("Hỏi về kỹ năng của một công việc…")
prompt = st.session_state.pending_prompt or typed_prompt
st.session_state.pending_prompt = None

if prompt:
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        with st.spinner("Đang phân tích kỹ năng phù hợp…"):
            try:
                provider = make_provider(provider_name)
                declarations = [item for item in load_tool_declarations(TOOLS_PATH) if item["name"] in APP_TOOL_NAMES]
                tools = to_openai_tools(declarations)
                history = [{"role": item["role"], "content": item["content"]} for item in st.session_state.messages[-10:]]
                result = run_model_tool_loop(
                    provider=provider,
                    messages=[
                        {"role": "system", "content": APP_SYSTEM_PROMPT},
                        *history,
                    ],
                    tools=tools,
                    model=model,
                    max_tool_rounds=4,
                )
                answer = result["assistant_text"] or "Mình chưa nhận được câu trả lời phù hợp."
                rounds = result.get("rounds", [])
                tool_events = result.get("tool_events", [])
                render_answer(answer, collapse_long=collapse_long)
                if show_process:
                    render_process(rounds, tool_events)

                st.session_state.messages.append(
                    {
                        "role": "assistant",
                        "content": answer,
                        "rounds": rounds,
                        "tool_events": tool_events,
                    }
                )
                st.session_state.turns.append(
                    {
                        "turn_index": len(st.session_state.turns) + 1,
                        "user": prompt,
                        "assistant_text": answer,
                        "status": result.get("status"),
                        "rounds": rounds,
                        "tool_events": tool_events,
                    }
                )
                save_transcript(provider_name, model)
            except Exception as exc:
                message = "Chưa thể kết nối API. Hãy kiểm tra API key trong file `.env` " f"và thử lại.\n\nChi tiết: `{type(exc).__name__}: {exc}`"
                st.error(message)
