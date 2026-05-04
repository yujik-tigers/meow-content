class NoApprovedMemeError(Exception):
    def __init__(self) -> None:
        super().__init__("No approved meme available")
