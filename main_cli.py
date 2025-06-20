#!/usr/bin/env python3
"""
带命令行参数支持的主程序文件

使用示例：
python main_cli.py --scene-count 10 --start-chapter 1 --end-chapter 3
python main_cli.py --help  # 查看所有可用参数
"""

import argparse
import asyncio
import logfire
from agents.main_agent import start_video_generation

# 配置logfire日志监控
logfire.configure()
logfire.instrument_pydantic_ai()


def parse_arguments():
    """解析命令行参数"""
    parser = argparse.ArgumentParser(
        description="AI视频生成系统 - 支持可配置的场景数量",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用示例:
  %(prog)s --scene-count 10                    # 生成10个场景的视频
  %(prog)s --scene-count 20 --end-chapter 3   # 生成3章，每章20个场景
  %(prog)s --start-chapter 2 --end-chapter 5  # 生成第2-5章，默认5个场景
        """
    )
    
    parser.add_argument(
        '--scene-count', 
        type=int, 
        default=5,
        metavar='N',
        help='每章节的场景数量 (范围: 5-50, 默认: 5)'
    )
    
    parser.add_argument(
        '--start-chapter',
        type=int,
        default=1,
        metavar='N',
        help='开始章节号 (默认: 1)'
    )
    
    parser.add_argument(
        '--end-chapter',
        type=int,
        default=1,
        metavar='N',
        help='结束章节号 (默认: 1)'
    )
    
    parser.add_argument(
        '--outline-file',
        type=str,
        metavar='FILE',
        help='从文件读取故事大纲'
    )
    
    parser.add_argument(
        '--config',
        type=str,
        metavar='FILE',
        help='使用配置文件 (Python文件格式)'
    )
    
    return parser.parse_args()


def load_outline_from_file(file_path: str) -> str:
    """从文件读取故事大纲"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return f.read().strip()
    except FileNotFoundError:
        print(f"❌ 错误：找不到大纲文件 {file_path}")
        exit(1)
    except Exception as e:
        print(f"❌ 错误：读取大纲文件时出错 {e}")
        exit(1)


def load_config_from_file(file_path: str) -> dict:
    """从配置文件读取配置"""
    try:
        import importlib.util
        spec = importlib.util.spec_from_file_location("config", file_path)
        if spec is None or spec.loader is None:
            raise ImportError(f"无法加载配置文件: {file_path}")
            
        config = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(config)
        
        return {
            'start_chapter': getattr(config, 'START_CHAPTER', 1),
            'end_chapter': getattr(config, 'END_CHAPTER', 1),
            'scene_count': getattr(config, 'SCENE_COUNT', 5),
            'outline': getattr(config, 'STORY_OUTLINE', ''),
            'requirement': getattr(config, 'GENERATION_REQUIREMENT', '')
        }
    except Exception as e:
        print(f"❌ 错误：读取配置文件时出错 {e}")
        exit(1)


def validate_scene_count(scene_count: int) -> int:
    """验证场景数量参数"""
    if scene_count < 5:
        print(f"⚠️ 警告：场景数量 {scene_count} 少于最小值5，已调整为5")
        return 5
    elif scene_count > 50:
        print(f"⚠️ 警告：场景数量 {scene_count} 超过最大值50，已调整为50")
        return 50
    return scene_count


async def main():
    """主函数"""
    args = parse_arguments()
    
    print("🎬 AI视频生成系统 (可配置场景数量版本)")
    print("=" * 60)
    
    # 处理配置文件
    if args.config:
        print(f"📄 从配置文件加载设置: {args.config}")
        config = load_config_from_file(args.config)
        start_chapter = config['start_chapter']
        end_chapter = config['end_chapter']
        scene_count = config['scene_count']
        outline = config['outline']
        requirement = config['requirement']
    else:
        # 使用命令行参数和默认值
        start_chapter = args.start_chapter
        end_chapter = args.end_chapter
        scene_count = args.scene_count
        requirement = "情节跌宕起伏，要体现出复仇的爽感，要有甜宠剧的风格和逆袭剧的风格，这个剧情的受众群体是女性，请结合这些要素进行生成。"
        
        # 处理大纲
        if args.outline_file:
            outline = load_outline_from_file(args.outline_file)
            print(f"📖 从文件加载大纲: {args.outline_file}")
        else:
            # 默认大纲
            outline = """
翠花是一个孤儿，生活在一个a镇中，她被一个普通人家收养。
但是她的父母却经常欺负他，她有一个姐姐，对她也很苛刻，什么事儿都让翠花来做。
并且还姐姐做了什么坏事还让翠花背锅。

但突然有一天，小镇中的年轻富少遇见了翠花，惊奇的发现翠花竟然和她已故的妹妹有着惊人的相似之处。
在富少的调查下，发现翠花其实是他的亲妹妹。
他也了解了翠花的处境，以及她在养父母家中所遭受的虐待。

翠花的逆袭之路由此开始。
            """.strip()
    
    # 验证和调整参数
    scene_count = validate_scene_count(scene_count)
    
    if start_chapter > end_chapter:
        print("❌ 错误：开始章节号不能大于结束章节号")
        return
    
    # 显示配置信息
    print("🎯 生成配置:")
    print(f"   📚 章节范围: 第{start_chapter}章 - 第{end_chapter}章")
    print(f"   🎬 每章场景数: {scene_count}个")
    print(f"   📝 大纲长度: {len(outline)}字符")
    print("-" * 60)
    
    # 启动视频生成
    try:
        result = await start_video_generation(
            outline=outline,
            start_chapter=start_chapter,
            end_chapter=end_chapter,
            scene_count=scene_count,
            requirement=requirement
        )
        
        print("\n" + "=" * 60)
        print("🎉 生成完成!")
        print("📋 结果:")
        print(result)
        print("=" * 60)
        
    except KeyboardInterrupt:
        print("\n⚠️ 用户中断了程序执行")
    except Exception as e:
        print(f"\n❌ 生成过程中出现错误: {str(e)}")


if __name__ == "__main__":
    asyncio.run(main())
