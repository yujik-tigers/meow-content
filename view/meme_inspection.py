import functools
import hashlib
import logging
import os
import threading
import time
from collections.abc import Callable, Sequence
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date, datetime, timedelta

import requests
import streamlit as st

_logger = logging.getLogger(__name__)

DEFAULT_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000")
_ADMIN_PW_HASH = hashlib.sha256(os.environ["ADMIN_PASSWORD"].encode()).hexdigest()

MAX_FAILURES = 5
LOCKOUT_SECONDS = 60
BULK_MAX_WORKERS = 5

ALL_CONTENT_TYPES = ["reddit_meme", "quote", "literal_quote", "fact"]
ALL_STATUSES = ["raw", "analyzed", "pending", "approved", "rejected", "used"]
ALL_MODELS = [
    "gpt-image-2-2026-04-21",
    "gemini-3.1-flash-image",
    "gemini-3-pro-image",
]
ALL_REGENERATE_TYPES = ["modify", "new"]
REGENERATE_TYPE_LABELS = {"modify": "modify (이전 이미지 기반)", "new": "new (새로 생성)"}
STATUS_COLORS = {
    "raw": "gray",
    "analyzed": "violet",
    "pending": "orange",
    "approved": "green",
    "rejected": "red",
    "used": "blue",
}
REANALYZABLE_FIELDS = [
    "content_translation",
    "expression",
    "expression_translation",
    "background",
]
REANALYZABLE_FIELD_LABELS = {
    "content_translation": "번역",
    "expression": "핵심 표현",
    "expression_translation": "표현 번역",
    "background": "배경",
}


# ── Auth ──────────────────────────────────────────────────────────────────────


@st.cache_resource
def _auth_state() -> tuple[threading.Lock, dict[str, list[float]]]:
    return threading.Lock(), {}


def _client_ip() -> str:
    headers = st.context.headers
    forwarded = headers.get("X-Forwarded-For") or headers.get("X-Real-Ip", "unknown")
    return forwarded.split(",")[0].strip()


def _is_locked_out(ip: str) -> float:
    lock, failures = _auth_state()
    now = time.monotonic()
    with lock:
        cutoff = now - LOCKOUT_SECONDS
        timestamps = [t for t in failures.get(ip, []) if t > cutoff]
        failures[ip] = timestamps
        if len(timestamps) >= MAX_FAILURES:
            return timestamps[0] + LOCKOUT_SECONDS - now
    return 0.0


def _record_failure(ip: str) -> None:
    lock, failures = _auth_state()
    with lock:
        timestamps = failures.setdefault(ip, [])
        timestamps.append(time.monotonic())
        if len(timestamps) == MAX_FAILURES:
            _logger.warning("Auth locked out: ip=%s failures=%d", ip, len(timestamps))


def _clear_failures(ip: str) -> None:
    lock, failures = _auth_state()
    with lock:
        failures.pop(ip, None)


def require_auth() -> bool:
    st.session_state.setdefault("authenticated", False)
    if st.session_state.authenticated:
        return True
    st.title("Meow Content Dashboard")
    st.subheader("로그인")

    ip = _client_ip()
    remaining = _is_locked_out(ip)
    if remaining > 0:
        st.error(
            f"너무 많은 실패 시도로 잠겼습니다. {int(remaining)}초 후에 다시 시도하세요."
        )
        return False

    with st.form("login_form"):
        pw = st.text_input("비밀번호", type="password")
        submitted = st.form_submit_button("로그인")

    if submitted:
        if hashlib.sha256(pw.encode()).hexdigest() == _ADMIN_PW_HASH:
            _clear_failures(ip)
            st.session_state.authenticated = True
            st.rerun()
        else:
            _record_failure(ip)
            remaining = _is_locked_out(ip)
            if remaining > 0:
                st.error(
                    f"너무 많은 실패 시도로 잠겼습니다. {int(remaining)}초 후에 다시 시도하세요."
                )
            else:
                left = MAX_FAILURES - len(_auth_state()[1].get(ip, []))
                st.error(f"비밀번호가 올바르지 않습니다. ({left}회 남음)")
    return False


