import os

import requests
import streamlit as st

DEFAULT_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000")
ALL_STATUSES = ["pending", "approved", "rejected", "used"]
STATUS_COLORS = {
    "pending": "orange",
    "approved": "green",
    "rejected": "red",
    "used": "blue",
}


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


def update_status(base_url: str, meme_id: int, new_status: str) -> None:
    resp = requests.patch(
        f"{base_url}/api/v1/contents/memes/{meme_id}/status",
        json={"status": new_status},
        timeout=10,
    )
    resp.raise_for_status()


def trigger_scraping(base_url: str, count: int) -> None:
    resp = requests.post(
        f"{base_url}/api/v1/contents/memes/scrape",
        json={"count": count},
        timeout=300,
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
        scrape_count = st.number_input("가져올 개수", min_value=1, max_value=10, value=3)
        if st.button("Reddit 스크래핑 실행", use_container_width=True, type="primary"):
            with st.spinner("스크래핑 중..."):
                try:
                    trigger_scraping(str(st.session_state.base_url), int(scrape_count))
                    st.success("완료!")
                except Exception as e:
                    st.error(f"실패: {e}")

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
            st.markdown(f"**핵심 표현:** `{meme['expressions']}`")
            st.markdown(f"**한국어:** {meme['translation']}")
            if meme.get("background"):
                st.markdown(f"**배경:** {meme['background']}")
            created = meme.get("created_at", "")[:10]
            st.caption(
                f"출처: {meme['source']}  |  작성자: {meme['author']}  |  생성일: {created}"
            )
            if meme.get("used_at"):
                st.caption(f"사용일: {meme['used_at']}")

        render_action_buttons(meme)


def main() -> None:
    st.set_page_config(page_title="Meow Meme Dashboard", layout="wide")
    init_state()
    render_sidebar()

    st.title("Meom Meme Dashboard")

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
