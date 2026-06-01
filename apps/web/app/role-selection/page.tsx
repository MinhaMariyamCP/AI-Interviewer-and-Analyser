'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import api from '@/lib/api';
import { 
  Search, 
  Code2, 
  Check,
  Brain,
  Target,
  Sparkles,
  Loader2,
  AlertCircle
} from 'lucide-react';
import { Button } from '@/components/ui/Button';
import { Card, CardContent } from '@/components/ui/Card';
import { cn } from '@/lib/utils';

interface JobPreference {
  role: string;
  confidence: number;
  reasoning: string;
  source?: 'resume' | 'practice';
}

const mergeRoles = (roles: JobPreference[] = []) => {
  const roleMap = new Map<string, JobPreference>();

  const resumeRoles = roles
    .filter((item) => item?.role)
    .map((item) => ({ ...item, role: item.role.trim(), confidence: Math.round(item.confidence), source: 'resume' as const }));
  resumeRoles.forEach((item) => {
    if (!item?.role) return;
    const key = item.role.trim().toLowerCase();
    const existing = roleMap.get(key);

    if (!existing || existing.source === 'practice') {
      roleMap.set(key, {
        ...item,
        role: item.role.trim(),
        confidence: Math.round(item.confidence),
      });
    }
  });

  return Array.from(roleMap.values()).sort((a, b) => {
    if (a.source !== b.source) return a.source === 'resume' ? -1 : 1;
    return b.confidence - a.confidence;
  });
};

