"use client";
import "@copilotkit/react-ui/styles.css";
import { CopilotChat } from "@copilotkit/react-ui";
import { useCoAgentStateRender, useCoAgent } from "@copilotkit/react-core";
import React, { useRef, useState, useEffect } from "react";
import { FileTree } from "./components/FileTree";
import { FilePreview } from "./components/FilePreview";
import { AgentStateDisplay } from "./components/AgentStateDisplay";
import {
  ProgressIndicator,
  videoGenerationSteps,
} from "./components/ProgressIndicator";

type AgentState = {
  message: string;
  detail: string;
};

interface FileNode {
  name: string;
  type: "file" | "directory";
  path: string;
  children?: FileNode[];
  size?: number;
  mtime?: string;
  ext?: string;
}

export default function App() {
  const [fileTreeData, setFileTreeData] = useState<FileNode | null>(null);
  const [selectedFile, setSelectedFile] = useState<FileNode | null>(null);
  const [sidebarWidth, setSidebarWidth] = useState(300);
  const [previewWidth, setPreviewWidth] = useState(400);
  const [showAgentPanel, setShowAgentPanel] = useState(false);
  const sidebarDragging = useRef(false);
  const previewDragging = useRef(false);

  // 获取文件树数据
  useEffect(() => {
    window.setInterval(() => {
      fetch("/api/file-tree")
        .then((res) => res.json())
        .then((data) => setFileTreeData(data))
        .catch((err) => {
          console.error("Failed to load file tree:", err);
          // 使用 mock 数据作为备用
          import("./mock").then(({ mockdata }) => {
            setFileTreeData(mockdata as FileNode);
          });
        });
    }, 3000);
  }, []);

  // 拖拽事件处理
  const handleSidebarMouseDown = () => {
    sidebarDragging.current = true;
    document.body.style.cursor = "col-resize";
  };

  const handlePreviewMouseDown = () => {
    previewDragging.current = true;
    document.body.style.cursor = "col-resize";
  };

  const handleMouseUp = () => {
    sidebarDragging.current = false;
    previewDragging.current = false;
    document.body.style.cursor = "";
  };

  const handleMouseMove = (e: MouseEvent) => {
    if (sidebarDragging.current) {
      const minWidth = 200;
      const maxWidth = 500;
      setSidebarWidth(Math.max(minWidth, Math.min(maxWidth, e.clientX)));
    }
    if (previewDragging.current) {
      const minWidth = 300;
      const maxWidth = 600;
      const rightEdge = window.innerWidth - e.clientX;
      setPreviewWidth(Math.max(minWidth, Math.min(maxWidth, rightEdge)));
    }
  };

  useEffect(() => {
    window.addEventListener("mousemove", handleMouseMove);
    window.addEventListener("mouseup", handleMouseUp);

    return () => {
      window.removeEventListener("mousemove", handleMouseMove);
      window.removeEventListener("mouseup", handleMouseUp);
    };
  });

  // CopilotKit 状态渲染
  useCoAgentStateRender<AgentState>({
    name: "main_agent",
    render: ({ state }) => {
      if (!state.message)
        return <div className="text-sm text-gray-500">等待 Agent 启动...</div>;
      return <AgentStateDisplay state={state} />;
    },
  });

  return (
    <div className="flex h-screen bg-gray-100">
      {/* 左侧文件树 */}
      <div
        className="bg-white border-r border-gray-300 flex flex-col"
        style={{ width: sidebarWidth }}
      >
        <div className="px-4 py-3 border-b border-gray-200 bg-gray-50 flex items-center justify-between">
          <h2 className="font-semibold text-gray-800">输出文件</h2>
          {/* <button
            onClick={() => setShowAgentPanel(!showAgentPanel)}
            className="text-sm px-2 py-1 bg-blue-100 text-blue-600 rounded hover:bg-blue-200 transition-colors"
          >
            {showAgentPanel ? "隐藏状态" : "显示状态"}
          </button> */}
        </div>
        <div className="flex-1 overflow-hidden">
          {fileTreeData ? (
            <FileTree
              data={fileTreeData}
              onFileSelect={(file) => setSelectedFile(file)}
            />
          ) : (
            <div className="flex items-center justify-center h-32 text-gray-500">
              <div className="text-center">
                <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-500 mx-auto mb-2"></div>
                <div>加载中...</div>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* 左侧拖拽条 */}
      <div
        className="w-1 cursor-col-resize bg-gray-300 hover:bg-blue-400 transition-colors"
        onMouseDown={handleSidebarMouseDown}
      />

      {/* 中间区域 */}
      <div className="flex-1 flex flex-col bg-gradient-to-br from-blue-50 via-white to-indigo-50">
        {/* Agent状态面板 */}
        {showAgentPanel && (
          <div className="border-b border-gray-200 bg-white/80 backdrop-blur-sm">
            <div className="p-4">
              <div className="flex items-center gap-2 mb-3">
                <div className="w-3 h-3 bg-green-400 rounded-full animate-pulse"></div>
                <h3 className="font-medium text-gray-800">AI Agent 状态</h3>
              </div>
              <div className="mb-3">
                <div className="text-sm text-gray-500">
                  Agent 状态将在这里显示
                </div>
              </div>
              <ProgressIndicator
                steps={videoGenerationSteps}
                currentStep="novel_creation"
              />
            </div>
          </div>
        )}

        {/* 聊天区域 */}
        <div className="flex-1 flex items-center justify-center">
          <div className="h-full w-full">
            <CopilotChat className="h-full w-full shadow-lg bg-white border border-gray-200 overflow-hidden" />
          </div>
        </div>
      </div>

      {/* 右侧拖拽条 */}
      <div
        className="w-1 cursor-col-resize bg-gray-300 hover:bg-blue-400 transition-colors"
        onMouseDown={handlePreviewMouseDown}
      />

      {/* 右侧文件预览 */}
      <div
        className="bg-white border-l border-gray-300 flex flex-col"
        style={{ width: previewWidth }}
      >
        <div className="px-4 py-3 border-b border-gray-200 bg-gray-50">
          <h2 className="font-semibold text-gray-800">文件预览</h2>
          {selectedFile && (
            <p className="text-xs text-gray-500 mt-1">{selectedFile.name}</p>
          )}
        </div>
        <div className="flex-1 overflow-hidden">
          <FilePreview file={selectedFile} />
        </div>
      </div>
    </div>
  );
}
