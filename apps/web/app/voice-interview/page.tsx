'use client';

import { useCallback, useEffect, useMemo, useState } from 'react';
import { useRouter } from 'next/navigation';
import {
  ArrowRight,
  Bot,
  Briefcase,
  CheckCircle2,
  Clock,
  GraduationCap,
  Loader2,
  Mic,
  Sparkles,
  Square,
  Target,
  User,
} from 'lucide-react';
import api from '@/lib/api';
import { Sidebar } from '@/components/layout/Sidebar';
import { VapiAssistant } from '@/components/voice/VapiAssistant';
import { Button } from '@/components/ui/Button';
import { Card, CardContent } from '@/components/ui/Card';
import { cn } from '@/lib/utils';

type TranscriptEntry = {
  role: 'assistant' | 'user';
  content: string;
  timestamp: string;
};

type RoleRecommendation = {
  role: string;
  confidence: number;
  reason: string;
  supporting_skills?: string[];
  missing_skills?: string[];
};

const stages = [
  { label: 'Introduction', icon: User },
  { label: 'Skills', icon: Sparkles },
  { label: 'Experience', icon: Briefcase },
  { label: 'Certifications', icon: CheckCircle2 },
  { label: 'Goals', icon: Target },
  { label: 'Summary', icon: GraduationCap },
];

const formatTime = (seconds: number) => {
  const mins = Math.floor(seconds / 60);
  const secs = seconds % 60;
  return `${mins}:${secs.toString().padStart(2, '0')}`;
};

