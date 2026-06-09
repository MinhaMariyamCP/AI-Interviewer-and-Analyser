'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import api from '@/lib/api';
import { 
  TrendingUp, 
  CheckCircle2, 
  Clock, 
  Loader2,
  ExternalLink,
  Download,
  Calendar,
  Bot,
  Mic,
  Sparkles,
  Target,
  ArrowRight,
  Upload
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

interface VoiceProfile {
  id: string;
  status: string;
  overall_score: number | null;
  created_at: string;
  candidate_profile?: {
    name?: string;
    skills?: string[];
    career_interests?: string[];
  };
  recommended_roles?: Array<{
    role: string;
    confidence: number;
    reason: string;
  }>;
}

export default function DashboardPage() {
  const [interviews, setInterviews] = useState<Interview[]>([]);
  const [voiceProfiles, setVoiceProfiles] = useState<VoiceProfile[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const router = useRouter();
  const apiBaseUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

  useEffect(() => {
    const fetchInterviews = async () => {
      try {
        const response = await api.get('/api/v1/interviews/history');
        setInterviews(response.data);
        const voiceResponse = await api.get('/api/v1/voice-interviews/history');
        setVoiceProfiles(voiceResponse.data);
      } catch (err) {
        console.error('Failed to fetch interviews', err);
      } finally {
        setIsLoading(false);
      }
    };

    fetchInterviews();
    const interval = setInterval(fetchInterviews, 5000);
    return () => clearInterval(interval);
  }, []);

  const latestVoiceProfile = voiceProfiles[0];
  const latestRoles = latestVoiceProfile?.recommended_roles || [];

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
      value: interviews.filter(i => i.status === 'completed').length + voiceProfiles.length,
      icon: CheckCircle2,
      color: 'text-emerald-600',
      bg: 'bg-emerald-50'
    },
    { 
      label: 'Total Sessions', 
      value: interviews.length + voiceProfiles.length,
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
            <h1 className="text-4xl font-black tracking-tight mb-2">AI Interview Dashboard</h1>
            <p className="text-slate-500 font-medium">Start with a voice interview, then review your generated profile and role matches.</p>
          </div>
          <div className="flex items-center gap-4">
             <Button variant="outline" className="rounded-xl border-slate-200" onClick={() => router.push('/dashboard/analytics')}>
                Full Analytics
             </Button>
             <Button className="rounded-xl px-8 shadow-lg shadow-primary-200" onClick={() => router.push('/voice-interview')}>
                <Mic size={18} className="mr-2" />
                Start AI Interview
             </Button>
          </div>
        </header>

        <section className="grid grid-cols-1 xl:grid-cols-[1.3fr_0.7fr] gap-6 mb-12 animate-slide-up">
          <Card className="border-none shadow-xl shadow-primary-100/40 ring-1 ring-primary-100 overflow-hidden">
            <CardContent className="p-0">
              <div className="bg-slate-950 text-white p-10 relative overflow-hidden">
                <div className="absolute right-8 top-8 opacity-10">
                  <Bot size={180} />
                </div>
                <div className="relative z-10 max-w-2xl">
                  <p className="text-xs font-black text-primary-300 uppercase tracking-[0.24em] mb-3">Voice-First Career Screening</p>
                  <h2 className="text-4xl font-black tracking-tight mb-4">Talk naturally. Get a candidate profile and role matches.</h2>
                  <p className="text-slate-300 font-medium leading-relaxed mb-8">
                    The AI interviewer collects your education, skills, projects, certifications, experience, and career goals through a Vapi voice conversation.
                  </p>
                  <div className="flex flex-col sm:flex-row gap-3">
                    <Button className="h-14 rounded-2xl px-8 font-black" onClick={() => router.push('/voice-interview')}>
                      <Mic size={18} className="mr-2" />
                      Start AI Interview
                    </Button>
                    <Button variant="outline" className="h-14 rounded-2xl px-8 font-black border-white/20 bg-white/5 text-white hover:bg-white/10" onClick={() => router.push('/upload')}>
                      <Upload size={18} className="mr-2" />
                      Resume Upload
                    </Button>
                  </div>
                </div>
              </div>
            </CardContent>
          </Card>

          <Card className="border-none shadow-sm ring-1 ring-slate-100">
            <CardContent className="p-8">
              <div className="flex items-center gap-3 mb-6">
                <div className="w-12 h-12 rounded-2xl bg-emerald-50 text-emerald-600 flex items-center justify-center">
                  <Target size={24} />
                </div>
                <div>
                  <p className="text-xs font-black uppercase tracking-widest text-slate-400">Recommended Roles</p>
                  <h3 className="text-xl font-black">Latest results</h3>
                </div>
              </div>

              {latestRoles.length === 0 ? (
                <div className="rounded-2xl bg-slate-50 border border-slate-100 p-6 text-center">
                  <Sparkles className="w-10 h-10 mx-auto text-slate-300 mb-3" />
                  <p className="text-sm font-bold text-slate-500">Complete a voice interview to unlock personalized role recommendations.</p>
                </div>
              ) : (
                <div className="space-y-3">
                  {latestRoles.slice(0, 3).map((role) => (
                    <div key={role.role} className="rounded-2xl bg-slate-50 border border-slate-100 p-4">
                      <div className="flex items-center justify-between gap-3 mb-2">
                        <p className="font-black text-slate-900">{role.role}</p>
                        <span className="text-xs font-black text-primary-700 bg-white px-2 py-1 rounded-full">{role.confidence}%</span>
                      </div>
                      <p className="text-xs font-semibold text-slate-500 leading-relaxed">{role.reason}</p>
                    </div>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>
        </section>

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

        {/* Recent Voice Interviews */}
        <div className="animate-slide-up [animation-delay:0.1s] mb-12">
          <Card className="border-none shadow-sm ring-1 ring-slate-100 overflow-hidden">
            <CardHeader className="p-8 border-b border-slate-50 flex flex-row items-center justify-between">
              <div>
                <CardTitle className="text-xl font-black">Voice Interview History</CardTitle>
                <CardDescription className="font-medium mt-1">Generated candidate profiles and job-role recommendations.</CardDescription>
              </div>
              <Button variant="ghost" size="sm" className="font-bold text-primary-600" onClick={() => router.push('/voice-interview')}>New Voice Interview</Button>
            </CardHeader>
            <CardContent className="p-0">
              {isLoading ? (
                <div className="flex flex-col items-center justify-center p-20">
                  <Loader2 className="w-10 h-10 text-primary-600 animate-spin mb-4" />
                  <p className="text-sm font-bold text-slate-400 uppercase tracking-widest">Fetching voice profiles...</p>
                </div>
              ) : voiceProfiles.length === 0 ? (
                <div className="text-center p-16 bg-white">
                  <div className="w-20 h-20 bg-slate-50 rounded-3xl flex items-center justify-center text-slate-200 mx-auto mb-6">
                    <Mic size={40} />
                  </div>
                  <h3 className="text-lg font-bold text-slate-900 mb-2">No voice interviews yet</h3>
                  <p className="text-slate-400 text-sm font-medium mb-8 max-w-sm mx-auto">Start your first Vapi-powered interview to create a candidate profile without uploading a resume.</p>
                  <Button onClick={() => router.push('/voice-interview')} className="rounded-xl px-10">Start AI Interview</Button>
                </div>
              ) : (
                <div className="divide-y divide-slate-50">
                  {voiceProfiles.map((profile) => (
                    <div key={profile.id} className="p-6 lg:p-8 hover:bg-slate-50/70 transition-colors">
                      <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-5">
                        <div className="flex items-start gap-4">
                          <div className="w-12 h-12 bg-primary-50 rounded-2xl flex items-center justify-center text-primary-600">
                            <Bot size={24} />
                          </div>
                          <div>
                            <p className="font-black text-slate-900">{profile.candidate_profile?.name || 'Voice Candidate Profile'}</p>
                            <p className="text-sm font-semibold text-slate-400 mt-1">
                              {new Date(profile.created_at).toLocaleDateString(undefined, { month: 'short', day: 'numeric', year: 'numeric' })}
                            </p>
                            <div className="flex flex-wrap gap-2 mt-3">
                              {(profile.candidate_profile?.skills || []).slice(0, 5).map((skill) => (
                                <span key={skill} className="px-2 py-1 rounded-lg bg-white border border-slate-100 text-[10px] font-black uppercase tracking-wider text-slate-500">
                                  {skill}
                                </span>
                              ))}
                            </div>
                          </div>
                        </div>
                        <div className="flex flex-wrap gap-3">
                          {(profile.recommended_roles || []).slice(0, 3).map((role) => (
                            <div key={role.role} className="rounded-xl bg-white border border-slate-100 px-4 py-3 min-w-[180px]">
                              <p className="text-xs font-black text-slate-900">{role.role}</p>
                              <p className="text-[10px] font-black text-primary-600 mt-1">{role.confidence}% match</p>
                            </div>
                          ))}
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>
        </div>

        {/* Recent Legacy Interviews */}
        <div className="animate-slide-up [animation-delay:0.1s]">
          <Card className="border-none shadow-sm ring-1 ring-slate-100 overflow-hidden">
            <CardHeader className="p-8 border-b border-slate-50 flex flex-row items-center justify-between">
              <div>
                <CardTitle className="text-xl font-black">Resume-Based Interview Archive</CardTitle>
                <CardDescription className="font-medium mt-1">Older upload-based interview performances and reports.</CardDescription>
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
                    <Bot size={40} />
                  </div>
                  <h3 className="text-lg font-bold text-slate-900 mb-2">No session history found</h3>
                  <p className="text-slate-400 text-sm font-medium mb-8 max-w-xs mx-auto">Start your first AI-powered interview to see results here.</p>
                  <Button onClick={() => router.push('/voice-interview')} className="rounded-xl px-10">Start Voice Interview</Button>
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
                                onClick={() => window.location.href = `${apiBaseUrl}/api/v1/interviews/${interview.id}/report`}
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
