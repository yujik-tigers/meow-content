class NoApprovedContentError(Exception):
    def __init__(self) -> None:
        super().__init__("No approved content available")


class ContentNotFoundError(Exception):
    def __init__(self, content_id: int) -> None:
        super().__init__(f"Content not found: {content_id}")
