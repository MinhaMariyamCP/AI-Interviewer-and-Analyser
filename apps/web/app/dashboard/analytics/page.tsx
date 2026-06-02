'use client';

import React, { useEffect, useState } from 'react';
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
  BarChart, Bar, Cell, AreaChart, Area, RadarChart, PolarGrid, PolarAngleAxis, Radar
} from 'recharts';
import { TrendingUp, Loader2, Target, Brain, MessageSquare, ArrowLeft, ShieldCheck, Zap, Download } from 'lucide-react';
import Link from 'next/link';
import api from '@/lib/api';
import { Sidebar } from '@/components/layout/Sidebar';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';

export default function AnalyticsDashboard() {
  const [data, setData] = useState<any>(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    const fetchAnalytics = async () => {
      try {
        const response = await api.get('/api/v1/analytics/interviews');
        setData(response.data);
      } catch (err) {
        console.error('Failed to fetch analytics', err);
      } finally {
        setIsLoading(false);
      }
    };
    fetchAnalytics();
  }, []);

  if (isLoading) {
    return (
      <div className="flex h-screen bg-slate-50 overflow-hidden dark:bg-slate-950">
        <Sidebar />
        <main className="flex-1 flex items-center justify-center">
          <div className="flex flex-col items-center">
            <Loader2 className="w-12 h-12 text-primary-600 animate-spin mb-4" />
            <p className="text-sm font-bold text-slate-400 uppercase tracking-widest">Aggregating intelligence...</p>
          </div>
        </main>
      </div>
    );
  }

  if (!data || !data.latest) {
    return (
      <div className="flex h-screen bg-slate-50 overflow-hidden dark:bg-slate-950">
        <Sidebar />
        <main className="flex-1 flex flex-col items-center justify-center p-12 text-center">
          <div className="w-24 h-24 bg-white rounded-[2.5rem] shadow-xl flex items-center justify-center text-slate-200 mb-8 border border-slate-100 dark:bg-slate-900 dark:border-slate-800">
            <Target size={48} />
          </div>
          <h1 className="text-3xl font-black text-slate-900 mb-4 dark:text-white">No Deep Analytics Yet</h1>
          <p className="text-slate-500 max-w-md mx-auto mb-8 font-medium dark:text-slate-300">Complete an interview to generate strengths, weaknesses, topic mastery, confidence trends, and a roadmap.</p>
          <Button onClick={() => window.location.href = '/upload'} className="rounded-2xl px-10 h-14 font-bold shadow-lg shadow-primary-200">Start First Session</Button>
        </main>
      </div>
    );
  }

  const latest = data.latest;
  const scores = data.avg_scores || {};
  const charts = latest.charts || {};
  const topicData = charts.topic_bars || latest.concept_clarity || [];
  const technicalDepth = charts.technical_depth || latest.technical_depth || [];
  const behavioral = charts.behavioral || latest.behavioral || [];
  const questionTimeline = charts.timeline || latest.question_analytics?.performance_timeline || [];
  const confidenceTrend = charts.confidence_trend || latest.confidence?.confidence_trend || [];
  const careerRecommendations = latest.career_recommendations || charts.career_recommendations || [];
  const apiBaseUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
  const exportReport = () => {
    window.location.href = `${apiBaseUrl}/api/v1/interviews/${latest.interview_id}/report`;
  };

  return (
    <div className="flex h-screen bg-slate-50 overflow-hidden font-sans text-slate-900 dark:bg-slate-950 dark:text-white">
      <Sidebar />

      <main className="flex-1 overflow-y-auto p-8 lg:p-12">
        <header className="mb-12 animate-fade-in">
          <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
            <div className="flex items-center gap-4">
              <Link href="/dashboard" className="p-2 bg-white rounded-xl shadow-sm border border-slate-100 text-slate-400 hover:text-primary-600 transition-all dark:bg-slate-900 dark:border-slate-800">
                <ArrowLeft size={20} />
              </Link>
              <div>
                <h1 className="text-4xl font-black tracking-tight">Interview Intelligence</h1>
                <p className="text-slate-500 font-medium mt-1 dark:text-slate-300">{latest.executive_summary}</p>
              </div>
            </div>
            <Button onClick={exportReport} className="rounded-xl px-6">
              <Download size={18} className="mr-2" />
              Export Analytics Report
            </Button>
          </div>
        </header>

        <div className="grid grid-cols-1 md:grid-cols-4 gap-6 mb-10">
          {[
            { label: 'Overall', value: scores.overall, icon: Brain, color: 'text-primary-600', bg: 'bg-primary-50' },
            { label: 'Technical', value: scores.technical, icon: Target, color: 'text-blue-600', bg: 'bg-blue-50' },
            { label: 'Communication', value: scores.communication, icon: MessageSquare, color: 'text-purple-600', bg: 'bg-purple-50' },
            { label: 'Confidence', value: scores.confidence, icon: ShieldCheck, color: 'text-emerald-600', bg: 'bg-emerald-50' },
          ].map((stat) => (
            <Card key={stat.label} className="border-none shadow-sm ring-1 ring-slate-100 dark:ring-slate-800">
              <CardContent className="p-6 flex items-center gap-4">
                <div className={`w-12 h-12 rounded-2xl flex items-center justify-center ${stat.bg} ${stat.color}`}>
                  <stat.icon size={24} />
                </div>
                <div>
                  <p className="text-[10px] font-black text-slate-400 uppercase tracking-widest">{stat.label}</p>
                  <p className="text-2xl font-black text-slate-900 dark:text-white">{stat.value || 0}%</p>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>

        <div className="grid grid-cols-1 xl:grid-cols-2 gap-8 mb-8">
          <Card className="border-none shadow-sm ring-1 ring-slate-100 dark:ring-slate-800">
            <CardHeader className="p-8">
              <CardTitle className="text-xl font-black">Score Radar</CardTitle>
              <CardDescription>Normalized 0-100 view of your core interview dimensions.</CardDescription>
            </CardHeader>
            <CardContent className="p-6 h-80">
              <ResponsiveContainer width="100%" height="100%">
                <RadarChart data={charts.radar || []}>
                  <PolarGrid />
                  <PolarAngleAxis dataKey="metric" tick={{ fontSize: 11 }} />
                  <Radar dataKey="score" stroke="#2563eb" fill="#2563eb" fillOpacity={0.25} />
                  <Tooltip />
                </RadarChart>
              </ResponsiveContainer>
            </CardContent>
          </Card>

          <Card className="border-none shadow-sm ring-1 ring-slate-100 dark:ring-slate-800">
            <CardHeader className="p-8">
              <CardTitle className="text-xl font-black">Performance Trend</CardTitle>
              <CardDescription>Progress across completed interview sessions.</CardDescription>
            </CardHeader>
            <CardContent className="p-6 h-80">
              <ResponsiveContainer width="100%" height="100%">
                <AreaChart data={data.trends || []}>
                  <defs>
                    <linearGradient id="overallTrend" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="#2563eb" stopOpacity={0.2} />
                      <stop offset="95%" stopColor="#2563eb" stopOpacity={0} />
                    </linearGradient>
                  </defs>
                  <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#e2e8f0" />
                  <XAxis dataKey="name" tick={{ fontSize: 10 }} />
                  <YAxis domain={[0, 100]} tick={{ fontSize: 10 }} />
                  <Tooltip />
                  <Area type="monotone" dataKey="overall" stroke="#2563eb" strokeWidth={3} fill="url(#overallTrend)" />
                  <Line type="monotone" dataKey="technical" stroke="#9333ea" strokeWidth={2} />
                  <Line type="monotone" dataKey="communication" stroke="#10b981" strokeWidth={2} />
                </AreaChart>
              </ResponsiveContainer>
            </CardContent>
          </Card>

          <Card className="border-none shadow-sm ring-1 ring-slate-100 dark:ring-slate-800">
            <CardHeader className="p-8">
              <CardTitle className="text-xl font-black">Topic Mastery</CardTitle>
              <CardDescription>Clarity and depth by technical concept.</CardDescription>
            </CardHeader>
            <CardContent className="p-6 h-80">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={topicData}>
                  <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#e2e8f0" />
                  <XAxis dataKey="topic" tick={{ fontSize: 10 }} />
                  <YAxis domain={[0, 100]} tick={{ fontSize: 10 }} />
                  <Tooltip />
                  <Bar dataKey="topic_score" radius={[8, 8, 0, 0]}>
                    {topicData.map((_: any, i: number) => <Cell key={i} fill={['#2563eb', '#10b981', '#9333ea', '#f59e0b'][i % 4]} />)}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            </CardContent>
          </Card>

          <Card className="border-none shadow-sm ring-1 ring-slate-100 dark:ring-slate-800">
            <CardHeader className="p-8">
              <CardTitle className="text-xl font-black">Question Timeline</CardTitle>
              <CardDescription>Per-question performance arc.</CardDescription>
            </CardHeader>
            <CardContent className="p-6 h-80">
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={questionTimeline}>
                  <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#e2e8f0" />
                  <XAxis dataKey="name" tick={{ fontSize: 10 }} />
                  <YAxis domain={[0, 100]} tick={{ fontSize: 10 }} />
                  <Tooltip />
                  <Line type="monotone" dataKey="score" stroke="#2563eb" strokeWidth={4} dot={{ r: 5 }} />
                </LineChart>
              </ResponsiveContainer>
            </CardContent>
          </Card>
        </div>

        <div className="grid grid-cols-1 xl:grid-cols-3 gap-8 mb-8">
          <InsightPanel title="Strengths" items={latest.strengths} positive />
          <InsightPanel title="Weaknesses" items={latest.weaknesses} />
          <Card className="border-none shadow-sm ring-1 ring-slate-100 dark:ring-slate-800">
            <CardHeader className="p-6">
              <CardTitle className="text-lg font-black flex items-center gap-2"><Zap size={18} /> Filler Words</CardTitle>
            </CardHeader>
            <CardContent className="p-6 pt-0">
              <p className="text-4xl font-black text-slate-900 dark:text-white">{latest.filler_words?.total_count || 0}</p>
              <p className="text-xs font-bold uppercase tracking-widest text-slate-400 mb-4">Total fillers</p>
              {(latest.filler_words?.recommendations || []).map((item: string) => (
                <p key={item} className="text-sm text-slate-500 mb-2 dark:text-slate-300">{item}</p>
              ))}
            </CardContent>
          </Card>
        </div>

        <Card className="border-none shadow-sm ring-1 ring-slate-100 mb-8 dark:ring-slate-800">
          <CardHeader className="p-8">
            <CardTitle className="text-xl font-black">Career Recommendations</CardTitle>
            <CardDescription>Distinct role paths ranked from resume evidence, selected target role, and interview performance.</CardDescription>
          </CardHeader>
          <CardContent className="p-8 pt-0 grid grid-cols-1 lg:grid-cols-3 gap-4">
            {(careerRecommendations || []).map((item: any, index: number) => (
              <div key={`${item.role}-${index}`} className="p-5 rounded-2xl bg-white border border-slate-100 shadow-sm dark:bg-slate-900 dark:border-slate-800">
                <div className="flex items-start justify-between gap-3 mb-4">
                  <div>
                    <p className="text-[10px] font-black text-primary-600 uppercase tracking-widest mb-1">{item.career_path}</p>
                    <h3 className="font-black text-slate-900 dark:text-white">{item.role}</h3>
                  </div>
                  <p className="text-2xl font-black font-mono text-emerald-500">{item.fit_score}%</p>
                </div>
                <p className="text-xs font-bold text-slate-400 uppercase tracking-widest mb-2">{item.readiness}</p>
                <p className="text-sm text-slate-500 leading-relaxed mb-4 dark:text-slate-300">{item.why}</p>
                <div className="flex flex-wrap gap-2 mb-4">
                  {(item.evidence || []).map((tag: string) => (
                    <span key={tag} className="px-2 py-1 rounded-lg bg-primary-50 text-primary-700 text-[10px] font-black uppercase tracking-wider">
                      {tag}
                    </span>
                  ))}
                </div>
                <p className="text-sm font-bold text-slate-700 dark:text-slate-200">{item.next_step}</p>
              </div>
            ))}
            {(!careerRecommendations || careerRecommendations.length === 0) && (
              <p className="text-sm text-slate-500 font-medium">Complete a fresh interview to generate career recommendations.</p>
            )}
          </CardContent>
        </Card>

        <div className="grid grid-cols-1 xl:grid-cols-2 gap-8 mb-8">
          <MiniBar title="Technical Depth Breakdown" data={technicalDepth} labelKey="category" valueKey="score" />
          <MiniBar title="Behavioral Skills" data={behavioral} labelKey="category" valueKey="score" />
        </div>

        <Card className="border-none shadow-sm ring-1 ring-slate-100 mb-12 dark:ring-slate-800">
          <CardHeader className="p-8">
            <CardTitle className="text-xl font-black">Improvement Roadmap</CardTitle>
            <CardDescription>Prioritized actions generated from weaknesses and question-level evidence.</CardDescription>
          </CardHeader>
          <CardContent className="p-8 pt-0 grid grid-cols-1 md:grid-cols-2 gap-4">
            {(latest.improvement_roadmap || []).map((item: any) => (
              <div key={`${item.priority}-${item.skill_gap}`} className="p-5 rounded-2xl bg-slate-50 border border-slate-100 dark:bg-slate-900 dark:border-slate-800">
                <p className="text-[10px] font-black text-primary-600 uppercase tracking-widest mb-2">Priority {item.priority}</p>
                <h3 className="font-black text-slate-900 mb-2 dark:text-white">{item.skill_gap}</h3>
                <p className="text-sm text-slate-500 mb-3 dark:text-slate-300">{item.explanation}</p>
                <p className="text-sm font-bold text-slate-700 dark:text-slate-200">{item.recommended_action}</p>
              </div>
            ))}
          </CardContent>
        </Card>
      </main>
    </div>
  );
}

function InsightPanel({ title, items, positive = false }: { title: string; items: any[]; positive?: boolean }) {
  return (
    <Card className="border-none shadow-sm ring-1 ring-slate-100 dark:ring-slate-800">
      <CardHeader className="p-6">
        <CardTitle className="text-lg font-black">{title}</CardTitle>
      </CardHeader>
      <CardContent className="p-6 pt-0 space-y-3">
        {(items || []).slice(0, 5).map((item: any, index: number) => (
          <div key={index} className={`p-4 rounded-2xl border ${positive ? 'bg-emerald-50 border-emerald-100 text-emerald-800' : 'bg-amber-50 border-amber-100 text-amber-800'}`}>
            <p className="text-sm font-black">{item.title || item.severity}</p>
            <p className="text-xs mt-1 opacity-80">{item.explanation || item.improvement_suggestion}</p>
          </div>
        ))}
      </CardContent>
    </Card>
  );
}

function MiniBar({ title, data, labelKey, valueKey }: { title: string; data: any[]; labelKey: string; valueKey: string }) {
  return (
    <Card className="border-none shadow-sm ring-1 ring-slate-100 dark:ring-slate-800">
      <CardHeader className="p-8">
        <CardTitle className="text-xl font-black">{title}</CardTitle>
      </CardHeader>
      <CardContent className="p-6 h-80">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={data || []} layout="vertical" margin={{ left: 30 }}>
            <CartesianGrid strokeDasharray="3 3" horizontal={false} stroke="#e2e8f0" />
            <XAxis type="number" domain={[0, 100]} tick={{ fontSize: 10 }} />
            <YAxis dataKey={labelKey} type="category" tick={{ fontSize: 10 }} width={110} />
            <Tooltip />
            <Bar dataKey={valueKey} fill="#2563eb" radius={[0, 8, 8, 0]} />
          </BarChart>
        </ResponsiveContainer>
      </CardContent>
    </Card>
  );
}
