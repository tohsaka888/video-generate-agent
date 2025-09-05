"use client";

import React from "react";
import { 
  DocumentTextIcon, 
  UserGroupIcon, 
  PhotoIcon, 
  SpeakerWaveIcon, 
  VideoCameraIcon,
  PlayIcon 
} from "@heroicons/react/24/outline";

interface QuickAction {
  id: string;
  title: string;
  description: string;
  icon: React.ReactNode;
  action: string;
  color: string;
}

interface QuickActionsProps {
  onActionClick?: (action: string) => void;
}

const quickActions: QuickAction[] = [
  {
    id: "create_novel",
    title: "创建小说",
    description: "根据基线生成小说内容",
    icon: <DocumentTextIcon className="w-5 h-5" />,
    action: "请根据我提供的基线创建一个1000字的小说",
    color: "bg-blue-50 border-blue-200 text-blue-700 hover:bg-blue-100"
  },
  {
    id: "generate_characters",
    title: "生成角色",
    description: "为小说创建角色设定",
    icon: <UserGroupIcon className="w-5 h-5" />,
    action: "请为当前小说生成角色设定",
    color: "bg-purple-50 border-purple-200 text-purple-700 hover:bg-purple-100"
  },
  {
    id: "create_scenes",
    title: "分镜场景",
    description: "将小说分解为场景",
    icon: <PhotoIcon className="w-5 h-5" />,
    action: "请为小说生成分镜场景",
    color: "bg-green-50 border-green-200 text-green-700 hover:bg-green-100"
  },
  {
    id: "generate_audio",
    title: "生成音频",
    description: "为场景生成配音和字幕",
    icon: <SpeakerWaveIcon className="w-5 h-5" />,
    action: "请为所有场景生成音频和字幕",
    color: "bg-yellow-50 border-yellow-200 text-yellow-700 hover:bg-yellow-100"
  },
  {
    id: "compose_video",
    title: "合成视频",
    description: "将所有元素合成为视频",
    icon: <VideoCameraIcon className="w-5 h-5" />,
    action: "请开始视频合成",
    color: "bg-red-50 border-red-200 text-red-700 hover:bg-red-100"
  },
  {
    id: "full_pipeline",
    title: "一键生成",
    description: "执行完整的视频生成流程",
    icon: <PlayIcon className="w-5 h-5" />,
    action: "请执行完整的视频生成流程，包括小说创作、角色设定、场景生成、图片生成、音频合成和视频合成",
    color: "bg-indigo-50 border-indigo-200 text-indigo-700 hover:bg-indigo-100"
  }
];

export const QuickActions: React.FC<QuickActionsProps> = ({ onActionClick }) => {
  return (
    <div className="bg-white rounded-lg border border-gray-200 p-4 mb-4">
      <h3 className="text-sm font-medium text-gray-900 mb-3">快速操作</h3>
      <div className="grid grid-cols-2 gap-2">
        {quickActions.map((action) => (
          <button
            key={action.id}
            onClick={() => onActionClick?.(action.action)}
            className={`
              p-3 rounded-lg border-2 text-left transition-all duration-200 hover:scale-105
              ${action.color}
            `}
          >
            <div className="flex items-start gap-2">
              <div className="flex-shrink-0 mt-0.5">
                {action.icon}
              </div>
              <div className="flex-1 min-w-0">
                <div className="text-xs font-medium mb-1">{action.title}</div>
                <div className="text-xs opacity-75 line-clamp-2">
                  {action.description}
                </div>
              </div>
            </div>
          </button>
        ))}
      </div>
    </div>
  );
};
