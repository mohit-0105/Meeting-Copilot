import React from "react";

export default function MeetingCopilot() {
  return (
    <div className="flex h-screen w-full bg-background font-sans text-foreground">
      {/* 1. Left Sidebar (Navigation) */}
      <aside className="w-64 bg-sidebar text-sidebar-fg flex flex-col justify-between shrink-0 transition-all">
        <div className="p-6">
          <div className="flex items-center gap-3 mb-10">
            <div className="w-8 h-8 rounded bg-accent flex items-center justify-center text-white font-bold text-lg shadow-md">
              M
            </div>
            <h1 className="text-xl font-semibold tracking-tight text-white">Meeting Copilot</h1>
          </div>

          <nav className="space-y-2">
            <NavItem label="Dashboard" icon="📊" />
            <NavItem label="Meetings" icon="📅" active />
            <div className="ml-6 mt-2 space-y-1 border-l border-slate-600 pl-4 py-1">
              <SubNavItem label="Strategy Sync" active />
              <SubNavItem label="Weekly Review" />
              <SubNavItem label="Project Alpha" />
            </div>
            <NavItem label="Calendar" icon="📆" />
            <NavItem label="Recordings" icon="📼" />
            <NavItem label="Settings" icon="⚙️" />
          </nav>
        </div>
        
        <div className="p-6 border-t border-slate-700/50">
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 rounded-full bg-slate-600 flex-shrink-0" />
            <div className="text-sm">
              <p className="font-medium text-white">Alex Manager</p>
              <p className="text-slate-400 text-xs">alex@nexus.ai</p>
            </div>
          </div>
        </div>
      </aside>

      {/* 2. Center Panel (Live Transcript) */}
      <main className="flex-1 flex flex-col bg-background min-w-0 border-r border-border-subtle shadow-sm z-10">
        {/* Header */}
        <header className="h-20 border-b border-border-subtle bg-panel flex items-center justify-between px-8 shrink-0 shadow-sm">
          <div>
            <h2 className="text-2xl font-semibold text-slate-800">Weekly Strategy Sync</h2>
            <p className="text-sm text-slate-500 mt-1 flex items-center gap-2">
              <span className="w-2 h-2 rounded-full bg-red-500 animate-pulse" />
              Recording • 00:32:45
            </p>
          </div>
          <div className="flex gap-2">
            <button className="px-4 py-2 text-sm font-medium text-slate-700 bg-white border border-slate-300 rounded-md hover:bg-slate-50 transition-colors">
              Share
            </button>
            <button className="px-4 py-2 text-sm font-medium text-white bg-accent rounded-md shadow-sm hover:bg-blue-700 transition-colors">
              End Meeting
            </button>
          </div>
        </header>

        {/* Transcript Feed */}
        <div className="flex-1 overflow-y-auto p-8 space-y-6">
          <TranscriptLine 
            speaker="Sarah K." time="00:03" color="text-blue-600"
            text="Okay everyone, welcome to the weekly sync. Let's start with the Q4 goals. Dave, can you update us on the API integration?"
          />
          <TranscriptLine 
            speaker="Dave R." time="00:15" color="text-emerald-600"
            text="We need to address the supply chain bottlenecks for Project Gamma. It's delaying our initial rollout plan significantly."
          />
          <TranscriptLine 
            speaker="Emily W." time="00:29" color="text-purple-600"
            text="That's correct. Logistics is facing severe challenges with international shipping. We might need a contingency plan."
          />
           <TranscriptLine 
            speaker="Sarah K." time="00:40" color="text-blue-600"
            text="Agreed. I will schedule a deep dive on logistics tomorrow at 2 PM to resolve this."
          />
        </div>
        
        {/* Input area (simulation of speaking) */}
        <div className="p-4 bg-panel border-t border-border-subtle">
           <div className="w-full flex items-center justify-center p-3 rounded-lg border border-slate-200 bg-slate-50 text-slate-500 text-sm">
              Listening to microphone...
           </div>
        </div>
      </main>

      {/* 3. Right Panel (AI Copilot Insights) */}
      <aside className="w-80 bg-slate-50 flex flex-col shrink-0">
        <div className="h-20 border-b border-border-subtle bg-slate-50 flex items-center px-6 shrink-0">
          <h3 className="text-lg font-semibold text-slate-800 flex items-center gap-2">
            ✨ AI Copilot
          </h3>
        </div>

        <div className="flex-1 overflow-y-auto p-6 space-y-8">
          {/* Summary Section */}
          <section>
            <h4 className="text-xs font-bold text-slate-500 uppercase tracking-wider mb-3">Live Summary</h4>
            <ul className="space-y-2 text-sm text-slate-700 list-disc list-inside">
              <li>Project Gamma timeline is delayed.</li>
              <li>Supply chain bottlenecks identified.</li>
              <li>Logistics deep dive required.</li>
            </ul>
          </section>

          <hr className="border-border-subtle" />

          {/* Action Items Section */}
          <section>
            <h4 className="text-xs font-bold text-slate-500 uppercase tracking-wider mb-3">Action Items</h4>
            <div className="space-y-3">
              <ActionItem text="Schedule logistics deep dive" owner="Sarah K." date="Tomorrow 2 PM" />
              <ActionItem text="Draft contingency plan for Gamma" owner="Dave R." date="Oct 18" />
              <ActionItem text="Finalize Q4 marketing budget" owner="Emily W." date="Oct 20" />
            </div>
          </section>
        </div>

        {/* Copilot Chat Input */}
        <div className="p-4 bg-slate-50 border-t border-border-subtle">
          <div className="relative">
            <input 
              type="text" 
              placeholder="Ask Copilot..." 
              className="w-full pl-4 pr-10 py-3 text-sm border border-slate-300 rounded-lg bg-white shadow-sm focus:outline-none focus:border-accent focus:ring-1 focus:ring-accent transition-all"
            />
            <button className="absolute right-3 top-3 text-slate-400 hover:text-accent transition-colors">
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M22 2L11 13"/><path d="M22 2L15 22L11 13L2 9L22 2Z"/></svg>
            </button>
          </div>
        </div>
      </aside>
    </div>
  );
}

