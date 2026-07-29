# Day 04 Lab v2 Report — Research Agent & Career Assistant

## Team

- **Team**: 2A
- **Members**:
  - Vũ Ngọc Hùng (2A202601722)
  - Nguyễn Thị Thanh Hiền (2A202601150)
  - Nguyễn Công Việt Quang (2A202601586)
  - Đỗ Thành Đạt (2A202601278)
  - Trần Thị Hường (2A202601648)
- **Provider/model**: DeepSeek / `deepseek-chat`

---

# PHẦN A — Giới thiệu agent

## A1. Agent này làm được gì

SkillLens & Career Research Agent: Tra cứu bài đăng tuyển dụng thời gian thực qua JSearch API (theo vị trí, địa điểm, remote), xem chi tiết mô tả công việc (JD) qua `job_details`, đọc URL bài đăng qua `fetch`, tự động hỏi lại khi thiếu thông tin vị trí (`clarify`), xin xác nhận trước khi thực hiện hành động gửi tin nhắn Telegram, và hỗ trợ phân tích lộ trình kỹ năng nghề nghiệp.

**Link dùng thử (truy cập được trong showdown):**

> URL: `http://localhost:8501` (Streamlit GUI running locally)

## A2. Tool agent có

| Tên tool | Làm được gì | Tool mới nhóm thêm? |
|---|---|---|
| clarify | Hỏi lại người dùng khi thiếu thông tin hoặc xin xác nhận trước khi đăng bài | Không |
| job_search | Tìm kiếm bài đăng tuyển dụng thời gian thực theo vị trí và địa điểm (JSearch API) | Có (Tool mới #1) |
| job_details | Lấy thông tin chi tiết đầy đủ của vị trí tuyển dụng (JD, lương, yêu cầu) theo `job_id` | Có (Tool mới #2) |
| lookup | Tra cứu tin tức và thông tin công nghệ tổng quan trên Internet | Không |
| fetch | Đọc và trích xuất nội dung văn bản từ một địa chỉ URL bài đăng | Không |
| format | Trình bày dữ liệu danh sách bài đăng thành văn bản định dạng Markdown đẹp mắt | Không |
| send | Gửi thông điệp/bản tin tóm tắt tuyển dụng qua Telegram (cần xác nhận) | Không |

## A3. Câu hỏi mẫu để thử

1. "Tìm bài đăng tuyển dụng vị trí AI Engineer ở Việt Nam"
2. "Tìm giúp mình các công việc Senior Data Scientist tại Ho Chi Minh"
3. "Xem chi tiết yêu cầu công việc cho mã job_id=gJ3wBAAAAQAAMAQAAGkAAAAAAA=="
4. "Soạn bản tin tổng hợp tuyển dụng Unity Developer và đăng lên Telegram giúp mình"

## A4. Kịch bản demo đã rehearse

| Scenario | Tool trace cần thấy | Câu chuyện cải thiện version | Fallback run/transcript |
|---|---|---|---|
| 1. Tra cứu tuyển dụng theo vị trí | `job_search({"query": "AI Engineer in Vietnam"})` | Chuyển từ API Twitter cũ sang JSearch endpoint `/search-v2` giúp tìm kiếm chính xác vị trí công việc theo quốc gia. | `runs/v2_B_base_deepseek_20260729T155045480437.json` |
| 2. Thiếu thông tin vị trí công việc | `clarify({"question": "...", "response_type": "text"})` | Bổ sung quy tắc Missing Role Rule giúp Agent không gọi nhầm tool tìm kiếm khi thiếu Job Title. | `runs/v3_B_group_deepseek_20260729T160335973619.json` |
| 3. Ranh giới xin xác nhận trước khi gửi bài | `clarify({"question": "...", "response_type": "yes_no"})` | Cập nhật Action Confirmation Boundary trong `tools.yaml` & `system_prompt.md` đảm bảo 100% không tự ý gửi bài Telegram. | `transcripts/skilllens_20260729T161520526262.transcript.json` |

---

# PHẦN B — Chi tiết / Bằng chứng

## B1. Version evidence

| Version | Prompt/tool change | Hypothesis | Metric name | Before | After | Run File |
|---|---|---|---|---:|---:|---|
| v0 | Baseline starter code | Đánh giá ban đầu với prompt và tool mặc định | case_accuracy | 0.0000 | 0.7500 | `runs/v0_B_base_deepseek_20260729T152200316012.json` |
| v1 | Tích hợp JSearch `job_search` API | Thay thế Twitter API bằng JSearch `/search-v2` tăng khả năng tra cứu việc làm | case_accuracy | 0.7500 | 0.8500 | `runs/v1_B_base_deepseek_20260729T152411182539.json` |
| v2 | Tối ưu prompt & clarify yes_no boundary | Cấu trúc lại schema `tools.yaml` và quy tắc `clarify` giúp loại bỏ hoàn toàn lỗi boundary | case_accuracy | 0.8500 | 1.0000 | `runs/v2_B_base_deepseek_20260729T154428339727.json` |
| v3 | Tích hợp `job_details` & bộ 10 team eval cases | Thêm tool `job_details` và 10 test case nhóm cho quy trình tuyển dụng | case_accuracy | 0.7000 | 1.0000 | `runs/v3_B_group_deepseek_20260729T160335973619.json` |

## B2. Failure analysis

| Case ID | Failure Type | Actual Tool Calls | What Failed | Fix |
|---|---|---|---|---|
| `R12_confirm_before_send` | `wrong_boundary` | `clarify(response_type="text")` | LLM suy luận hỏi nội dung văn bản thay vì hỏi xác nhận Yes/No trước khi đăng bài Telegram | Cập nhật mô tả `response_type` trong `tools.yaml` và ưu tiên Action Confirmation Boundary trong `system_prompt.md` |
| `G04_job_search_missing_title` | `missing_info` | `job_search(query="việc làm Hà Nội")` | Người dùng chỉ nhập địa điểm mà không có Job Title, LLM tự lấy địa điểm làm từ khóa tìm kiếm | Thêm quy tắc Missing Role Rule ép buộc gọi `clarify(response_type="text")` khi thiếu tên vị trí công việc |
| `G01_job_search_routing` | `wrong_tool` / `wrong_arg_value` | `job_search(query="AI Engineer Vietnam")` | Format chuỗi query thiếu từ nối vị trí địa lý | Bổ sung hướng dẫn ghép địa điểm bằng mẫu `"in <Location>"` vào `system_prompt.md` |

## B3. Team eval cases

10 test cases được thiết kế trong `data/eval_group.json`:

| Case ID | What It Tests | Expected Tool/Behavior | Result |
|---|---|---|---|
| `G01_job_search_routing` | Tra cứu tin tuyển dụng vị trí AI Engineer tại Việt Nam | `job_search(query="AI Engineer in Vietnam")` | PASS |
| `G02_job_search_location_arg` | Trích xuất từ khóa vị trí kèm địa điểm vào `query` | `job_search(query="Senior Data Scientist in Ho Chi Minh")` | PASS |
| `G03_job_search_read_url` | Có URL bài tuyển dụng cụ thể $\rightarrow$ gọi `fetch` đọc trang | `fetch(url="https://www.linkedin.com/jobs/view/12345678")` | PASS |
| `G04_job_search_missing_title` | Thiếu tên vị trí công việc $\rightarrow$ gọi `clarify` hỏi lại | `clarify(response_type="text")` | PASS |
| `G05_job_search_out_of_scope` | Yêu cầu viết code crawler ngoài phạm vi $\rightarrow$ không gọi tool, từ chối | `no_tool` | PASS |
| `GM01_job_search_location_update` | Multi-turn: kết hợp query vị trí lượt 1 và địa điểm lượt 2 | `job_search(query="AI Engineer in Ho Chi Minh")` | PASS |
| `GM02_job_search_title_correction` | Multi-turn: đính chính tên vị trí công việc ở lượt 2 | `job_search(query="Data Engineer")` | PASS |
| `GM03_job_search_clarify_then_fill` | Multi-turn: bổ sung tên vị trí công việc sau khi được hỏi lại | `job_search(query="Solution Architect")` | PASS |
| `GM04_job_search_read_url_multiturn` | Multi-turn: cung cấp URL ở lượt 2 $\rightarrow$ gọi `fetch` | `fetch(url="https://www.linkedin.com/jobs/view/98765432")` | PASS |
| `GM05_job_search_confirm_post` | Multi-turn: yêu cầu đăng bài $\rightarrow$ gọi `clarify` yes_no xin xác nhận | `clarify(response_type="yes_no")` | PASS |

## B4. Live chat evidence

File bằng chứng hội thoại thực tế: `transcripts/skilllens_20260729T161520526262.transcript.json`

| Scenario/Turn | Version | Tool Calls + Args | Transcript/Run | Outcome |
|---|---|---|---|---|
| Lượt 1: "Tìm việc làm Unity Developer ở Việt Nam" | v3 | `job_search({"query": "Unity Developer in Vietnam", "num_pages": 1})` | `skilllens_20260729T161520526262` | Trả về danh sách công việc Unity Developer thời gian thực từ JSearch API |
| Lượt 2: "Xem chi tiết công việc đầu tiên" | v3 | `job_details({"job_id": "gJ3wBAAAAQAAMAQAAGkAAAAAAA==", "country": "vn"})` | `skilllens_20260729T161520526262` | Trả về đầy đủ thông tin JD, yêu cầu kỹ năng và link ứng tuyển |

## B5. Tool capability evidence

| Category | Evidence File | What Worked | Risk / Guardrail |
|---|---|---|---|
| Must-have: tool mới #1 (`job_search`) | `tools/job_search/tool.py` | Lấy dữ liệu tuyển dụng trực tiếp từ JSearch RapidAPI endpoint `/search-v2` với fallback sang Tavily/Mock | Giới hạn số lượng request per minute của API key được xử lý qua try/except fallback |
| Must-have: tool mới #2 (`job_details`) | `tools/job_details/tool.py` | Trích xuất toàn bộ mô tả JD, yêu cầu kinh nghiệm, kỹ năng và mức lương theo `job_id` | Cắt gọn độ dài mô tả tối đa 1500 ký tự để tránh vượt token limit của LLM |
| Optional built-in (`clarify`) | `tools/clarify/tool.py` | Phân biệt chính xác giữa làm rõ thông tin thiếu (`text`) và xin xác nhận trước khi đăng bài (`yes_no`) | Đặt cờ `awaiting_user` để tạm dừng luồng trước khi thực hiện hành động ghi |

## B6. Reflection

- **Fix thuộc về `system_prompt.md`**: Các nguyên tắc định hướng tổng quát (principle-based), quy tắc Missing Role Rule khi thiếu tên vị trí công việc, và thứ tự ưu tiên tuyệt đối cho Action Confirmation Boundary khi đăng bài Telegram.
- **Fix thuộc về `tools.yaml`**: Chi tiết hóa mô tả các tham số của tool (đặc biệt là mô tả phân biệt giữa `text` và `yes_no` của `response_type` trong tool `clarify`).
- **Lỗi cần review thủ công**: Các phản hồi lỗi từ phía server API mạng (như HTTP 403 từ endpoint scrape) hoặc các trường hợp câu trả lời tự nhiên của LLM khi không cần gọi tool.
- **Cải tiến tiếp theo**: Bổ sung bộ nhớ lưu trữ lịch sử ứng tuyển của người dùng và tính năng tự động so sánh CV với JD để chỉ ra khoảng cách kỹ năng (Skill Gap Analysis).