export default function VoiceInterviewPage() {
  const router = useRouter();
  const [transcript, setTranscript] = useState<TranscriptEntry[]>([]);
  const [isLive, setIsLive] = useState(false);
  const [elapsed, setElapsed] = useState(0);
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [result, setResult] = useState<{
    candidate_profile: Record<string, any>;
    recommended_roles: RoleRecommendation[];
    overall_score: number;
  } | null>(null);
  const [error, setError] = useState('');

  useEffect(() => {
    if (!isLive) return;
    const timer = setInterval(() => setElapsed((value) => value + 1), 1000);
    return () => clearInterval(timer);
  }, [isLive]);

  const currentStage = useMemo(() => {
    const userTurns = transcript.filter((item) => item.role === 'user').length;
    return Math.min(stages.length - 1, Math.floor(userTurns / 2));
  }, [transcript]);

  const addTranscript = useCallback((entry: { role: 'assistant' | 'user'; content: string }) => {
    setTranscript((prev) => {
      const last = prev[prev.length - 1];
      if (last?.role === entry.role && last.content === entry.content) return prev;
      return [...prev, { ...entry, timestamp: new Date().toISOString() }];
    });
  }, []);

  const handleCallStart = useCallback(() => {
    setIsLive(true);
    setError('');
  }, []);

  const handleCallEnd = useCallback(() => {
    setIsLive(false);
  }, []);

  const analyzeInterview = async () => {
    if (transcript.length === 0) {
      setError('Start the Vapi interview first so there is a transcript to analyze.');
      return;
    }

    setIsAnalyzing(true);
    setError('');
    setIsLive(false);

    try {
      const response = await api.post('/api/v1/voice-interviews/analyze', {
        transcript,
        duration_seconds: elapsed,
      });
      setResult(response.data);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Could not analyze the voice interview.');
    } finally {
      setIsAnalyzing(false);
    }
  };

  return (
    <div className="flex h-screen overflow-hidden bg-slate-50 text-slate-900">
      <Sidebar />

      <main className="flex-1 overflow-y-auto">
        <div className="min-h-screen">
          <section className="border-b border-slate-200 bg-white px-8 py-8 lg:px-12">
            <div className="flex flex-col gap-6 lg:flex-row lg:items-center lg:justify-between">
              <div>
                <p className="mb-2 text-xs font-black uppercase tracking-[0.24em] text-primary-600">Voice-First AI Interview</p>
                <h1 className="text-4xl font-black tracking-tight">Speak with your AI career interviewer</h1>
                <p className="mt-3 max-w-2xl text-sm font-semibold leading-relaxed text-slate-500">
                  Answer naturally. The assistant will collect your education, skills, projects, certifications, experience, and career goals before generating role recommendations.
                </p>
              </div>
              <div className="flex items-center gap-3">
                <div className="rounded-2xl border border-slate-100 bg-slate-50 px-5 py-3">
                  <p className="text-[10px] font-black uppercase tracking-widest text-slate-400">Timer</p>
                  <p className="font-mono text-2xl font-black">{formatTime(elapsed)}</p>
                </div>
                <Button
                  variant="outline"
                  className="h-14 rounded-2xl border-red-100 px-6 font-black text-red-600 hover:bg-red-50"
                  onClick={analyzeInterview}
                  disabled={isAnalyzing}
                >
                  <Square size={16} className="mr-2" />
                  End Interview
                </Button>
              </div>
            </div>
          </section>

          <section className="grid gap-6 p-8 lg:grid-cols-[360px_1fr] lg:p-12">
            <div className="space-y-6">
              <Card className="border-none shadow-sm ring-1 ring-slate-100">
                <CardContent className="p-6">
                  <div className="mb-6 flex items-center gap-4">
                    <div className={cn(
                      'flex h-16 w-16 items-center justify-center rounded-3xl text-white shadow-xl',
                      isLive ? 'bg-emerald-600 shadow-emerald-100' : 'bg-primary-600 shadow-primary-100'
                    )}>
                      {isLive ? <Mic size={30} className="animate-pulse" /> : <Bot size={30} />}
                    </div>
                    <div>
                      <p className="text-xs font-black uppercase tracking-widest text-slate-400">Interview Status</p>
                      <p className="text-xl font-black">{isLive ? 'Listening live' : result ? 'Completed' : 'Ready to start'}</p>
                    </div>
                  </div>

                  <VapiAssistant
                    targetRole="Career Discovery Interview"
                    onTranscript={addTranscript}
                    onCallStart={handleCallStart}
                    onCallEnd={handleCallEnd}
                  />

                  <p className="mt-4 text-xs font-semibold leading-relaxed text-slate-400">
                    Configure your Vapi assistant with the career interviewer system prompt. When the call ends, click End Interview to generate the candidate profile.
                  </p>
                </CardContent>
              </Card>

              <Card className="border-none shadow-sm ring-1 ring-slate-100">
                <CardContent className="p-6">
                  <p className="mb-5 text-xs font-black uppercase tracking-widest text-slate-400">Interview Progress</p>
                  <div className="space-y-4">
                    {stages.map((stage, index) => (
                      <div key={stage.label} className="flex items-center gap-3">
                        <div className={cn(
                          'flex h-9 w-9 items-center justify-center rounded-xl',
                          index <= currentStage ? 'bg-primary-600 text-white' : 'bg-slate-100 text-slate-400'
                        )}>
                          <stage.icon size={16} />
                        </div>
                        <span className={cn(
                          'text-sm font-black',
                          index <= currentStage ? 'text-slate-900' : 'text-slate-400'
                        )}>
                          {stage.label}
                        </span>
                      </div>
                    ))}
                  </div>
                </CardContent>
              </Card>
            </div>

            <div className="space-y-6">
              {error && (
                <div className="rounded-2xl border border-red-100 bg-red-50 p-4 text-sm font-bold text-red-600">
                  {error}
                </div>
              )}

              <Card className="border-none shadow-sm ring-1 ring-slate-100">
                <CardContent className="p-0">
                  <div className="border-b border-slate-100 p-6">
                    <p className="text-xs font-black uppercase tracking-widest text-slate-400">Live Transcript</p>
                    <h2 className="mt-1 text-2xl font-black">Candidate conversation</h2>
                  </div>
                  <div className="max-h-[520px] min-h-[420px] space-y-5 overflow-y-auto p-6">
                    {transcript.length === 0 ? (
                      <div className="flex h-80 flex-col items-center justify-center text-center">
                        <div className="mb-5 flex h-20 w-20 items-center justify-center rounded-3xl bg-slate-50 text-slate-300">
                          <Mic size={38} />
                        </div>
                        <p className="text-lg font-black">No transcript yet</p>
                        <p className="mt-2 max-w-sm text-sm font-semibold text-slate-400">
                          Start the Vapi call and speak naturally. Final transcript turns will appear here.
                        </p>
                      </div>
                    ) : (
                      transcript.map((entry, index) => (
                        <div key={`${entry.timestamp}-${index}`} className={cn('flex', entry.role === 'user' ? 'justify-end' : 'justify-start')}>
                          <div className={cn(
                            'max-w-[78%] rounded-3xl p-5 shadow-sm',
                            entry.role === 'user'
                              ? 'rounded-tr-none bg-primary-600 text-white'
                              : 'rounded-tl-none border border-slate-100 bg-white text-slate-800'
                          )}>
                            <p className="text-sm font-semibold leading-relaxed">{entry.content}</p>
                            <p className={cn('mt-3 text-[10px] font-black uppercase tracking-widest opacity-60', entry.role === 'user' ? 'text-white' : 'text-slate-400')}>
                              {entry.role === 'user' ? 'Candidate' : 'AI Interviewer'}
                            </p>
                          </div>
                        </div>
                      ))
                    )}
                  </div>
                </CardContent>
              </Card>

              {isAnalyzing && (
                <Card className="border-none shadow-sm ring-1 ring-primary-100">
                  <CardContent className="flex items-center gap-4 p-6">
                    <Loader2 className="h-8 w-8 animate-spin text-primary-600" />
                    <div>
                      <p className="font-black">Generating candidate profile</p>
                      <p className="text-sm font-semibold text-slate-400">Analyzing transcript and ranking suitable roles...</p>
                    </div>
                  </CardContent>
                </Card>
              )}

              {result && (
                <Card className="border-none shadow-xl shadow-primary-100/50 ring-1 ring-primary-100">
                  <CardContent className="p-8">
                    <div className="mb-8 flex items-center justify-between gap-4">
                      <div>
                        <p className="text-xs font-black uppercase tracking-widest text-primary-600">Dashboard Results</p>
                        <h2 className="mt-1 text-3xl font-black">Recommended roles</h2>
                      </div>
                      <div className="rounded-2xl bg-primary-50 px-5 py-3 text-right">
                        <p className="text-[10px] font-black uppercase tracking-widest text-primary-400">Profile Score</p>
                        <p className="text-2xl font-black text-primary-700">{result.overall_score?.toFixed(1) || '0.0'}%</p>
                      </div>
                    </div>

                    <div className="grid gap-4">
                      {result.recommended_roles.map((role) => (
                        <div key={role.role} className="rounded-2xl border border-slate-100 bg-slate-50 p-5">
                          <div className="mb-3 flex items-center justify-between gap-3">
                            <h3 className="text-lg font-black">{role.role}</h3>
                            <span className="rounded-full bg-white px-3 py-1 text-xs font-black text-primary-700 shadow-sm">
                              {role.confidence}%
                            </span>
                          </div>
                          <p className="text-sm font-semibold leading-relaxed text-slate-500">{role.reason}</p>
                        </div>
                      ))}
                    </div>

                    <div className="mt-8 flex flex-col gap-3 sm:flex-row">
                      <Button className="h-14 rounded-2xl px-8 font-black" onClick={() => router.push('/dashboard')}>
                        View Dashboard
                        <ArrowRight size={18} className="ml-2" />
                      </Button>
                      <Button variant="outline" className="h-14 rounded-2xl px-8 font-black" onClick={() => router.push('/dashboard/analytics')}>
                        Open Analytics
                      </Button>
                    </div>
                  </CardContent>
                </Card>
              )}
            </div>
          </section>
        </div>
      </main>
    </div>
  );
}