export default function RoleSelectionPage() {
  const [suggestedRoles, setSuggestedRoles] = useState<JobPreference[]>([]);
  const [selectedRole, setSelectedRole] = useState('');
  const [customRole, setCustomRole] = useState('');
  const [roleFilter, setRoleFilter] = useState('');
  const [isLoading, setIsLoading] = useState(true);
  const [isInitializing, setIsInitializing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const router = useRouter();

  useEffect(() => {
    const fetchRecommendations = async () => {
      const resumeId = localStorage.getItem('resume_id');
      if (!resumeId) {
        setError('Resume context missing. Please upload your resume again.');
        setIsLoading(false);
        return;
        }

      try {
        const response = await api.post(`/api/v1/resumes/${resumeId}/reanalyze`);
        const analysis = response.data.analysis_result;
        
        if (analysis && analysis.suggested_roles?.length) {
          setSuggestedRoles(mergeRoles(analysis.suggested_roles));
        } else {
          setSuggestedRoles([]);
          setError('No confident resume-based matches were found. Please use Custom / Niche Role.');
        }
      } catch (err) {
        console.error("Failed to fetch recommendations", err);
        try {
          const response = await api.get(`/api/v1/resumes/${resumeId}`);
          const analysis = response.data.analysis_result;
          setSuggestedRoles(mergeRoles(analysis?.suggested_roles || []));
          setError('Using saved role analysis because fresh analysis could not be generated.');
        } catch {
          setSuggestedRoles([]);
          setError('Failed to connect to the analysis engine.');
        }
      } finally {
        setIsLoading(false);
      }
    };

    fetchRecommendations();
  }, []);

  const handleStartInterview = async () => {
    const role = selectedRole === 'Other' ? customRole : selectedRole;
    if (!role) return;

    setIsInitializing(true);
    setError(null);

    const resumeId = localStorage.getItem('resume_id');
    try {
      const response = await api.post(`/api/v1/interviews/init?resume_id=${resumeId}&job_role=${encodeURIComponent(role)}`);
      const interviewId = response.data.interview_id;
      localStorage.setItem('current_interview_id', interviewId);
      localStorage.setItem('selected_role', role);
      router.push(`/interview?id=${interviewId}`);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to initialize interview session.');
      setIsInitializing(false);
    }
  };

  const visibleRoles = suggestedRoles.filter((item) => {
    const query = roleFilter.trim().toLowerCase();
    if (!query) return true;
    return `${item.role} ${item.reasoning}`.toLowerCase().includes(query);
  });

  if (isLoading) {
    return (
      <div className="min-h-screen bg-slate-50 flex flex-col items-center justify-center p-6 text-center">
        <div className="w-20 h-20 bg-white rounded-3xl shadow-xl flex items-center justify-center text-primary-600 mb-8 border border-slate-100 animate-bounce">
          <Brain size={40} />
        </div>
        <h2 className="text-2xl font-black text-slate-900 mb-2">Analyzing Career Path</h2>
        <p className="text-slate-500 font-medium max-w-xs mx-auto animate-pulse">Our AI agents are matching your skills to optimal technical roles...</p>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-slate-50 flex flex-col items-center justify-center p-6">
      <div className="max-w-5xl w-full animate-slide-up">
        <div className="text-center mb-12">
          <div className="inline-flex items-center px-4 py-2 rounded-full bg-primary-50 border border-primary-100 text-primary-700 text-xs font-bold mb-6 shadow-sm">
            <Sparkles size={14} className="mr-2" />
            Personalized Recommendations
          </div>
          <h1 className="text-4xl font-black text-slate-900 mb-3 tracking-tight">Select Your Target Role</h1>
          <p className="text-slate-500 font-medium">Choose from roles backed by your resume evidence or specify a custom one.</p>
        </div>
        
        {error && (
          <div className="max-w-md mx-auto mb-10 p-6 bg-red-50 text-red-600 rounded-3xl border border-red-100 flex items-center gap-4 animate-shake">
            <AlertCircle size={24} className="flex-shrink-0" />
            <div className="text-sm font-bold">{error}</div>
          </div>
        )}

        <div className="max-w-xl mx-auto mb-8 relative">
          <Search size={20} className="absolute left-5 top-1/2 -translate-y-1/2 text-slate-400" />
          <input
            type="search"
            value={roleFilter}
            onChange={(e) => setRoleFilter(e.target.value)}
            placeholder="Search more interview roles..."
            className="w-full pl-14 pr-5 py-4 bg-white border border-slate-100 rounded-2xl shadow-sm outline-none focus:ring-4 focus:ring-primary-50 focus:border-primary-300 font-bold text-slate-900 placeholder:text-slate-300"
          />
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6 mb-12">
          {visibleRoles.map((item, i) => (
            <div 
              key={i}
              onClick={() => setSelectedRole(item.role)}
              className={cn(
                "relative group cursor-pointer p-8 rounded-[2rem] border-2 transition-all duration-300 h-full flex flex-col",
                selectedRole === item.role 
                  ? 'border-primary-500 bg-white shadow-2xl shadow-primary-100 ring-4 ring-primary-50' 
                  : 'border-white bg-white hover:border-slate-200 shadow-sm hover:shadow-lg'
              )}
            >
              <div className="flex justify-between items-start mb-6">
                <div className={cn(
                  "w-12 h-12 rounded-2xl flex items-center justify-center transition-transform group-hover:scale-110",
                  selectedRole === item.role ? 'bg-primary-600 text-white' : 'bg-slate-50 text-primary-600'
                )}>
                  <Target size={24} />
                </div>
                <div className="flex flex-col items-end">
                   <span className="text-[10px] font-black text-slate-400 uppercase tracking-widest mb-1 px-1">
                     {item.source === 'practice' ? 'Practice' : 'Resume Match'}
                   </span>
                   <div className={cn(
                     "text-lg font-black font-mono",
                     item.confidence > 85 ? "text-emerald-500" : "text-primary-500"
                   )}>{item.confidence}%</div>
                </div>
              </div>
              
              <h3 className="font-bold text-slate-900 text-lg mb-3 leading-tight">{item.role}</h3>
              <p className="text-xs text-slate-500 font-medium leading-relaxed flex-1">
                {item.reasoning}
              </p>
              
              {selectedRole === item.role && (
                <div className="absolute -top-3 -right-3 w-10 h-10 bg-primary-600 rounded-2xl flex items-center justify-center text-white shadow-xl shadow-primary-200 animate-in zoom-in duration-300">
                  <Check size={20} strokeWidth={3} />
                </div>
              )}
            </div>
          ))}

          {visibleRoles.length === 0 && (
            <div className="lg:col-span-2 p-8 rounded-[2rem] border-2 border-dashed border-slate-200 bg-white text-center">
              <h3 className="font-black text-slate-900 mb-2">No confident resume matches yet</h3>
              <p className="text-sm text-slate-500 font-medium">
                The parser did not find enough evidence for a specific role. Use the custom option and the interview will tailor questions to that target.
              </p>
            </div>
          )}

          {/* Custom Role Option */}
          <div 
            onClick={() => setSelectedRole('Other')}
            className={cn(
              "relative group cursor-pointer p-8 rounded-[2rem] border-2 transition-all duration-300 h-full flex flex-col",
              selectedRole === 'Other' 
                ? 'border-primary-500 bg-white shadow-2xl shadow-primary-100 ring-4 ring-primary-50' 
                : 'border-white bg-white hover:border-slate-200 shadow-sm hover:shadow-lg'
            )}
          >
            <div className={cn(
              "w-12 h-12 rounded-2xl flex items-center justify-center mb-6 transition-transform group-hover:scale-110",
              selectedRole === 'Other' ? 'bg-primary-600 text-white' : 'bg-slate-50 text-slate-400'
            )}>
              <Search size={24} />
            </div>
            <h3 className="font-bold text-slate-900 text-lg mb-3">Custom / Niche Role</h3>
            <p className="text-xs text-slate-400 font-medium leading-relaxed">
              Don't see a perfect match? Specify the exact role you're preparing for.
            </p>
            {selectedRole === 'Other' && (
              <div className="absolute -top-3 -right-3 w-10 h-10 bg-primary-600 rounded-2xl flex items-center justify-center text-white shadow-xl shadow-primary-200 animate-in zoom-in duration-300">
                <Check size={20} strokeWidth={3} />
              </div>
            )}
          </div>
        </div>

        {selectedRole === 'Other' && (
          <div className="mb-12 animate-in fade-in slide-in-from-top-4 duration-500 max-w-lg mx-auto">
            <label className="block text-[10px] font-black text-slate-400 uppercase tracking-[0.2em] mb-4 ml-2">Specify Custom Job Title</label>
            <input
              type="text"
              autoFocus
              value={customRole}
              onChange={(e) => setCustomRole(e.target.value)}
              placeholder="e.g. Senior Applied AI Engineer"
              className="w-full px-8 py-5 bg-white border-none rounded-[1.5rem] shadow-2xl shadow-slate-200 focus:ring-4 focus:ring-primary-50 focus:border-primary-500 outline-none transition-all font-bold text-slate-900 placeholder:text-slate-300"
            />
          </div>
        )}

        <div className="max-w-md mx-auto text-center pb-20">
          <Button
            onClick={handleStartInterview}
            disabled={(!selectedRole || (selectedRole === 'Other' && !customRole)) || isInitializing}
            className="w-full h-16 rounded-[1.5rem] text-xl font-black shadow-2xl shadow-primary-200"
            isLoading={isInitializing}
          >
            {isInitializing ? 'Configuring AI Persona...' : 'Begin AI Assessment'}
          </Button>
          
          <p className="mt-8 text-[11px] text-slate-400 font-bold uppercase tracking-widest leading-relaxed">
            By clicking above, you'll start a live interactive session with our AI recruiter.
          </p>
        </div>
      </div>
    </div>
  );
}
