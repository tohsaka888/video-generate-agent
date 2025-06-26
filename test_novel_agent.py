#!/usr/bin/env python3
"""
测试新的 Novel Agent 智能读取功能
"""
import asyncio
import os
from agents.novel_agent import novel_agent, NovelAgentDeps

async def test_novel_agent():
    """测试 novel agent 的功能"""
    
    print("🚀 开始测试 Novel Agent 智能读取功能...")
    
    # 测试参数
    test_deps = NovelAgentDeps(
        current_chapter=1,
        novel_file_path="",  # 可以设置为真实的小说文件路径
        chunk_size=500,
        overlap_sentences=1
    )
    
    try:
        # 测试基本章节生成功能
        print("\n📝 测试基本章节生成功能...")
        
        prompt = """
请生成一个关于年轻法师艾莉丝的冒险故事第1章。

故事大纲：
- 艾莉丝是一名在魔法学院学习的年轻法师
- 她性格开朗但有时会冲动
- 在学院中遇到了好友凯尔，他是一名战士学徒
- 第一章应该描述她们的日常学习生活和初次相遇

要求：
- 章节长度控制在1000-1500字
- 描述要生动具体
- 要有对话和情节发展
- 为后续章节埋下伏笔

请使用 save_chapter_content 工具保存生成的内容。
"""
        
        async with novel_agent.run_mcp_servers():
            result = await novel_agent.run(prompt, deps=test_deps)
            print(f"✅ 章节生成完成: {result.data}")
        
        # 检查生成的文件
        output_path = "output/chapters/chapter_1/index.txt"
        if os.path.exists(output_path):
            with open(output_path, 'r', encoding='utf-8') as f:
                content = f.read()
            print(f"\n📖 生成的章节内容预览 ({len(content)} 字符):")
            print("=" * 50)
            print(content[:300] + "..." if len(content) > 300 else content)
            print("=" * 50)
        
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()

async def test_novel_reader():
    """测试 NovelReader 的功能（如果有源文件的话）"""
    
    from utils.novel_reader import NovelReader
    
    print("\n🔍 测试 NovelReader 功能...")
    
    # 创建一个测试文件
    test_file = "test_novel.txt"
    test_content = """这是一个测试小说文件。第一段内容描述了主角的背景。

主角张三是一个普通的程序员，每天过着朝九晚五的生活。但是有一天，他发现了一个神秘的代码。

这个代码似乎有着不同寻常的力量。当张三运行这段代码时，奇妙的事情发生了。

他发现自己可以通过代码来改变现实世界。这让他既兴奋又害怕。

张三决定谨慎地使用这个能力，他开始研究这段代码的原理。经过几天的研究，他发现这段代码来自一个古老的文明。

这个文明早已消失，但他们留下了这些神奇的代码碎片。张三意识到，他可能是唯一知道这个秘密的人。

随着故事的深入，张三遇到了更多的挑战。他必须在保护这个秘密和使用它来帮助他人之间找到平衡。

故事还在继续，张三的冒险才刚刚开始..."""
    
    try:
        # 创建测试文件
        with open(test_file, 'w', encoding='utf-8') as f:
            f.write(test_content)
        
        reader = NovelReader()
        
        # 初始化文件
        print(f"📚 初始化测试文件: {test_file}")
        state = reader.init_novel_file(test_file, chunk_size=100)
        print(f"✅ 文件初始化成功，大小: {state.total_size} 字节")
        
        # 读取几个块
        chunk_count = 0
        while chunk_count < 3:
            chunk_text, is_end, read_info = reader.read_next_chunk(test_file, overlap_sentences=1)
            
            if not chunk_text:
                print("📄 已到达文件末尾")
                break
                
            chunk_count += 1
            print(f"\n📖 第 {chunk_count} 个文本块:")
            print(f"   大小: {read_info['chunk_size']} 字符")
            print(f"   进度: {read_info['progress']:.1f}%")
            print(f"   重叠: {'是' if read_info['has_overlap'] else '否'}")
            print(f"   内容: {chunk_text[:100]}...")
            
            if is_end:
                print("📄 已到达文件末尾")
                break
        
        # 获取进度信息
        progress = reader.get_reading_progress(test_file)
        if progress:
            print(f"\n📊 最终进度: {progress['progress']:.1f}%")
        
        # 清理测试文件
        os.remove(test_file)
        print(f"🗑️ 已删除测试文件: {test_file}")
        
    except Exception as e:
        print(f"❌ NovelReader 测试失败: {e}")
        import traceback
        traceback.print_exc()
        
        # 确保清理测试文件
        if os.path.exists(test_file):
            os.remove(test_file)

if __name__ == "__main__":
    print("🎯 Novel Agent 功能测试开始...")
    
    # 运行测试
    asyncio.run(test_novel_agent())
    asyncio.run(test_novel_reader())
    
    print("\n🎉 测试完成!")