// Reusable micro-components for the mockup
function NavItem({ label, icon, active = false }: { label: string, icon: string, active?: boolean }) {
  return (
    <a href="#" className={`flex items-center gap-3 px-3 py-2 rounded-md transition-colors ${active ? 'bg-slate-700/60 text-white font-medium' : 'text-slate-300 hover:bg-slate-700/40 hover:text-white'}`}>
      <span>{icon}</span>
      <span className="text-sm">{label}</span>
    </a>
  );
}

function SubNavItem({ label, active = false }: { label: string, active?: boolean }) {
  return (
    <a href="#" className={`block text-xs py-1 transition-colors ${active ? 'text-blue-400 font-medium' : 'text-slate-400 hover:text-slate-200'}`}>
      {label}
    </a>
  );
}

function TranscriptLine({ speaker, time, text, color }: { speaker: string, time: string, text: string, color: string }) {
  return (
    <div className="flex gap-4 group">
      <div className="w-12 text-xs text-slate-400 pt-1 shrink-0">{time}</div>
      <div>
        <span className={`font-semibold text-sm ${color}`}>{speaker}</span>
        <p className="text-slate-700 mt-1 leading-relaxed text-[15px]">{text}</p>
      </div>
    </div>
  );
}

function ActionItem({ text, owner, date }: { text: string, owner: string, date: string }) {
  return (
    <div className="flex gap-3 bg-white p-3 rounded-lg border border-slate-200 shadow-sm hover:shadow-md transition-shadow">
      <input type="checkbox" className="mt-1 w-4 h-4 rounded border-slate-300 text-accent focus:ring-accent" />
      <div>
        <p className="text-sm font-medium text-slate-800">{text}</p>
        <div className="flex items-center gap-4 mt-2 text-xs text-slate-500">
          <span className="flex items-center gap-1"><span className="w-4 h-4 rounded-full bg-slate-200 flex items-center justify-center text-[8px]">👤</span> {owner}</span>
          <span className="flex items-center gap-1">📅 {date}</span>
        </div>
      </div>
    </div>
  );
}