# ── State ─────────────────────────────────────────────────────────────────────


def init_state() -> None:
    st.session_state.setdefault("base_url", DEFAULT_BASE_URL)
    st.session_state.setdefault("content_type", ALL_CONTENT_TYPES[0])
    st.session_state.setdefault("content_status", ALL_STATUSES[0])
    st.session_state.setdefault("page_index", 0)
    st.session_state.setdefault("page_size", 20)
    st.session_state.setdefault("last_error", None)
    st.session_state.setdefault("sel_gen", 0)


def _sel_key(content_id: int) -> str:
    return f"sel_{content_id}_{st.session_state.sel_gen}"


def _get_selected_ids(items: list[dict]) -> set[int]:
    return {
        item["id"]
        for item in items
        if st.session_state.get(_sel_key(item["id"]), False)
    }


def _deselect_all() -> None:
    st.session_state.sel_gen += 1


def _clear_all_sel_keys() -> None:
    st.session_state.sel_gen += 1


# ── API ───────────────────────────────────────────────────────────────────────


@st.cache_data(ttl=300)
def fetch_contents(
    base_url: str,
    content_type: str,
    content_status: str,
    page_index: int,
    page_size: int,
) -> list[dict]:
    resp = requests.get(
        f"{base_url}/api/v1/admin/contents",
        params={
            "content_type": content_type,
            "content_status": content_status,
            "page_index": page_index,
            "page_size": page_size,
        },
        timeout=10,
    )
    resp.raise_for_status()
    return resp.json().get("content", [])


def analyze_content(base_url: str, content_id: int, content_type: str) -> dict:
    resp = requests.post(
        f"{base_url}/api/v1/admin/contents/{content_id}/analyze",
        json=content_type,
        timeout=180,
    )
    resp.raise_for_status()
    return resp.json().get("content", {})


def update_status(
    base_url: str, content_id: int, from_status: str, to_status: str
) -> None:
    resp = requests.patch(
        f"{base_url}/api/v1/admin/contents/{content_id}/status",
        json={"from_status": from_status, "to_status": to_status},
        timeout=10,
    )
    resp.raise_for_status()


def reanalyze_fields(
    base_url: str,
    content_id: int,
    content_type: str,
    fields: list[dict],
) -> None:
    resp = requests.patch(
        f"{base_url}/api/v1/admin/contents/{content_id}",
        json={"request": fields, "content_type": content_type},
        timeout=180,
    )
    resp.raise_for_status()


def generate_image(base_url: str, content_id: int, content_type: str, model: str) -> dict:
    resp = requests.post(
        f"{base_url}/api/v1/admin/contents/{content_id}/image",
        json={"model": model, "content_type": content_type},
        timeout=180,
    )
    resp.raise_for_status()
    return resp.json().get("content", {})


def regenerate_image(
    base_url: str,
    content_id: int,
    content_type: str,
    model: str,
    prompt: str,
    regenerate_type: str,
) -> dict:
    resp = requests.post(
        f"{base_url}/api/v1/admin/contents/{content_id}/image/regenerate",
        json={
            "model": model,
            "content_type": content_type,
            "prompt": prompt,
            "regenerate_type": regenerate_type,
        },
        timeout=180,
    )
    resp.raise_for_status()
    return resp.json().get("content", {})


def trigger_scraping(base_url: str) -> None:
    for content_type in ("reddit_meme", "quote", "literal_quote"):
        resp = requests.post(
            f"{base_url}/api/v1/admin/scrap",
            json={"content_type": content_type},
            timeout=180,
        )
        resp.raise_for_status()


def fetch_usage_summary(
    base_url: str,
    start: datetime,
    end: datetime,
    apply_free_tier: bool,
) -> list[dict]:
    resp = requests.get(
        f"{base_url}/api/v1/admin/usage/cost",
        params={
            "start": start.isoformat(),
            "end": end.isoformat(),
            "apply_free_tier": apply_free_tier,
        },
        timeout=10,
    )
    resp.raise_for_status()
    return resp.json().get("content", [])


