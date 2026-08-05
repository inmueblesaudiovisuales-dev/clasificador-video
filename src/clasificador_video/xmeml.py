from pathlib import Path
from urllib.parse import quote

from clasificador_video.models import ClipSpec
from clasificador_video.rate import rate_for_fps


def _rate_xml(fps: float) -> str:
    timebase, ntsc = rate_for_fps(fps)
    return f"<rate><timebase>{timebase}</timebase><ntsc>{'TRUE' if ntsc else 'FALSE'}</ntsc></rate>"


def _pathurl(path: Path) -> str:
    encoded = quote(str(path))
    return f"file://localhost{encoded}"


def _audio_block_xml(source_channel: int, channel_label: str) -> str:
    return (
        "<audio>"
        "<samplecharacteristics><depth>16</depth><samplerate>48000</samplerate></samplecharacteristics>"
        "<channelcount>1</channelcount><layout>stereo</layout>"
        f"<audiochannel><sourcechannel>{source_channel}</sourcechannel>"
        f"<channellabel>{channel_label}</channellabel></audiochannel>"
        "</audio>"
    )


def _file_xml(clip: ClipSpec, file_id: str) -> str:
    audio_xml = ""
    if clip.has_audio:
        audio_xml = _audio_block_xml(1, "left") + _audio_block_xml(2, "right")

    return (
        f'<file id="{file_id}">'
        f"<name>{clip.file_path.name}</name>"
        f"<pathurl>{_pathurl(clip.file_path)}</pathurl>"
        f"{_rate_xml(clip.fps)}"
        f"<duration>{clip.duration_frames}</duration>"
        "<media><video><samplecharacteristics>"
        f"{_rate_xml(clip.fps)}"
        f"<width>{clip.width}</width><height>{clip.height}</height>"
        "<anamorphic>FALSE</anamorphic><pixelaspectratio>square</pixelaspectratio>"
        "<fielddominance>none</fielddominance>"
        f"</samplecharacteristics></video>{audio_xml}</media>"
        "</file>"
    )
