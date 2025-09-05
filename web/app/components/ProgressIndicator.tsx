"use client";

import React from "react";

interface ProgressStep {
  id: string;
  title: string;
  status: "pending" | "running" | "completed" | "failed";
  description?: string;
}

interface ProgressIndicatorProps {
  steps: ProgressStep[];
  currentStep?: string;
}

const statusColors = {
  pending: "bg-gray-200 text-gray-600",
  running: "bg-blue-500 text-white animate-pulse",
  completed: "bg-green-500 text-white",
  failed: "bg-red-500 text-white",
};

const statusIcons = {
  pending: "⏳",
  running: "🔄",
  completed: "✅",
  failed: "❌",
};

export const ProgressIndicator: React.FC<ProgressIndicatorProps> = ({ 
  steps, 
  currentStep 
}) => {
  const getStepIndex = (stepId: string) => steps.findIndex(step => step.id === stepId);
  const currentIndex = currentStep ? getStepIndex(currentStep) : -1;

  return (
    <div className="bg-white rounded-lg border border-gray-200 p-4 mb-4">
      <h3 className="text-sm font-medium text-gray-900 mb-3">生成进度</h3>
      <div className="space-y-3">
        {steps.map((step, index) => {
          const isActive = step.id === currentStep;
          const isCompleted = step.status === "completed";
          const isFailed = step.status === "failed";
          const isRunning = step.status === "running";

          return (
            <div key={step.id} className="flex items-start gap-3">
              {/* 步骤编号/状态图标 */}
              <div 
                className={`
                  flex-shrink-0 w-6 h-6 rounded-full flex items-center justify-center text-xs font-medium
                  ${statusColors[step.status]}
                `}
              >
                {isRunning || isCompleted || isFailed ? (
                  <span className="text-xs">{statusIcons[step.status]}</span>
                ) : (
                  <span>{index + 1}</span>
                )}
              </div>

              {/* 连接线 */}
              {index < steps.length - 1 && (
                <div 
                  className={`
                    absolute left-[11px] mt-6 w-0.5 h-6
                    ${isCompleted ? "bg-green-500" : "bg-gray-200"}
                  `}
                  style={{ marginLeft: "11px" }}
                />
              )}

              {/* 步骤内容 */}
              <div className="flex-1 min-w-0">
                <h4 className={`
                  text-sm font-medium
                  ${isActive ? "text-blue-600" : isCompleted ? "text-green-600" : isFailed ? "text-red-600" : "text-gray-600"}
                `}>
                  {step.title}
                </h4>
                {step.description && (
                  <p className="text-xs text-gray-500 mt-1">
                    {step.description}
                  </p>
                )}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};

// 预定义的视频生成步骤
export const videoGenerationSteps: ProgressStep[] = [
  {
    id: "novel_creation",
    title: "小说创作",
    status: "pending",
    description: "根据用户提供的基线创作小说内容"
  },
  {
    id: "character_settings",
    title: "角色设定",
    status: "pending", 
    description: "生成小说中的角色设定和人物描述"
  },
  {
    id: "scene_generation",
    title: "场景分镜",
    status: "pending",
    description: "将小说内容分解为多个场景和分镜"
  },
  {
    id: "image_generation",
    title: "图片生成",
    status: "pending",
    description: "为每个场景生成对应的图片"
  },
  {
    id: "audio_generation", 
    title: "音频合成",
    status: "pending",
    description: "生成旁白音频和字幕文件"
  },
  {
    id: "video_composition",
    title: "视频合成",
    status: "pending",
    description: "将图片、音频和字幕合成为最终视频"
  }
];
