import Link from 'next/link';

export default function Home() {
  return (
    <main className="min-h-screen bg-gradient-to-br from-slate-900 via-slate-800 to-slate-900 text-white">
      <div className="max-w-4xl mx-auto px-6 py-24">
        <div className="text-center mb-16">
          <h1 className="text-5xl font-bold mb-6">
            Portfolio Assistant
          </h1>
          <p className="text-xl text-slate-300 mb-8">
            Intelligent multi-agent system for exploring my work
          </p>
        </div>
        
        <div className="grid md:grid-cols-3 gap-6 mb-12">
          <div className="bg-slate-800/50 backdrop-blur border border-slate-700 rounded-xl p-6">
            <div className="text-3xl mb-3">💼</div>
            <h3 className="text-lg font-semibold mb-2">Recruiter Mode</h3>
            <p className="text-sm text-slate-400">
              Business-focused summaries and impact-driven insights
            </p>
          </div>
          
          <div className="bg-slate-800/50 backdrop-blur border border-slate-700 rounded-xl p-6">
            <div className="text-3xl mb-3">⚙️</div>
            <h3 className="text-lg font-semibold mb-2">Engineer Mode</h3>
            <p className="text-sm text-slate-400">
              Deep technical dives with architecture decisions
            </p>
          </div>
          
          <div className="bg-slate-800/50 backdrop-blur border border-slate-700 rounded-xl p-6">
            <div className="text-3xl mb-3">💬</div>
            <h3 className="text-lg font-semibold mb-2">AMA Mode</h3>
            <p className="text-sm text-slate-400">
              Conversational exploration and exploratory questions
            </p>
          </div>
        </div>
        
        <div className="text-center">
          <Link
            href="/chat"
            className="inline-block px-8 py-4 bg-blue-600 hover:bg-blue-700 rounded-lg font-semibold text-lg transition shadow-lg shadow-blue-500/30"
          >
            Start Exploring →
          </Link>
        </div>
      </div>
    </main>
  );
}
