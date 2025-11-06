'use client';

import { useState, useRef, useEffect } from 'react';
import { nanoid } from 'nanoid';
import ModeSelector from './ModeSelector';
import MessageBubble from './MessageBubble';
import JudgeScorePanel from './JudgeScorePanel';
import { sendChatMessage } from '@/lib/api';
import type { Message, InteractionMode, JudgeScore } from '@/lib/types';

const STORAGE_KEY = 'portfolio_chat_history';
const MODE_STORAGE_KEY = 'portfolio_chat_mode';

export default function ChatInterface() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState('');
  const [mode, setMode] = useState<InteractionMode>('ama');
  const [isLoading, setIsLoading] = useState(false);
  const [latestJudgeScore, setLatestJudgeScore] = useState<JudgeScore | null>(null);
  const [error, setError] = useState<string | null>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  
  // Load from localStorage on mount
  useEffect(() => {
    try {
      const savedMessages = localStorage.getItem(STORAGE_KEY);
      const savedMode = localStorage.getItem(MODE_STORAGE_KEY);
      
      if (savedMessages) {
        const parsed = JSON.parse(savedMessages);
        setMessages(parsed);
        console.log(`✓ Loaded ${parsed.length} messages from history`);
      }
      
      if (savedMode) {
        setMode(savedMode as InteractionMode);
        console.log(`✓ Loaded mode: ${savedMode}`);
      }
    } catch (err) {
      console.error('Error loading from localStorage:', err);
    }
  }, []);
  
  // Save messages to localStorage whenever they change
  useEffect(() => {
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(messages));
    } catch (err) {
      console.error('Error saving messages to localStorage:', err);
    }
  }, [messages]);
  
  // Save mode to localStorage whenever it changes
  useEffect(() => {
    try {
      localStorage.setItem(MODE_STORAGE_KEY, mode);
    } catch (err) {
      console.error('Error saving mode to localStorage:', err);
    }
  }, [mode]);
  
  // Auto-scroll to latest message
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);
  
  const handleClearHistory = () => {
    if (confirm('Clear all chat history? This cannot be undone.')) {
      setMessages([]);
      setLatestJudgeScore(null);
      localStorage.removeItem(STORAGE_KEY);
      console.log('✓ Chat history cleared');
    }
  };
  
  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    
    if (!input.trim() || isLoading) return;
    
    setError(null);
    
    // Add user message
    const userMessage: Message = {
      id: nanoid(),
      role: 'user',
      content: input,
      mode,
      timestamp: new Date()
    };
    
    setMessages(prev => [...prev, userMessage]);
    setInput('');
    setIsLoading(true);
    
    try {
      const response = await sendChatMessage({
        message: input,
        mode
      });
      
      const assistantMessage: Message = {
        id: nanoid(),
        role: 'assistant',
        content: response.response,
        mode: response.mode,
        judgeScore: response.judge_score || undefined,
        timestamp: new Date()
      };
      
      setMessages(prev => [...prev, assistantMessage]);
      
      if (response.judge_score) {
        setLatestJudgeScore(response.judge_score);
      }
      
    } catch (err) {
      console.error('Chat error:', err);
      setError('Failed to get response. Please try again.');
      
      const errorMessage: Message = {
        id: nanoid(),
        role: 'assistant',
        content: '❌ Sorry, I encountered an error. Please try again.',
        timestamp: new Date()
      };
      
      setMessages(prev => [...prev, errorMessage]);
    } finally {
      setIsLoading(false);
    }
  };
  
  return (
    <div className="flex h-screen bg-gradient-to-br from-slate-900 via-slate-800 to-slate-900">
      {/* Main Chat Area */}
      <div className="flex-1 flex flex-col">
        {/* Header */}
        <div className="bg-slate-800/80 backdrop-blur border-b border-slate-700 p-4">
          <div className="max-w-4xl mx-auto">
            <div className="flex justify-between items-center mb-3">
              <h1 className="text-2xl font-bold text-white">
                Portfolio Assistant
              </h1>
              <button
                onClick={handleClearHistory}
                className="px-3 py-1 text-xs bg-red-900/50 hover:bg-red-800/50 text-red-200 rounded transition"
              >
                Clear History
              </button>
            </div>
            <ModeSelector currentMode={mode} onModeChange={setMode} />
          </div>
        </div>
        
        {/* Messages */}
        <div className="flex-1 overflow-y-auto p-4">
          <div className="max-w-4xl mx-auto space-y-4">
            {messages.length === 0 && (
              <div className="text-center py-12">
                <div className="text-slate-400 mb-4">
                  <h2 className="text-xl font-semibold mb-2">Welcome!</h2>
                  <p>Ask me about my projects, experience, or technical decisions.</p>
                  <p className="text-xs mt-2 opacity-75">💾 Your chat history is saved automatically</p>
                </div>
              </div>
            )}
            
            {messages.map(message => (
              <MessageBubble key={message.id} message={message} />
            ))}
            
            {isLoading && (
              <div className="flex justify-start">
                <div className="bg-slate-700 rounded-lg px-4 py-3">
                  <div className="flex space-x-2">
                    <div className="w-2 h-2 bg-slate-400 rounded-full animate-bounce" />
                    <div className="w-2 h-2 bg-slate-400 rounded-full animate-bounce" style={{ animationDelay: '150ms' }} />
                    <div className="w-2 h-2 bg-slate-400 rounded-full animate-bounce" style={{ animationDelay: '300ms' }} />
                  </div>
                </div>
              </div>
            )}
            
            {error && (
              <div className="bg-red-900/50 border border-red-700 text-red-200 rounded-lg px-4 py-3">
                {error}
              </div>
            )}
            
            <div ref={messagesEndRef} />
          </div>
        </div>
        
        {/* Input */}
        <div className="border-t border-slate-700 bg-slate-800/80 backdrop-blur p-4">
          <form onSubmit={handleSubmit} className="max-w-4xl mx-auto flex gap-2">
            <input
              type="text"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder="Ask about my work..."
              className="flex-1 px-4 py-3 bg-slate-700 text-white placeholder-slate-400 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
              disabled={isLoading}
            />
            <button
              type="submit"
              disabled={isLoading || !input.trim()}
              className="px-6 py-3 bg-blue-600 hover:bg-blue-700 disabled:bg-slate-600 disabled:cursor-not-allowed text-white rounded-lg font-medium transition"
            >
              Send
            </button>
          </form>
        </div>
      </div>
      
      {/* Judge Score Panel */}
      {mode !== 'recruiter' && (
        <JudgeScorePanel score={latestJudgeScore} mode={mode} />
      )}
    </div>
  );
}
