from moviepy import (
    TextClip,
    CompositeVideoClip,
    CompositeAudioClip,
    AudioFileClip,
    ImageClip,
    concatenate_videoclips,
    vfx,
)
from moviepy.video.VideoClip import VideoClip
import os
import random
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
                    vfx.CrossFadeIn(1),
                    vfx.CrossFadeOut(1)
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

    # 添加BGM处理逻辑
    bgm_path = "assets/bgm"
    if os.path.exists(bgm_path) and os.path.isdir(bgm_path):
        bgm_files = [
            f for f in os.listdir(bgm_path) 
            if f.lower().endswith(('.mp3', '.wav', '.ogg', '.m4a'))
        ]
        if bgm_files:
            selected_bgm = random.choice(bgm_files)
            bgm_clip = AudioFileClip(os.path.join(bgm_path, selected_bgm))
            # 设置BGM音量为原声的30%
            bgm_clip = bgm_clip.with_volume_scaled(0.1)
            # 循环BGM以匹配视频长度
            bgm_clip = bgm_clip.with_effects([vfx.Loop()]).with_duration(duration=final_clip.duration)
            # 将BGM与原音频混合
            original_audio = final_clip.audio
            mixed_audio = CompositeAudioClip([original_audio, bgm_clip])
            final_clip = final_clip.with_audio(mixed_audio)

    final_clip.write_videofile(
        f"output/chapters/chapter_{current_chapter}/generated_video.mp4",
        fps=24,
    )


if __name__ == "__main__":
    generate_video(1)