# ── Sidebar ───────────────────────────────────────────────────────────────────


def render_sidebar() -> None:
    with st.sidebar:
        st.title("Setting")
        st.divider()

        new_url = st.text_input("API Base URL", value=st.session_state.base_url)
        if new_url != st.session_state.base_url:
            st.session_state.base_url = new_url
            st.session_state.page_index = 0

        st.divider()
        st.subheader("Filter")

        def _reset_page() -> None:
            st.session_state.page_index = 0
            _clear_all_sel_keys()

        st.selectbox(
            "Content Type",
            options=ALL_CONTENT_TYPES,
            key="content_type",
            on_change=_reset_page,
        )
        st.selectbox(
            "Status",
            options=ALL_STATUSES,
            key="content_status",
            on_change=_reset_page,
        )

        st.divider()
        st.select_slider(
            "Page Size", options=[10, 20, 50], key="page_size", on_change=_reset_page
        )

        st.divider()
        if st.button("지금 스크래핑 실행", use_container_width=True):
            with st.spinner("스크래핑 실행 중..."):
                try:
                    trigger_scraping(str(st.session_state.base_url))
                    st.success("스크래핑 완료. RAW 콘텐츠 목록을 확인하세요.")
                    fetch_contents.clear()
                except requests.exceptions.RequestException as e:
                    st.error(f"스크래핑 실패: {e}")


# ── Usage / Cost summary ────────────────────────────────────────────────────────


def render_usage_summary() -> None:
    today = date.today()
    default_start = today.replace(day=1)

    col_start, col_end = st.columns([1, 1])
    with col_start:
        start_date = st.date_input("시작일", value=default_start, key="usage_start")
    with col_end:
        end_date = st.date_input("종료일", value=today, key="usage_end")

    apply_free_tier = st.checkbox(
        "gpt-5.2 무료 티어 차감 (일 250,000 토큰)", key="usage_apply_free_tier"
    )

    if start_date > end_date:
        st.error("시작일은 종료일보다 이전이어야 합니다.")
        return

    start = datetime.combine(start_date, datetime.min.time())
    end = datetime.combine(end_date, datetime.min.time()) + timedelta(days=1)

    try:
        summaries = fetch_usage_summary(
            st.session_state.base_url, start, end, apply_free_tier
        )
    except requests.exceptions.ConnectionError:
        st.error(f"API 서버에 연결할 수 없습니다: {st.session_state.base_url}")
        return
    except Exception as e:
        st.error(f"사용량 조회 실패: {e}")
        return

    if not summaries:
        st.info("해당 기간에 사용 내역이 없습니다.")
        return

    total_cost = sum(s["cost"] for s in summaries if s.get("cost") is not None)
    missing_pricing = sorted({s["model"] for s in summaries if s.get("cost") is None})

    st.metric("총 비용 (USD)", f"${total_cost:,.4f}")
    if missing_pricing:
        st.caption(f"가격 정보 없음: {', '.join(missing_pricing)} (비용 미포함)")

    st.dataframe(
        summaries,
        column_order=[
            "period",
            "model",
            "request_count",
            "input_tokens_sum",
            "output_tokens_sum",
            "cost",
        ],
        use_container_width=True,
        hide_index=True,
    )


def render_usage_page() -> None:
    st.title("토큰 사용량 / 비용")
    render_usage_summary()


# ── Bulk Actions ──────────────────────────────────────────────────────────────


def _run_bulk_concurrent(
    tasks: Sequence[tuple[int, Callable[[], object]]],
    max_workers: int = BULK_MAX_WORKERS,
) -> list[str]:
    errors: list[str] = []
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_id = {executor.submit(fn): content_id for content_id, fn in tasks}
        for future in as_completed(future_to_id):
            content_id = future_to_id[future]
            try:
                future.result()
            except Exception as e:
                errors.append(f"#{content_id}: {e}")
    return errors


