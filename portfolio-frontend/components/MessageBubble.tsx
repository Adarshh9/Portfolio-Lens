'use client';

import type { Message } from '@/lib/types';
import clsx from 'clsx';

interface Props {
  message: Message;
}

export default function MessageBubble({ message }: Props) {
  const isUser = message.role === 'user';
  
  return (
    <div className={clsx('flex', isUser ? 'justify-end' : 'justify-start')}>
      <div
        className={clsx(
          'max-w-2xl px-4 py-3 rounded-lg',
          isUser
            ? 'bg-blue-600 text-white'
            : 'bg-slate-700 text-slate-100'
        )}
      >
        <div className="whitespace-pre-wrap">{message.content}</div>
        
        {message.judgeScore && !isUser && (
          <div className="mt-3 pt-3 border-t border-slate-600">
            <div className="text-xs opacity-75 space-y-1">
              <div>Grounding: {message.judgeScore.grounding_score}/5</div>
              <div>Consistency: {message.judgeScore.consistency_score}/5</div>
              <div>Depth: {message.judgeScore.depth_score}/5</div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
