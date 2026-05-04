class NoApprovedMemeError(Exception):
    def __init__(self) -> None:
        super().__init__("No approved meme available")


class MemeNotFoundError(Exception):
    def __init__(self, meme_id: int) -> None:
        super().__init__(f"Meme not found: {meme_id}")