_BULK_ACTIONS: dict[str, list[tuple[str, str]]] = {
    "raw": [("bulk reject", "rejected")],
    "analyzed": [("bulk pending", "pending"), ("bulk reject", "rejected")],
    "pending": [("bulk approve", "approved"), ("bulk reject", "rejected")],
    "approved": [("bulk pending", "pending"), ("bulk reject", "rejected")],
    "rejected": [("bulk pending", "pending")],
}


def render_bulk_actions(items: list[dict], selected_ids: set[int]) -> None:
    status = st.session_state.content_status
    actions = _BULK_ACTIONS.get(status, [])

    base_url = st.session_state.base_url
    content_type = st.session_state.content_type
    all_ids = {item["id"] for item in items}
    all_selected = bool(selected_ids) and selected_ids >= all_ids

    show_bulk_analyze = status == "raw"
    show_bulk_generate = status == "analyzed"
    n_special = int(show_bulk_analyze) + int(show_bulk_generate)

    with st.container(border=True):
        n_actions = (len(actions) + n_special) if selected_ids else 0
        cols = st.columns([3] + [2] * n_actions + [2])

        with cols[0]:
            label = (
                f"**{len(selected_ids)}개 선택됨**" if selected_ids else "**선택 없음**"
            )
            st.markdown(label)

        col_idx = 1

        if selected_ids and show_bulk_analyze:
            with cols[col_idx]:
                if st.button(
                    "일괄 분석",
                    key="bulk_analyze",
                    type="primary",
                    use_container_width=True,
                ):
                    tasks = [
                        (cid, functools.partial(analyze_content, base_url, cid, content_type))
                        for cid in selected_ids
                    ]
                    with st.spinner(f"{len(tasks)}개 항목 분석 중..."):
                        errors = _run_bulk_concurrent(tasks)
                    fetch_contents.clear()
                    _deselect_all()
                    st.session_state.last_error = "\n".join(errors) if errors else None
                    st.rerun()
            col_idx += 1

        if selected_ids and show_bulk_generate:
            with cols[col_idx]:
                if st.button(
                    "일괄 이미지 생성",
                    key="bulk_generate_image",
                    type="primary",
                    use_container_width=True,
                ):
                    tasks = [
                        (
                            cid,
                            functools.partial(
                                generate_image,
                                base_url,
                                cid,
                                content_type,
                                st.session_state.get(f"gen_model_{cid}", ALL_MODELS[0]),
                            ),
                        )
                        for cid in selected_ids
                    ]
                    with st.spinner(f"{len(tasks)}개 항목 이미지 생성 중..."):
                        errors = _run_bulk_concurrent(tasks)
                    fetch_contents.clear()
                    _deselect_all()
                    st.session_state.last_error = "\n".join(errors) if errors else None
                    st.rerun()
            col_idx += 1

        for label, to_status in actions:
            if not selected_ids:
                break
            with cols[col_idx]:
                btn_type = "primary" if to_status == "approved" else "secondary"
                if st.button(
                    label,
                    key=f"bulk_{to_status}",
                    type=btn_type,
                    use_container_width=True,
                ):
                    errors = []
                    for content_id in selected_ids:
                        try:
                            update_status(base_url, content_id, status, to_status)
                        except Exception as e:
                            errors.append(f"#{content_id}: {e}")
                    fetch_contents.clear()
                    _deselect_all()
                    st.session_state.last_error = "\n".join(errors) if errors else None
                    st.rerun()
            col_idx += 1

        with cols[-1]:
            select_label = "전체 해제" if all_selected else "전체 선택"
            if st.button(select_label, key="bulk_select_all", use_container_width=True):
                if all_selected:
                    _deselect_all()
                else:
                    st.session_state.sel_gen += 1
                    st.session_state["_select_all_ids"] = all_ids
                st.rerun()


# ── Pagination ────────────────────────────────────────────────────────────────


