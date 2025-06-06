"use client";

import React from "react";
import { IconRocket, IconFileText, IconCheck, IconAsset, IconBrain, IconSparkles, IconInfoCircle, IconExclamationCircle } from "@tabler/icons-react";
import { cn } from "@/lib/utils";

type LogType = 'header' | 'item' | 'sub-item' | 'code' | 'success' | 'error' | 'info';

interface LogLine {
  type: LogType;
  content: string;
  icon?: React.ReactNode;
}

// More specific parsing to create a structured log view
const parseLog = (log: string): LogLine => {
    const trimmed = log.trim();

    if (trimmed.startsWith('🚀')) return { type: 'header', content: trimmed.replace('🚀', '').trim(), icon: <IconRocket size={18} /> };
    if (trimmed.startsWith('✅')) return { type: 'success', content: trimmed.replace('✅', '').trim(), icon: <IconCheck size={16} className="text-green-400" /> };
    if (trimmed.startsWith('📦')) return { type: 'header', content: trimmed.replace('📦', '').trim(), icon: <IconAsset size={18} /> };
    if (trimmed.startsWith('🧠')) return { type: 'header', content: trimmed.replace('🧠', '').trim(), icon: <IconBrain size={18} /> };
    if (trimmed.startsWith('✨')) return { type: 'success', content: trimmed.replace('✨', '').trim(), icon: <IconSparkles size={16} className="text-yellow-400" /> };
    if (trimmed.startsWith('📄')) return { type: 'item', content: trimmed.replace('📄', '').trim(), icon: <IconFileText size={16} className="text-neutral-400" /> };
    if (trimmed.startsWith('ERROR:')) return { type: 'error', content: trimmed.replace('ERROR:', '').trim(), icon: <IconExclamationCircle size={16} className="text-red-400" /> };
    if (trimmed.startsWith('- ')) return { type: 'sub-item', content: trimmed.replace('- ', '').trim() };
    if (trimmed.startsWith('> ')) return { type: 'code', content: trimmed.substring(2) };

    return { type: 'info', content: trimmed, icon: <IconInfoCircle size={16} className="text-blue-400" /> };
};

const LogLineView = ({ line }: { line: LogLine }) => {
  const baseClasses = "flex items-start gap-3";
  switch(line.type) {
    case 'header':
      return <div className="text-sm font-medium text-neutral-200 mt-4 mb-2 flex items-center gap-2">{line.icon}{line.content}</div>;
    case 'item':
      return <div className={cn(baseClasses, "text-xs text-neutral-300")}>{line.icon}{line.content}</div>
    case 'sub-item':
      return <div className={cn(baseClasses, "text-xs text-neutral-400 ml-6")}>- {line.content}</div>
    case 'success':
         return <div className={cn(baseClasses, "text-xs text-green-400")}>{line.icon}{line.content}</div>
    case 'error':
        return <div className={cn(baseClasses, "text-xs text-red-400")}>{line.icon}{line.content}</div>
    case 'info':
        return <div className={cn(baseClasses, "text-xs text-blue-400")}>{line.icon}{line.content}</div>
    case 'code':
        return <pre className="text-xs text-neutral-500 whitespace-pre-wrap font-mono pl-4 bg-neutral-900 p-2 rounded-md border border-neutral-700/50">{line.content}</pre>
    default:
      return <div className="text-xs text-neutral-400">{line.content}</div>
  }
}


export const LiveLogView = ({ logs, isActive }: { logs: string[], isActive?: boolean }) => {
  const logContainerRef = React.useRef<HTMLDivElement>(null);
  const [showEllipsis, setShowEllipsis] = React.useState(false);
  const lastLogTime = React.useRef(Date.now());

  React.useEffect(() => {
    if (logContainerRef.current) {
      logContainerRef.current.scrollTop = logContainerRef.current.scrollHeight;
    }
    lastLogTime.current = Date.now();
    setShowEllipsis(false);
    if (isActive) {
      // If no new log in 1s, show ellipsis
      const timeout = setTimeout(() => setShowEllipsis(true), 1000);
      return () => clearTimeout(timeout);
    }
  }, [logs, isActive]);

  const parsedLogs = React.useMemo(() => {
    const allLogs: LogLine[] = [];
    for (const log of logs) {
      log.split('\n').forEach(line => {
        if(line.trim()) allLogs.push(parseLog(line));
      });
    }
    return allLogs;
  }, [logs]);

  return (
    <div className="text-xs text-neutral-400 font-mono bg-neutral-900/50 p-3 rounded-lg border border-neutral-700 flex-1 overflow-y-auto" ref={logContainerRef}>
      <div className="space-y-2">
        {parsedLogs.map((line, index) => (
          <LogLineView key={index} line={line} />
        ))}
        {isActive && showEllipsis && (
          <div className="flex items-center gap-2 mt-2">
            <span className="animate-pulse text-blue-400">•</span>
            <span className="animate-bounce text-blue-400">.</span>
            <span className="animate-bounce text-blue-400" style={{ animationDelay: '0.2s' }}>.</span>
            <span className="animate-bounce text-blue-400" style={{ animationDelay: '0.4s' }}>.</span>
          </div>
        )}
      </div>
    </div>
  );
}; 