from moviepy import CompositeVideoClip, VideoFileClip
from moviepy.video.tools.subtitles import SubtitlesClip

if __name__ == "__main__":
    # Example usage
    video = VideoFileClip("output/chapters/chapter_1/video.mp4")
    subtitles = SubtitlesClip(
        subtitles="output/chapters/chapter_1/srt/srt_1.srt",
        font="Arial",
        encoding="utf-8",

    )
    # text = TextClip(
    #     text="在一个魔法与科技并存的世界中，年轻的女巫艾莉丝踏上了寻找失落神器的旅程。",
    #     font_size=1000,
    #     font='Arial'
    # )

    # Combine video and subtitles
    final_video = CompositeVideoClip(
        [video, subtitles.with_position(("center", "bottom"))]
    )

    # Write the final video to a file
    final_video.write_videofile(
        "output_video.mp4",
        fps=24,
    )