def render_pagination(
    page_index: int, is_last_page: bool, position: str = "top"
) -> None:
    col_prev, col_info, col_next = st.columns([1, 2, 1])
    with col_prev:
        if st.button(
            "◀ 이전",
            key=f"prev_{position}",
            disabled=(page_index == 0),
            use_container_width=True,
        ):
            st.session_state.page_index -= 1
            st.rerun()
    with col_info:
        st.markdown(
            f"<div style='text-align:center;padding-top:6px'>페이지 {page_index + 1}</div>",
            unsafe_allow_html=True,
        )
    with col_next:
        if st.button(
            "다음 ▶",
            key=f"next_{position}",
            disabled=is_last_page,
            use_container_width=True,
        ):
            st.session_state.page_index += 1
            st.rerun()


# ── Card ──────────────────────────────────────────────────────────────────────

_STAGE_RANK = {"raw": 0, "analyzed": 1, "pending": 2, "approved": 3}


def _backward_options(status: str) -> list[str]:
    if status == "rejected":
        return ["raw", "analyzed", "pending"]
    rank = _STAGE_RANK.get(status)
    if rank is None:  # "used" — no backward move allowed
        return []
    return [s for s in ("raw", "analyzed", "pending", "approved") if _STAGE_RANK[s] < rank]


def render_action_buttons(item: dict) -> None:
    content_id = item["id"]
    status = item["status"]
    content_type = item["type"]
    base_url = st.session_state.base_url

    def do_status(to: str) -> None:
        try:
            update_status(base_url, content_id, status, to)
            st.session_state.last_error = None
            fetch_contents.clear()
        except Exception as e:
            st.session_state.last_error = str(e)
        st.rerun()

    if status == "raw":
        col1, col2, *_ = st.columns(6)
        with col1:
            if st.button(
                "Analyze",
                key=f"analyze_{content_id}",
                type="primary",
                use_container_width=True,
            ):
                try:
                    analyze_content(base_url, content_id, content_type)
                    st.session_state.last_error = None
                    fetch_contents.clear()
                except Exception as e:
                    st.session_state.last_error = str(e)
                st.rerun()
        with col2:
            if st.button(
                "Reject", key=f"reject_{content_id}", use_container_width=True
            ):
                do_status("rejected")

    elif status == "analyzed":
        gen_model = st.selectbox(
            "이미지 모델",
            ALL_MODELS,
            key=f"gen_model_{content_id}",
        )
        col1, col2, *_ = st.columns(6)
        with col1:
            if st.button(
                "이미지 생성",
                key=f"gen_image_{content_id}",
                type="primary",
                use_container_width=True,
            ):
                try:
                    generate_image(base_url, content_id, content_type, gen_model)
                    st.session_state.last_error = None
                    fetch_contents.clear()
                except Exception as e:
                    st.session_state.last_error = str(e)
                st.rerun()
        with col2:
            if st.button(
                "Reject", key=f"reject_{content_id}", use_container_width=True
            ):
                do_status("rejected")

    elif status == "pending":
        col1, col2, *_ = st.columns(6)
        with col1:
            if st.button(
                "Approve",
                key=f"approve_{content_id}",
                type="primary",
                use_container_width=True,
            ):
                do_status("approved")
        with col2:
            if st.button(
                "Reject", key=f"reject_{content_id}", use_container_width=True
            ):
                do_status("rejected")

    elif status == "approved":
        col1, *_ = st.columns(6)
        with col1:
            if st.button(
                "Reject", key=f"reject_{content_id}", use_container_width=True
            ):
                do_status("rejected")

    backward_options = _backward_options(status)
    if backward_options:
        st.caption("이전 단계로 되돌리기")
        col_sel, col_btn = st.columns([3, 1])
        with col_sel:
            target = st.selectbox(
                "되돌릴 상태",
                backward_options,
                key=f"backward_target_{content_id}",
                label_visibility="collapsed",
            )
        with col_btn:
            if st.button(
                "되돌리기",
                key=f"backward_btn_{content_id}",
                use_container_width=True,
            ):
                do_status(target)


