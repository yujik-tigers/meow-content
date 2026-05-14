import hashlib
import logging
import os
import threading
import time

import requests
import streamlit as st

_logger = logging.getLogger(__name__)

DEFAULT_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000")
_ADMIN_PW_HASH = hashlib.sha256(os.environ["ADMIN_PASSWORD"].encode()).hexdigest()

MAX_FAILURES = 5
LOCKOUT_SECONDS = 60


@st.cache_resource
def _auth_state() -> tuple[threading.Lock, dict[str, list[float]]]:
    return threading.Lock(), {}


def _client_ip() -> str:
    headers = st.context.headers
    forwarded = headers.get("X-Forwarded-For") or headers.get("X-Real-Ip", "unknown")
    return forwarded.split(",")[0].strip()
ALL_STATUSES = ["pending", "approved", "rejected", "used"]
STATUS_COLORS = {
    "pending": "orange",
    "approved": "green",
    "rejected": "red",
    "used": "blue",
}


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
    st.title("Meow Meme Dashboard")
    st.subheader("로그인")

    ip = _client_ip()
    remaining = _is_locked_out(ip)
    if remaining > 0:
        st.error(f"너무 많은 실패 시도로 잠겼습니다. {int(remaining)}초 후에 다시 시도하세요.")
        return False

    pw = st.text_input("비밀번호", type="password")
    if st.button("로그인"):
        if hashlib.sha256(pw.encode()).hexdigest() == _ADMIN_PW_HASH:
            _clear_failures(ip)
            st.session_state.authenticated = True
            st.rerun()
        else:
            _record_failure(ip)
            remaining = _is_locked_out(ip)
            if remaining > 0:
                st.error(f"너무 많은 실패 시도로 잠겼습니다. {int(remaining)}초 후에 다시 시도하세요.")
            else:
                left = MAX_FAILURES - len(_auth_state()[1].get(ip, []))
                st.error(f"비밀번호가 올바르지 않습니다. ({left}회 남음)")
    return False


def init_state() -> None:
    st.session_state.setdefault("base_url", DEFAULT_BASE_URL)
    st.session_state.setdefault("active_statuses", ["pending"])
    st.session_state.setdefault("page_index", 0)
    st.session_state.setdefault("page_size", 20)
    st.session_state.setdefault("last_error", None)


def fetch_memes(
    base_url: str, statuses: list[str], page_index: int, page_size: int
) -> list[dict]:
    params: list[tuple[str, str | int]] = [("status", s) for s in statuses]
    params += [("page_index", page_index), ("page_size", page_size)]
    resp = requests.get(
        f"{base_url}/api/v1/contents/memes/search", params=params, timeout=10
    )
    resp.raise_for_status()
    return resp.json().get("content", [])


def update_background(base_url: str, meme_id: int, background: str) -> None:
    resp = requests.patch(
        f"{base_url}/api/v1/contents/memes/{meme_id}/background",
        json={"background": background},
        timeout=10,
    )
    resp.raise_for_status()


def update_status(base_url: str, meme_id: int, new_status: str) -> None:
    resp = requests.patch(
        f"{base_url}/api/v1/contents/memes/{meme_id}/status",
        json={"status": new_status},
        timeout=10,
    )
    resp.raise_for_status()


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
        selected: list[str] = []
        for s in ALL_STATUSES:
            if st.checkbox(
                s.capitalize(),
                value=(s in st.session_state.active_statuses),
                key=f"cb_{s}",
            ):
                selected.append(s)
        if selected != st.session_state.active_statuses:
            st.session_state.active_statuses = selected
            st.session_state.page_index = 0

        st.divider()
        page_size = st.select_slider(
            "Page Size", options=[10, 20, 50], value=st.session_state.page_size
        )
        if page_size != st.session_state.page_size:
            st.session_state.page_size = page_size
            st.session_state.page_index = 0


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


