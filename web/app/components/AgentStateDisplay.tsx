"use client";

import React from "react";
import {
  CheckCircleIcon,
  ClockIcon,
  ExclamationCircleIcon,
  PlayIcon,
} from "@heroicons/react/24/outline";

interface AgentState {
  message: string;
  detail: string;
}

interface AgentStateDisplayProps {
  state: AgentState;
}

const getStateIcon = (message: string) => {
  if (message.includes("已完成") || message.includes("✅")) {
    return <CheckCircleIcon className="w-5 h-5 text-green-500" />;
  }
  if (
    message.includes("正在执行") ||
    message.includes("🔄") ||
    message.includes("已开始")
  ) {
    return <PlayIcon className="w-5 h-5 text-blue-500 animate-spin" />;
  }
  if (message.includes("失败") || message.includes("❌")) {
    return <ExclamationCircleIcon className="w-5 h-5 text-red-500" />;
  }
  return <ClockIcon className="w-5 h-5 text-yellow-500" />;
};

const getStateColor = (message: string) => {
  if (message.includes("已完成") || message.includes("✅")) {
    return "border-green-200 bg-green-50";
  }
  if (
    message.includes("正在执行") ||
    message.includes("🔄") ||
    message.includes("已开始")
  ) {
    return "border-blue-200 bg-blue-50";
  }
  if (message.includes("失败") || message.includes("❌")) {
    return "border-red-200 bg-red-50";
  }
  return "border-yellow-200 bg-yellow-50";
};

export const AgentStateDisplay: React.FC<AgentStateDisplayProps> = ({
  state,
}) => {
  if (!state.message) return null;

  const formatDetail = (detail: string) => {
    try {
      // 尝试解析JSON并美化显示
      const parsed = JSON.parse(detail);
      return JSON.stringify(parsed, null, 2);
    } catch {
      return detail;
    }
  };

  return (
    <div
      className={`border rounded-lg p-4 my-4 ${getStateColor(state.message)}`}
    >
      <div className="flex items-start gap-3">
        <div className="flex-shrink-0 mt-0.5">
          {getStateIcon(state.message)}
        </div>
        <div className="flex-1 min-w-0">
          <h3 className="text-sm font-medium text-gray-900 mb-2">
            {state.message}
          </h3>
          {state.detail && (
            <div className="text-xs text-gray-600">
              <details className="cursor-pointer">
                <summary className="hover:text-gray-800 font-medium">
                  查看详细信息
                </summary>
                <pre className=" max-h-96 mt-2 whitespace-pre-wrap bg-white p-3 rounded border text-xs overflow-x-auto">
                  {formatDetail(state.detail)}
                </pre>
              </details>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