def render_image_regenerate_expander(item: dict) -> None:
    if item["status"] != "pending":
        return

    content_id = item["id"]
    content_type = item["type"]
    base_url = st.session_state.base_url
    is_reddit_meme = content_type == "reddit_meme"

    with st.expander("이미지 재생성"):
        if is_reddit_meme:
            st.info("reddit_meme은 이미지 재생성을 지원하지 않습니다.")
        else:
            col_model, col_type = st.columns(2)
            with col_model:
                regen_model = st.selectbox(
                    "모델",
                    ALL_MODELS,
                    key=f"regen_model_{content_id}",
                )
            with col_type:
                regen_type = st.selectbox(
                    "재생성 타입",
                    ALL_REGENERATE_TYPES,
                    key=f"regen_type_{content_id}",
                    format_func=lambda t: REGENERATE_TYPE_LABELS[t],
                )
            prompt = st.text_input(
                "재생성 프롬프트",
                key=f"regen_prompt_{content_id}",
                placeholder="이미지 재생성 방향 입력",
            )
            if st.button(
                "이미지 재생성",
                key=f"regen_image_{content_id}",
                type="primary",
                disabled=not prompt,
            ):
                try:
                    regenerate_image(
                        base_url, content_id, content_type, regen_model, prompt, regen_type
                    )
                    st.session_state.last_error = None
                    fetch_contents.clear()
                    st.rerun()
                except Exception as e:
                    st.error(f"이미지 재생성 실패: {e}")


def render_reanalyze_expander(item: dict) -> None:
    if item["status"] == "raw":
        return

    content_id = item["id"]
    content_type = item["type"]
    base_url = st.session_state.base_url

    with st.expander("필드 재분석"):
        selected_fields = []
        for field in REANALYZABLE_FIELDS:
            col_check, col_label, col_input = st.columns([1, 2, 5])
            with col_check:
                checked = st.checkbox(
                    "", key=f"chk_{content_id}_{field}", label_visibility="collapsed"
                )
            with col_label:
                st.markdown(f"`{field}` ({REANALYZABLE_FIELD_LABELS[field]})")
            with col_input:
                guide = st.text_input(
                    "프롬프트 가이드",
                    key=f"pg_{content_id}_{field}",
                    label_visibility="collapsed",
                    placeholder="재분석 방향 가이드 (선택)",
                    disabled=not checked,
                )
            if checked:
                selected_fields.append({"field_name": field, "prompt_guide": guide})

        if st.button(
            "재분석",
            key=f"reanalyze_{content_id}",
            type="primary",
            disabled=not selected_fields,
        ):
            try:
                reanalyze_fields(base_url, content_id, content_type, selected_fields)
                st.session_state.last_error = None
                fetch_contents.clear()
                st.rerun()
            except Exception as e:
                st.error(f"재분석 실패: {e}")


def render_fields(item: dict) -> None:
    content_type = item.get("type", "")

    if content_type == "reddit_meme":
        if item.get("title"):
            st.markdown(f"**제목:** {item['title']}")
        if item.get("content"):
            st.markdown(f"**밈 텍스트:** {item['content']}")
        if item.get("content_translation"):
            st.markdown(f"**번역:** {item['content_translation']}")
        if item.get("expression"):
            st.markdown(f"**핵심 표현:** `{item['expression']}`")
        if item.get("expression_translation"):
            st.markdown(f"**표현 번역:** {item['expression_translation']}")
        if item.get("background"):
            st.markdown(f"**배경:** {item['background']}")

    elif content_type == "quote":
        if item.get("content"):
            st.markdown(f"**인용:** {item['content']}")
        if item.get("content_translation"):
            st.markdown(f"**번역:** {item['content_translation']}")
        if item.get("expression"):
            st.markdown(f"**핵심 표현:** `{item['expression']}`")
        if item.get("expression_translation"):
            st.markdown(f"**표현 번역:** {item['expression_translation']}")
        if item.get("background"):
            st.markdown(f"**배경:** {item['background']}")
        if item.get("author"):
            st.caption(f"— {item['author']}")

    elif content_type == "literal_quote":
        if item.get("title"):
            st.markdown(f"**작품:** {item['title']} ({item.get('literal_type', '')})")
        if item.get("content"):
            st.markdown(f"**인용:** {item['content']}")
        if item.get("content_translation"):
            st.markdown(f"**번역:** {item['content_translation']}")
        if item.get("expression"):
            st.markdown(f"**핵심 표현:** `{item['expression']}`")
        if item.get("expression_translation"):
            st.markdown(f"**표현 번역:** {item['expression_translation']}")
        if item.get("background"):
            st.markdown(f"**배경:** {item['background']}")
        if item.get("author"):
            st.caption(f"— {item['author']}")

    elif content_type == "fact":
        if item.get("content"):
            st.markdown(f"**팩트:** {item['content']}")
        if item.get("content_translation"):
            st.markdown(f"**번역:** {item['content_translation']}")
        if item.get("background"):
            st.markdown(f"**배경:** {item['background']}")


