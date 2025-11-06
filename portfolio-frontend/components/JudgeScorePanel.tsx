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
    if (s >= 8) return 'text-green-400';
    if (s >= 6) return 'text-yellow-400';
    if (s >= 4) return 'text-orange-400';
    return 'text-red-400';
  };
  
  const getScoreBarColor = (s: number) => {
    if (s >= 8) return 'bg-green-500';
    if (s >= 6) return 'bg-yellow-500';
    if (s >= 4) return 'bg-orange-500';
    return 'bg-red-500';
  };
  
  const getScoreLabel = (s: number) => {
    if (s >= 9) return 'Excellent';
    if (s >= 7) return 'Good';
    if (s >= 5) return 'Acceptable';
    if (s >= 3) return 'Poor';
    return 'Very Poor';
  };
  
  // Get scores - handle both old (0-5) and new (0-10) formats
  const groundingScore = (score.grounding_score || 0); // Convert if needed
  const consistencyScore = (score.consistency_score || 0);
  const depthScore = (score.depth_score || 0) ;
  const specificityScore = (score.specificity_score || 0);
  // const averageScore = (score.depth_score || 0) * 2;

  const averageScore = (groundingScore + consistencyScore + depthScore + specificityScore) / 4;
  
  return (
    <div className="w-96 border-l border-slate-700 bg-slate-800/50 p-6 overflow-y-auto">
      <h3 className="text-lg font-semibold text-white mb-2">
        Response Quality Scores
      </h3>
      <p className="text-xs text-slate-400 mb-4">
        0-10 scale (7+ is professional quality)
      </p>
      
      {/* Average Score */}
      <div className="mb-6 p-4 bg-slate-700/50 rounded-lg">
        <div className="flex justify-between items-center mb-2">
          <span className="text-sm font-semibold text-slate-300">Overall</span>
          <span className={`text-lg font-bold ${getScoreColor(averageScore)}`}>
            {averageScore.toFixed(1)}/10
          </span>
        </div>
        <div className="text-xs text-slate-400">
          {getScoreLabel(averageScore)}
        </div>
      </div>
      
      {/* Individual Scores */}
      <div className="space-y-4">
        {/* Grounding */}
        <div>
          <div className="flex justify-between items-center mb-2">
            <span className="text-sm text-slate-300">
              📌 Grounding
              <span className="text-xs text-slate-500 block">Citations & Evidence</span>
            </span>
            <span className={`text-sm font-semibold ${getScoreColor(groundingScore)}`}>
              {groundingScore.toFixed(1)}/10
            </span>
          </div>
          <div className="w-full bg-slate-700 rounded-full h-2 overflow-hidden">
            <div
              className={`h-full ${getScoreBarColor(groundingScore)} transition-all`}
              style={{ width: `${(groundingScore / 10) * 100}%` }}
            />
          </div>
        </div>
        
        {/* Consistency */}
        <div>
          <div className="flex justify-between items-center mb-2">
            <span className="text-sm text-slate-300">
              🔗 Consistency
              <span className="text-xs text-slate-500 block">Cross-project alignment</span>
            </span>
            <span className={`text-sm font-semibold ${getScoreColor(consistencyScore)}`}>
              {consistencyScore.toFixed(1)}/10
            </span>
          </div>
          <div className="w-full bg-slate-700 rounded-full h-2 overflow-hidden">
            <div
              className={`h-full ${getScoreBarColor(consistencyScore)} transition-all`}
              style={{ width: `${(consistencyScore / 10) * 100}%` }}
            />
          </div>
        </div>
        
        {/* Depth */}
        <div>
          <div className="flex justify-between items-center mb-2">
            <span className="text-sm text-slate-300">
              🧠 Depth
              <span className="text-xs text-slate-500 block">Technical sophistication</span>
            </span>
            <span className={`text-sm font-semibold ${getScoreColor(depthScore)}`}>
              {depthScore.toFixed(1)}/10
            </span>
          </div>
          <div className="w-full bg-slate-700 rounded-full h-2 overflow-hidden">
            <div
              className={`h-full ${getScoreBarColor(depthScore)} transition-all`}
              style={{ width: `${(depthScore / 10) * 100}%` }}
            />
          </div>
        </div>

      {/* Specificity */}
      <div>
        <div className="flex justify-between items-center mb-2">
          <span className="text-sm text-slate-300">
            📌 Specificity
            <span className="text-xs text-slate-500 block">Precision & Detail</span>
          </span>
          <span className={`text-sm font-semibold ${getScoreColor(specificityScore)}`}>
            {specificityScore.toFixed(1)}/10
          </span>
        </div>
        <div className="w-full bg-slate-700 rounded-full h-2 overflow-hidden">
          <div
            className={`h-full ${getScoreBarColor(specificityScore)} transition-all`}
            style={{ width: `${(specificityScore / 10) * 100}%` }}
          />
        </div>
      </div>
      </div>

      {/* Feedback */}
      {score.feedback && score.feedback.length > 0 && (
        <div className="mt-6 pt-4 border-t border-slate-700">
          <p className="text-xs font-semibold text-slate-400 mb-2">Feedback:</p>
          <ul className="text-xs text-slate-400 space-y-1">
            {score.feedback.map((fb, i) => (
              <li key={i}>• {fb}</li>
            ))}
          </ul>
        </div>
      )}
      
      {/* Sources */}
      {score.citations_used && score.citations_used.length > 0 && (
        <div className="mt-4 pt-4 border-t border-slate-700">
          <p className="text-xs font-semibold text-slate-400 mb-2">Sources:</p>
          <div className="flex flex-wrap gap-1">
            {score.citations_used.map((src, i) => (
              <span key={i} className="text-xs bg-slate-700 text-slate-300 px-2 py-1 rounded">
                {src}
              </span>
            ))}
          </div>
        </div>
      )}
      
      {/* Quality Indicator */}
      <div className="mt-6 pt-4 border-t border-slate-700">
        <div className="text-xs text-slate-400">
          {averageScore >= 7 ? (
            <span className="text-green-400">✓ Professional quality</span>
          ) : averageScore >= 5 ? (
            <span className="text-yellow-400">⚠ Could be improved</span>
          ) : (
            <span className="text-red-400">✗ Needs revision</span>
          )}
        </div>
      </div>
    </div>
  );
}
