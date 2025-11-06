'use client';

import type { JudgeScore, InteractionMode } from '@/lib/types';

interface Props {
  score: JudgeScore | null;
  mode: InteractionMode;
}

export default function JudgeScorePanel({ score, mode }: Props) {
  if (!score) {
    return (
      <div className="w-80 border-l border-slate-700 bg-slate-800/50 p-6">
        <h3 className="text-lg font-semibold text-white mb-4">
          Response Quality
        </h3>
        <p className="text-slate-400 text-sm">
          Scores will appear after the first response
        </p>
      </div>
    );
  }
  
  const getScoreColor = (s: number) => {
    if (s >= 4) return 'text-green-400';
    if (s >= 3) return 'text-yellow-400';
    return 'text-red-400';
  };
  
  const getScoreBarColor = (s: number) => {
    if (s >= 4) return 'bg-green-500';
    if (s >= 3) return 'bg-yellow-500';
    return 'bg-red-500';
  };
  
  return (
    <div className="w-80 border-l border-slate-700 bg-slate-800/50 p-6 overflow-y-auto">
      <h3 className="text-lg font-semibold text-white mb-4">
        Response Quality
      </h3>
      
      <div className="space-y-4">
        {/* Grounding */}
        <div>
          <div className="flex justify-between items-center mb-2">
            <span className="text-sm text-slate-300">Grounding</span>
            <span className={`text-sm font-semibold ${getScoreColor(score.grounding_score)}`}>
              {score.grounding_score}/5
            </span>
          </div>
          <div className="w-full bg-slate-700 rounded-full h-2 overflow-hidden">
            <div
              className={`h-full ${getScoreBarColor(score.grounding_score)} transition-all`}
              style={{ width: `${(score.grounding_score / 5) * 100}%` }}
            />
          </div>
        </div>
        
        {/* Consistency */}
        <div>
          <div className="flex justify-between items-center mb-2">
            <span className="text-sm text-slate-300">Consistency</span>
            <span className={`text-sm font-semibold ${getScoreColor(score.consistency_score)}`}>
              {score.consistency_score}/5
            </span>
          </div>
          <div className="w-full bg-slate-700 rounded-full h-2 overflow-hidden">
            <div
              className={`h-full ${getScoreBarColor(score.consistency_score)} transition-all`}
              style={{ width: `${(score.consistency_score / 5) * 100}%` }}
            />
          </div>
        </div>
        
        {/* Depth */}
        <div>
          <div className="flex justify-between items-center mb-2">
            <span className="text-sm text-slate-300">Depth</span>
            <span className={`text-sm font-semibold ${getScoreColor(score.depth_score)}`}>
              {score.depth_score}/5
            </span>
          </div>
          <div className="w-full bg-slate-700 rounded-full h-2 overflow-hidden">
            <div
              className={`h-full ${getScoreBarColor(score.depth_score)} transition-all`}
              style={{ width: `${(score.depth_score / 5) * 100}%` }}
            />
          </div>
        </div>
      </div>
    </div>
  );
}