def render_card(item: dict) -> None:
    content_id = item["id"]
    status = item["status"]
    content_type = item["type"]
    color = STATUS_COLORS.get(status, "gray")

    with st.container(border=True):
        col_check, col_info = st.columns([0.3, 9.7])
        with col_check:
            preselected = content_id in st.session_state.get("_select_all_ids", set())
            st.checkbox(
                "선택",
                value=preselected,
                key=_sel_key(content_id),
                label_visibility="collapsed",
            )
        with col_info:
            st.markdown(
                f"**#{content_id}** &nbsp; `{content_type}` &nbsp; :{color}[{status.upper()}]"
            )
        created = (item.get("created_at") or "")[:10]
        meta = f"생성일: {created}"
        if item.get("author"):
            meta = f"작성자: {item['author']}  |  " + meta
        if item.get("used_at"):
            meta += f"  |  사용일: {item['used_at']}"
        st.caption(meta)

        if item.get("image_url"):
            col_img, col_fields = st.columns([1, 3])
            with col_img:
                st.markdown(
                    f'<a href="{item["image_url"]}" target="_blank">'
                    f'<img src="{item["image_url"]}" width="200" style="border-radius:4px;cursor:pointer"></a>',
                    unsafe_allow_html=True,
                )
            with col_fields:
                render_fields(item)
        else:
            render_fields(item)

        st.divider()
        render_action_buttons(item)
        render_image_regenerate_expander(item)
        render_reanalyze_expander(item)


# ── Main ──────────────────────────────────────────────────────────────────────


def render_content_page() -> None:
    render_sidebar()

    st.title("Meow Content Dashboard")

    if st.session_state.last_error:
        st.error(f"API 오류: {st.session_state.last_error}")

    try:
        items = fetch_contents(
            st.session_state.base_url,
            st.session_state.content_type,
            st.session_state.content_status,
            st.session_state.page_index,
            st.session_state.page_size,
        )
    except requests.exceptions.ConnectionError:
        st.error(f"API 서버에 연결할 수 없습니다: {st.session_state.base_url}")
        return
    except Exception as e:
        st.error(f"오류 발생: {e}")
        return

    is_last_page = len(items) < st.session_state.page_size
    st.caption(f"{len(items)}개 표시 중")

    if not items:
        st.info("해당 조건에 맞는 콘텐츠가 없습니다.")
        return

    render_pagination(st.session_state.page_index, is_last_page, position="top")

    for item in items:
        render_card(item)

    st.session_state.pop("_select_all_ids", None)
    selected_ids = _get_selected_ids(items)
    render_pagination(st.session_state.page_index, is_last_page, position="bottom")
    render_bulk_actions(items, selected_ids)


def main() -> None:
    st.set_page_config(page_title="Meow Content Dashboard", layout="wide")
    if not require_auth():
        return
    init_state()

    pg = st.navigation(
        [
            st.Page(render_content_page, title="콘텐츠", url_path="contents", default=True),
            st.Page(render_usage_page, title="토큰 사용량", url_path="usage"),
        ]
    )
    pg.run()


if __name__ == "__main__":
    main()
