from dataclasses import dataclass
from pathlib import Path


@dataclass
class ClipSpec:
    file_path: Path
    category_path: list[str]
    width: int
    height: int
    fps: float
    has_audio: bool
    duration_frames: int
    in_frame: int | None = None
    out_frame: int | None = None
    flag: str = "none"  # "none" | "pick" | "reject"

    def effective_in(self) -> int:
        return self.in_frame if self.in_frame is not None else 0

    def effective_out(self) -> int:
        return self.out_frame if self.out_frame is not None else self.duration_frames
