from moviepy import (
    TextClip,
    CompositeVideoClip,
    AudioFileClip,
    ImageClip,
    concatenate_videoclips,
    vfx,
)
from moviepy.video.VideoClip import VideoClip
import os
from moviepy.video.tools.subtitles import SubtitlesClip
from typing import cast

import dotenv

dotenv.load_dotenv()

FONT_PATH = os.getenv("FONT_PATH") or ''

def generate_video(current_chapter: int) -> None:
    # 读取chapter目录下的所有音频文件
    audio_path = f"output/chapters/chapter_{current_chapter}/audio"
    image_path = f"output/chapters/chapter_{current_chapter}/images"
    srt_path = f"output/chapters/chapter_{current_chapter}/srt"

    audio_files = sorted(
        [f"{audio_path}/{f}" for f in os.listdir(audio_path) if f.endswith(".mp3")]
    )

    # 读取chapter目录下的所有图片文件
    image_files = sorted(
        [
            f"{image_path}/{f}"
            for f in os.listdir(image_path)
            if f.endswith((".png", ".jpg", ".jpeg"))
        ]
    )

    # 读取所有srt
    srt_files = sorted(
        [f"{srt_path}/{f}" for f in os.listdir(srt_path) if f.endswith(".srt")]
    )

    clips = []

    for img_path, audio_path, srt_path in zip(image_files, audio_files, srt_files):
        audio_clip = AudioFileClip(audio_path)
        image_clip = ImageClip(img_path, duration=audio_clip.duration)
        srt_clip = SubtitlesClip(
            subtitles=srt_path,
            encoding="utf-8",
            # font='Arial',
            make_textclip=lambda text: TextClip(
                font=FONT_PATH or "Arial",
                text=text,
                font_size=48,
                color="white",
                stroke_color="black",
                stroke_width=1,
                vertical_align="center",
                margin=(10, 10, 10, 48 * 3),
                method="caption",
                text_align="center",
                size=(image_clip.w, None),
            ),
        )

        # Apply effects to image clip and cast to VideoClip for proper typing
        image_with_effects = cast(
            VideoClip,
            image_clip.with_effects(
                [
                    vfx.FadeIn(1),
                    vfx.FadeOut(1),
                    vfx.CrossFadeIn(3),
                    vfx.CrossFadeOut(3),
                ]
            ),
        )

        clips.append(
            CompositeVideoClip(
                [
                    image_with_effects.with_audio(audio_clip),
                    srt_clip.with_position(("center", "bottom")),
                ]
            ),
        )

    # clips[0].write_videofile(
    #     f"output/chapters/chapter_{current_chapter}/video.mp4",
    #     fps=24,
    # )

    # # 合并所有视频片段
    final_clip = concatenate_videoclips(clips=clips, method="compose")

    final_clip.write_videofile(
        f"output/chapters/chapter_{current_chapter}/generated_video.mp4",
        fps=24,
    )


if __name__ == "__main__":
    generate_video(1)
