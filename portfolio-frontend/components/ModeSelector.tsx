'use client';

import type { InteractionMode } from '@/lib/types';
import { MODE_INFO } from '@/lib/constants';
import clsx from 'clsx';

interface Props {
  currentMode: InteractionMode;
  onModeChange: (mode: InteractionMode) => void;
}

export default function ModeSelector({ currentMode, onModeChange }: Props) {
  return (
    <div className="flex gap-2">
      {Object.entries(MODE_INFO).map(([mode, info]) => (
        <button
          key={mode}
          onClick={() => onModeChange(mode as InteractionMode)}
          className={clsx(
            'px-4 py-2 rounded-lg font-medium transition-all flex items-center gap-2',
            currentMode === mode
              ? 'bg-blue-600 text-white shadow-lg shadow-blue-500/30'
              : 'bg-slate-700 text-slate-300 hover:bg-slate-600'
          )}
        >
          <span>{info.icon}</span>
          <div className="text-left">
            <div className="text-sm font-semibold">{info.label}</div>
            <div className="text-xs opacity-75">{info.description}</div>
          </div>
        </button>
      ))}
    </div>
  );
}
