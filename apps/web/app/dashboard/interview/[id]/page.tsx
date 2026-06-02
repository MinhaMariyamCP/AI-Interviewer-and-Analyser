'use client';

import { useState, useEffect, Suspense } from 'react';
import { useParams, useRouter } from 'next/navigation';
import { 
  ArrowLeft, 
  Download, 
  Bot, 
  User, 
  Award, 
  Calendar,
  MessageSquare,
  Clock,
  Loader2,
  ChevronRight,
  TrendingUp,
  Target,
  Brain
} from 'lucide-react';
import api from '@/lib/api';
import { Sidebar } from '@/components/layout/Sidebar';
import { Button } from '@/components/ui/Button';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/Card';
import { cn } from '@/lib/utils';

function InterviewDetailContent() {
  const { id } = useParams();
  const router = useRouter();
  const [data, setData] = useState<any>(null);
  const [analytics, setAnalytics] = useState<any>(null);
  const [isLoading, setIsLoading] = useState(true);
  const apiBaseUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
  const exportReport = () => {
    window.location.href = `${apiBaseUrl}/api/v1/interviews/${id}/report`;
  };

  useEffect(() => {
    const fetchDetail = async () => {
      try {
        const response = await api.get(`/api/v1/interviews/history`);
        const session = response.data.find((s: any) => s.id === id);
        setData(session);
        if (session) {
          const analyticsResponse = await api.get(`/api/v1/interviews/${id}/analytics`);
          setAnalytics(analyticsResponse.data);
        }
      } catch (err) {
        console.error("Failed to fetch details", err);
      } finally {
        setIsLoading(false);
      }
    };
    fetchDetail();
  }, [id]);

  if (isLoading) {
    return (
      <div className="flex-1 flex items-center justify-center">
        <Loader2 className="w-12 h-12 text-primary-600 animate-spin" />
      </div>
    );
  }

  if (!data) {
    return (
      <div className="flex-1 flex flex-col items-center justify-center p-12 text-center">
        <h2 className="text-2xl font-black text-slate-900 mb-4">Session Not Found</h2>
        <Button onClick={() => router.push('/dashboard')}>Back to Dashboard</Button>
      </div>
    );
  }

  return (
    <div className="flex-1 overflow-y-auto p-8 lg:p-12 animate-fade-in">
      <header className="flex flex-col md:flex-row justify-between items-start md:items-center gap-6 mb-12">
        <div className="flex items-center gap-4">
          <Button variant="outline" size="icon" onClick={() => router.push('/dashboard')} className="rounded-xl border-slate-200">
            <ArrowLeft size={20} />
          </Button>
          <div>
            <h1 className="text-4xl font-black tracking-tight">{data.job_role || 'Technical Interview'}</h1>
            <div className="flex items-center gap-4 text-slate-500 font-medium text-sm mt-1">
              <span className="flex items-center gap-1.5"><Calendar size={14}/> {new Date(data.created_at).toLocaleDateString()}</span>
              <span className="w-1 h-1 bg-slate-300 rounded-full"></span>
              <span className="flex items-center gap-1.5"><Clock size={14}/> 15:24 min</span>
            </div>
          </div>
        </div>
        <div className="flex items-center gap-3">
          <Button className="rounded-xl px-8 h-12 shadow-lg" onClick={exportReport}>
            <Download size={18} className="mr-2" />
            Export Analytics Report
          </Button>
        </div>
      </header>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8 mb-12">
        {/* Main Stats */}
        <div className="lg:col-span-2 space-y-8">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            {[
              { label: 'Overall Proficiency', value: `${analytics?.overall_scores?.overall_score || data.overall_score || 0}%`, icon: Brain, color: 'text-primary-600', bg: 'bg-primary-50' },
              { label: 'Technical Depth', value: `${analytics?.overall_scores?.technical_knowledge || 0}%`, icon: Target, color: 'text-blue-600', bg: 'bg-blue-50' },
              { label: 'Comm. Clarity', value: `${analytics?.overall_scores?.communication || 0}%`, icon: MessageSquare, color: 'text-purple-600', bg: 'bg-purple-50' },
            ].map((stat, i) => (
              <Card key={i} className="border-none shadow-sm ring-1 ring-slate-100">
                <CardContent className="p-6">
                  <div className={`w-10 h-10 rounded-xl flex items-center justify-center ${stat.bg} ${stat.color} mb-4`}>
                    <stat.icon size={20} />
                  </div>
                  <p className="text-[10px] font-black text-slate-400 uppercase tracking-widest">{stat.label}</p>
                  <p className="text-3xl font-black text-slate-900">{stat.value}</p>
                </CardContent>
              </Card>
            ))}
          </div>

          <Card className="border-none shadow-sm ring-1 ring-slate-100 overflow-hidden">
            <CardHeader className="p-8 bg-white border-b border-slate-50">
              <CardTitle className="text-xl font-black flex items-center gap-3">
                <MessageSquare className="text-primary-600" size={24} />
                Interview Transcript
              </CardTitle>
              <CardDescription className="font-medium">Full record of the conversation and AI probing.</CardDescription>
            </CardHeader>
            <CardContent className="p-8 space-y-10 bg-slate-50/30">
              {data.transcript ? data.transcript.map((msg: any, i: number) => (
                <div key={i} className={cn("flex gap-6", msg.role === 'candidate' ? 'flex-row-reverse' : 'flex-row')}>
                  <div className={cn(
                    "w-10 h-10 rounded-xl flex-shrink-0 flex items-center justify-center shadow-sm",
                    msg.role === 'candidate' ? 'bg-slate-900 text-white' : 'bg-white text-primary-600 ring-1 ring-slate-100'
                  )}>
                    {msg.role === 'candidate' ? <User size={18} /> : <Bot size={18} />}
                  </div>
                  <div className={cn(
                    "max-w-2xl p-6 rounded-3xl text-sm font-medium leading-relaxed shadow-sm",
                    msg.role === 'candidate' ? 'bg-primary-600 text-white rounded-tr-none' : 'bg-white text-slate-700 rounded-tl-none ring-1 ring-slate-100'
                  )}>
                    {msg.content}
                  </div>
                </div>
              )) : (
                <p className="text-center py-10 text-slate-400 font-medium italic">Transcript details are being processed or unavailable.</p>
              )}
            </CardContent>
          </Card>
        </div>

        {/* Sidebar Analysis */}
        <div className="space-y-8">
           <Card className="border-none shadow-sm ring-1 ring-slate-100">
              <CardHeader className="p-6 border-b border-slate-50">
                <CardTitle className="text-lg font-black tracking-tight">Interview Intelligence</CardTitle>
              </CardHeader>
              <CardContent className="p-6 space-y-6">
                {analytics?.status === 'pending' && (
                  <div className="p-4 bg-primary-50 rounded-xl text-primary-700 text-sm font-bold">
                    Generating Interview Insights...
                  </div>
                )}
                <div>
                   <h4 className="text-[10px] font-black text-slate-400 uppercase tracking-widest mb-4">Key Strengths</h4>
                   <div className="space-y-2">
                      {(analytics?.strengths?.length ? analytics.strengths : [{ title: 'Generating strengths...' }]).map((s: any, i: number) => (
                        <div key={i} className="flex items-center gap-3 p-3 bg-emerald-50 rounded-xl text-emerald-800 text-xs font-bold">
                           <Award size={14} className="text-emerald-500" />
                           {s.title}
                        </div>
                      ))}
                   </div>
                </div>
                <div>
                   <h4 className="text-[10px] font-black text-slate-400 uppercase tracking-widest mb-4">Improvement Areas</h4>
                   <div className="space-y-2">
                      {(analytics?.weaknesses?.length ? analytics.weaknesses : [{ title: 'Generating weaknesses...' }]).map((s: any, i: number) => (
                        <div key={i} className="flex items-center gap-3 p-3 bg-amber-50 rounded-xl text-amber-800 text-xs font-bold">
                           <TrendingUp size={14} className="text-amber-500" />
                           {s.title}
                        </div>
                      ))}
                   </div>
                </div>
                <div>
                   <h4 className="text-[10px] font-black text-slate-400 uppercase tracking-widest mb-4">Roadmap</h4>
                   <div className="space-y-2">
                      {(analytics?.improvement_roadmap || []).slice(0, 3).map((item: any) => (
                        <div key={`${item.priority}-${item.skill_gap}`} className="p-3 bg-slate-50 rounded-xl text-xs">
                          <p className="font-black text-slate-900">P{item.priority}: {item.skill_gap}</p>
                          <p className="text-slate-500 mt-1">{item.recommended_action}</p>
                        </div>
                      ))}
                   </div>
                </div>
                <div>
                   <h4 className="text-[10px] font-black text-slate-400 uppercase tracking-widest mb-4">Career Recommendations</h4>
                   <div className="space-y-3">
                      {((analytics?.career_recommendations || analytics?.charts?.career_recommendations || []) as any[]).slice(0, 3).map((item: any) => (
                        <div key={item.role} className="p-3 bg-white rounded-xl border border-slate-100 text-xs">
                          <div className="flex items-start justify-between gap-2">
                            <p className="font-black text-slate-900">{item.role}</p>
                            <p className="font-black text-emerald-500">{item.fit_score}%</p>
                          </div>
                          <p className="text-slate-500 mt-1">{item.why}</p>
                        </div>
                      ))}
                   </div>
                </div>
              </CardContent>
           </Card>

           <div className="p-8 bg-primary-600 rounded-[2rem] text-white shadow-xl shadow-primary-100 relative overflow-hidden group">
              <div className="absolute top-0 right-0 p-6 opacity-10 group-hover:rotate-12 transition-transform duration-500">
                 <Bot size={120} />
              </div>
              <h3 className="text-xl font-black mb-2 relative z-10">Ready for a rematch?</h3>
              <p className="text-primary-100 text-sm font-medium mb-8 relative z-10 leading-relaxed">Your scores are improving. Take another session to hit 90%.</p>
              <Button variant="secondary" className="w-full rounded-xl font-bold bg-white text-primary-600 border-none relative z-10" onClick={() => router.push('/upload')}>
                 Retake Interview
              </Button>
           </div>
        </div>
      </div>
    </div>
  );
}

export default function InterviewDetailPage() {
  return (
    <div className="flex h-screen bg-slate-50 overflow-hidden font-sans">
      <Sidebar />
      <Suspense fallback={
        <div className="flex-1 flex items-center justify-center">
          <Loader2 className="w-12 h-12 text-primary-600 animate-spin" />
        </div>
      }>
        <InterviewDetailContent />
      </Suspense>
    </div>
  );
}