def render_action_buttons(meme: dict) -> None:
    status = meme["status"]
    meme_id = meme["id"]
    base_url = st.session_state.base_url

    def do_update(new_status: str) -> None:
        try:
            update_status(base_url, meme_id, new_status)
            st.session_state.last_error = None
        except Exception as e:
            st.session_state.last_error = str(e)
        st.rerun()

    if status == "pending":
        col1, col2, *_ = st.columns(6)
        with col1:
            if st.button(
                "Approve",
                key=f"approve_{meme_id}",
                type="primary",
                use_container_width=True,
            ):
                do_update("approved")
        with col2:
            if st.button("Reject", key=f"reject_{meme_id}", use_container_width=True):
                do_update("rejected")
    elif status == "approved":
        col1, col2, *_ = st.columns(6)
        with col1:
            if st.button("Reject", key=f"reject_{meme_id}", use_container_width=True):
                do_update("rejected")
        with col2:
            if st.button("Reset", key=f"pending_{meme_id}", use_container_width=True):
                do_update("pending")
    elif status == "rejected":
        col1, col2, *_ = st.columns(6)
        with col1:
            if st.button(
                "Approve",
                key=f"approve_{meme_id}",
                type="primary",
                use_container_width=True,
            ):
                do_update("approved")
        with col2:
            if st.button("Reset", key=f"pending_{meme_id}", use_container_width=True):
                do_update("pending")


def render_card(meme: dict) -> None:
    meme_id = meme["id"]
    with st.container(border=True):
        col_img, col_meta = st.columns([1, 3])

        with col_img:
            st.markdown(
                f'<a href="{meme["image_url"]}" target="_blank">'
                f'<img src="{meme["image_url"]}" width="200" style="border-radius:4px;cursor:pointer"></a>',
                unsafe_allow_html=True,
            )

        with col_meta:
            status = meme["status"]
            color = STATUS_COLORS.get(status, "gray")
            st.markdown(f"**#{meme['id']}** &nbsp; :{color}[{status.upper()}]")
            st.markdown(f"**밈 텍스트:** {meme['meme_text']}")
            st.markdown(f"**밈 텍스트 번역:** {meme['meme_text_translation']}")
            st.markdown(f"**핵심 표현:** `{meme['expressions']}`")
            st.markdown(f"**한국어:** {meme['translation']}")
            st.markdown("**배경:**")
            current_bg = (
                st.text_area(
                    "배경",
                    value=meme.get("background", ""),
                    key=f"bg_{meme_id}",
                    height=80,
                    label_visibility="collapsed",
                )
                or ""
            )
            if current_bg != meme.get("background", ""):
                if st.button("저장", key=f"save_bg_{meme_id}", type="primary"):
                    try:
                        update_background(
                            st.session_state.base_url, meme_id, current_bg
                        )
                        st.success("배경이 저장되었습니다.")
                        st.rerun()
                    except Exception as e:
                        st.error(f"저장 실패: {e}")
            created = meme.get("created_at", "")[:10]
            st.caption(
                f"출처: {meme['source']}  |  작성자: {meme['author']}  |  생성일: {created}"
            )
            if meme.get("used_at"):
                st.caption(f"사용일: {meme['used_at']}")

        render_action_buttons(meme)


def main() -> None:
    st.set_page_config(page_title="Meow Meme Dashboard", layout="wide")
    if not require_auth():
        return
    init_state()
    render_sidebar()

    st.title("Meow Meme Dashboard")

    if st.session_state.last_error:
        st.error(f"API 오류: {st.session_state.last_error}")

    if not st.session_state.active_statuses:
        st.warning("사이드바에서 하나 이상의 상태를 선택하세요.")
        return

    try:
        memes = fetch_memes(
            st.session_state.base_url,
            st.session_state.active_statuses,
            st.session_state.page_index,
            st.session_state.page_size,
        )
    except requests.exceptions.ConnectionError:
        st.error(f"API 서버에 연결할 수 없습니다: {st.session_state.base_url}")
        return
    except Exception as e:
        st.error(f"오류 발생: {e}")
        return

    is_last_page = len(memes) < st.session_state.page_size

    st.caption(f"{len(memes)}개 표시 중")

    if not memes:
        st.info("해당 조건에 맞는 밈이 없습니다.")
        return

    for meme in memes:
        render_card(meme)

    render_pagination(st.session_state.page_index, is_last_page, position="bottom")


if __name__ == "__main__":
    main()
