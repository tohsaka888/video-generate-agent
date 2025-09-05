import { NextResponse } from "next/server";

// 将实现迁移到 Python（FastAPI），此处仅做转发以保持前端路径不变。
// 配置后端地址：设置环境变量 BACKEND_BASE_URL，例如 http://localhost:8000
const BASE_URL = process.env.BACKEND_BASE_URL || "http://localhost:8000";

export async function GET() {
  try {
    const res = await fetch(`${BASE_URL}/api/output-tree`, {
      // 明确禁用缓存，保证得到最新输出目录结构
      cache: "no-store",
      // 服务器路由请求无需额外 headers；如需鉴权可在此追加
    });
    const data = await res.json();
    return NextResponse.json(data, { status: res.status });
  } catch (err: unknown) {
    console.error("[file-tree] Proxy to Python backend failed:", err);
    return NextResponse.json(
      { error: "Failed to fetch file tree from backend" },
      { status: 502 }
    );
  }
}
