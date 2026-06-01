'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import api from '@/lib/api';
import { 
  TrendingUp, 
  CheckCircle2, 
  Clock, 
  FileText,
  Loader2,
  ArrowRight,
  ExternalLink,
  Download,
  Calendar,
  MoreVertical,
  Bot
} from 'lucide-react';
import { Sidebar } from '@/components/layout/Sidebar';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { cn } from '@/lib/utils';

interface Interview {
  id: string;
  status: string;
  overall_score: number | null;
  created_at: string;
  job_role?: string;
}

export default function DashboardPage() {
  const [interviews, setInterviews] = useState<Interview[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const router = useRouter();

  useEffect(() => {
    const fetchInterviews = async () => {
      try {
        const response = await api.get('/api/v1/interviews/history');
        setInterviews(response.data);
      } catch (err) {
        console.error('Failed to fetch interviews', err);
      } finally {
        setIsLoading(false);
      }
    };

    fetchInterviews();
  }, []);

  const stats = [
    { 
      label: 'Average Score', 
      value: interviews.length > 0 
        ? `${(interviews.reduce((acc, curr) => acc + (curr.overall_score || 0), 0) / interviews.length).toFixed(1)}%` 
        : '0.0%',
      icon: TrendingUp,
      color: 'text-blue-600',
      bg: 'bg-blue-50'
    },
    { 
      label: 'Completed', 
      value: interviews.filter(i => i.status === 'completed').length,
      icon: CheckCircle2,
      color: 'text-emerald-600',
      bg: 'bg-emerald-50'
    },
    { 
      label: 'Total Sessions', 
      value: interviews.length,
      icon: Clock,
      color: 'text-amber-600',
      bg: 'bg-amber-50'
    },
  ];

  return (
    <div className="flex h-screen bg-slate-50 overflow-hidden font-sans text-slate-900">
      <Sidebar />

      <main className="flex-1 overflow-y-auto p-8 lg:p-12">
        <header className="flex flex-col md:flex-row justify-between items-start md:items-center gap-6 mb-12 animate-fade-in">
          <div>
            <h1 className="text-4xl font-black tracking-tight mb-2">Overview</h1>
            <p className="text-slate-500 font-medium italic">"Every session is a step closer to your dream role."</p>
          </div>
          <div className="flex items-center gap-4">
             <Button variant="outline" className="rounded-xl border-slate-200" onClick={() => router.push('/dashboard/analytics')}>
                Full Analytics
             </Button>
             <Button className="rounded-xl px-8 shadow-lg shadow-primary-200" onClick={() => router.push('/upload')}>
                New Session
             </Button>
          </div>
        </header>

        {/* Stats Grid */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-12 animate-slide-up">
          {stats.map((stat, i) => (
            <Card key={i} className="border-none shadow-sm ring-1 ring-slate-100 transition-all hover:ring-primary-200 hover:shadow-xl hover:shadow-primary-50">
              <CardContent className="p-8">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-xs font-bold text-slate-400 uppercase tracking-widest mb-1">{stat.label}</p>
                    <p className="text-4xl font-black text-slate-900">{stat.value}</p>
                  </div>
                  <div className={cn("p-4 rounded-2xl shadow-inner", stat.bg, stat.color)}>
                    <stat.icon size={28} />
                  </div>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>

        {/* Recent Interviews */}
        <div className="animate-slide-up [animation-delay:0.1s]">
          <Card className="border-none shadow-sm ring-1 ring-slate-100 overflow-hidden">
            <CardHeader className="p-8 border-b border-slate-50 flex flex-row items-center justify-between">
              <div>
                <CardTitle className="text-xl font-black">Recent Activity</CardTitle>
                <CardDescription className="font-medium mt-1">Your latest interview performances and reports.</CardDescription>
              </div>
              <Button variant="ghost" size="sm" className="font-bold text-primary-600">View Archive</Button>
            </CardHeader>
            <CardContent className="p-0">
              {isLoading ? (
                <div className="flex flex-col items-center justify-center p-20">
                  <Loader2 className="w-10 h-10 text-primary-600 animate-spin mb-4" />
                  <p className="text-sm font-bold text-slate-400 uppercase tracking-widest">Fetching data...</p>
                </div>
              ) : interviews.length === 0 ? (
                <div className="text-center p-24 bg-white">
                  <div className="w-20 h-20 bg-slate-50 rounded-3xl flex items-center justify-center text-slate-200 mx-auto mb-6">
                    <FileText size={40} />
                  </div>
                  <h3 className="text-lg font-bold text-slate-900 mb-2">No session history found</h3>
                  <p className="text-slate-400 text-sm font-medium mb-8 max-w-xs mx-auto">Start your first AI-powered interview to see results here.</p>
                  <Button onClick={() => router.push('/upload')} className="rounded-xl px-10">Start Session</Button>
                </div>
              ) : (
                <div className="overflow-x-auto">
                  <table className="w-full">
                    <thead>
                      <tr className="text-left text-[10px] font-black text-slate-400 uppercase tracking-[0.2em] bg-slate-50/50">
                        <th className="px-8 py-5">Target Role</th>
                        <th className="px-8 py-5">Status</th>
                        <th className="px-8 py-5">Proficiency</th>
                        <th className="px-8 py-5">Session Date</th>
                        <th className="px-8 py-5 text-right">Actions</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-50">
                      {interviews.map((interview) => (
                        <tr key={interview.id} className="group hover:bg-slate-50/80 transition-all duration-200">
                          <td className="px-8 py-6">
                            <div className="flex items-center gap-3">
                              <div className="w-10 h-10 bg-white rounded-xl shadow-sm border border-slate-100 flex items-center justify-center text-slate-400 group-hover:text-primary-600 group-hover:border-primary-100 transition-colors">
                                <Bot size={20} />
                              </div>
                              <span className="font-bold text-slate-900 group-hover:text-primary-700">{interview.job_role || 'Software Engineer'}</span>
                            </div>
                          </td>
                          <td className="px-8 py-6">
                            <span className={cn(
                              "inline-flex items-center px-3 py-1 rounded-full text-[10px] font-black uppercase tracking-widest",
                              interview.status === 'completed' 
                                ? 'bg-emerald-50 text-emerald-700 ring-1 ring-emerald-100' 
                                : 'bg-amber-50 text-amber-700 ring-1 ring-amber-100'
                            )}>
                              {interview.status}
                            </span>
                          </td>
                          <td className="px-8 py-6">
                            <div className="flex items-center gap-3">
                              <div className="flex-1 h-1.5 w-20 bg-slate-100 rounded-full overflow-hidden hidden md:block">
                                <div 
                                  className={cn(
                                    "h-full rounded-full transition-all duration-1000",
                                    (interview.overall_score || 0) > 70 ? 'bg-emerald-500' : 'bg-primary-500'
                                  )}
                                  style={{ width: `${interview.overall_score || 0}%` }}
                                ></div>
                              </div>
                              <span className="font-mono font-black text-slate-900">
                                {interview.overall_score?.toFixed(1) || '--'}%
                              </span>
                            </div>
                          </td>
                          <td className="px-8 py-6">
                            <div className="flex items-center gap-2 text-slate-500 font-medium text-sm">
                              <Calendar size={14} className="text-slate-300" />
                              {new Date(interview.created_at).toLocaleDateString(undefined, { month: 'short', day: 'numeric', year: 'numeric' })}
                            </div>
                          </td>
                          <td className="px-8 py-6 text-right">
                            <div className="flex items-center justify-end gap-2">
                              <button 
                                onClick={() => window.location.href = `/api/v1/reports/${interview.id}/download`}
                                className="p-2.5 bg-white text-slate-400 hover:text-primary-600 hover:bg-primary-50 rounded-xl transition-all shadow-sm border border-slate-100 hover:border-primary-100"
                                title="Download PDF Report"
                              >
                                <Download size={18} />
                              </button>
                              <button 
                                onClick={() => router.push(`/dashboard/interview/${interview.id}`)}
                                className="p-2.5 bg-white text-slate-400 hover:text-primary-600 hover:bg-primary-50 rounded-xl transition-all shadow-sm border border-slate-100 hover:border-primary-100"
                                title="View Session Details"
                              >
                                <ExternalLink size={18} />
                              </button>
                            </div>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </CardContent>
          </Card>
        </div>
      </main>
    </div>
  );
}
