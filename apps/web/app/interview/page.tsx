'use client';

import { useState, useEffect, useRef, Suspense } from 'react';
import { useSearchParams, useRouter } from 'next/navigation';
import {
  User,
  Bot,
  Loader2,
  Award,
  LogOut,
  Mic,
  MicOff,
  Timer,
  ChevronRight,
  Sparkles,
  Info,
  Clock,
  AlertCircle,
  Radio,
  TrendingUp,
  Brain,
  MessageCircle,
  Zap
} from 'lucide-react';
import { Button } from '@/components/ui/Button';
import { Card, CardContent } from '@/components/ui/Card';
import { VapiAssistant } from '@/components/voice/VapiAssistant';
import { cn } from '@/lib/utils';

interface Message {
  role: 'interviewer' | 'candidate';
  content: string;
}

// Animated score bar component
function ScoreBar({ label, value, color, icon: Icon }: {
  label: string;
  value: number | null;
  color: string;
  icon: React.ElementType;
}) {
  return (
    <div className="space-y-2">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-1.5">
          <Icon size={12} className={color} />
          <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider">{label}</span>
        </div>
        <span className={cn("text-sm font-black tabular-nums", value ? color : 'text-slate-300')}>
          {value ? `${Math.round(value)}` : '--'}
        </span>
      </div>
      <div className="h-2 w-full bg-slate-100 rounded-full overflow-hidden">
        <div
          className={cn("h-full rounded-full transition-all duration-1000 ease-out", {
            'bg-blue-500': color.includes('blue'),
            'bg-emerald-500': color.includes('emerald'),
            'bg-purple-500': color.includes('purple'),
            'bg-orange-500': color.includes('orange'),
          })}
          style={{ width: `${value || 0}%` }}
        />
      </div>
    </div>
  );
}

// Pulsing voice visualizer
function VoiceVisualizer({ isActive }: { isActive: boolean }) {
  return (
    <div className="flex items-center justify-center gap-1 h-8">
      {[1, 2, 3, 4, 5, 6, 7].map((i) => (
        <div
          key={i}
          className={cn(
            "w-1 rounded-full transition-all duration-150",
            isActive ? "bg-primary-500" : "bg-slate-200"
          )}
          style={{
            height: isActive ? `${8 + Math.sin(i * 0.8) * 14 + Math.random() * 10}px` : '8px',
            animation: isActive ? `pulse ${0.4 + i * 0.1}s ease-in-out infinite alternate` : 'none',
          }}
        />
      ))}
    </div>
  );
}

function InterviewContent() {
  const searchParams = useSearchParams();
  const interviewId = searchParams.get('id');
  const router = useRouter();

  const [messages, setMessages] = useState<Message[]>([]);
  const [isProcessing, setIsProcessing] = useState(false);
  const [isCompleted, setIsCompleted] = useState(false);
  const [report, setReport] = useState<any>(null);
  const [elapsedTime, setElapsedTime] = useState(0);
  const [statusMessage, setStatusMessage] = useState('Connecting to interview stream...');
  const [error, setError] = useState<string | null>(null);
  const [processingStage, setProcessingStage] = useState<string | null>(null);
  const [targetRole, setTargetRole] = useState('Software Engineer');
  const [liveScores, setLiveScores] = useState<any>(null);
  const [coveredTopics, setCoveredTopics] = useState<string[]>([]);
  const [isRecording, setIsRecording] = useState(false);
  const [recordingDuration, setRecordingDuration] = useState(0);

  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const audioChunksRef = useRef<Blob[]>([]);
  const socketRef = useRef<WebSocket | null>(null);
  const scrollRef = useRef<HTMLDivElement>(null);
  const initializationRef = useRef(false);
  const recordingTimerRef = useRef<NodeJS.Timeout | null>(null);

  // Restore session
  useEffect(() => {
    try {
      const saved = sessionStorage.getItem('interview-session-state');
      if (!saved) return;
      const parsed = JSON.parse(saved);
      setMessages(parsed.messages || []);
      setLiveScores(parsed.liveScores || null);
      setCoveredTopics(parsed.coveredTopics || []);
      setElapsedTime(parsed.elapsedTime || 0);
      setReport(parsed.report || null);
      setIsCompleted(Boolean(parsed.isCompleted));
    } catch (err) {
      console.warn('Could not restore interview session', err);
    }
  }, []);

  // Persist session
  useEffect(() => {
    if (typeof window === 'undefined') return;
    sessionStorage.setItem('interview-session-state', JSON.stringify({
      messages, liveScores, coveredTopics, elapsedTime, report, isCompleted,
    }));
  }, [messages, liveScores, coveredTopics, elapsedTime, report, isCompleted]);

  // Session timer
  useEffect(() => {
    if (isCompleted) return;
    const interval = setInterval(() => setElapsedTime(prev => prev + 1), 1000);
    return () => clearInterval(interval);
  }, [isCompleted]);

  // Recording duration timer
  useEffect(() => {
    if (isRecording) {
      setRecordingDuration(0);
      recordingTimerRef.current = setInterval(() => setRecordingDuration(d => d + 1), 1000);
    } else {
      if (recordingTimerRef.current) clearInterval(recordingTimerRef.current);
      setRecordingDuration(0);
    }
    return () => { if (recordingTimerRef.current) clearInterval(recordingTimerRef.current); };
  }, [isRecording]);

  const formatTime = (seconds: number) => {
    const m = Math.floor(seconds / 60);
    const s = seconds % 60;
    return `${m}:${s.toString().padStart(2, '0')}`;
  };

  // WebSocket setup
  useEffect(() => {
    if (!interviewId || initializationRef.current) return;
    initializationRef.current = true;
    setTargetRole(localStorage.getItem('selected_role') || 'Software Engineer');
    setStatusMessage('Establishing connection...');

    const token = localStorage.getItem('token');
    const wsUrl = `${process.env.NEXT_PUBLIC_WS_URL || 'ws://localhost:8000'}/api/v1/interviews/${interviewId}/stream?token=${token}`;
    const socket = new WebSocket(wsUrl);
    socketRef.current = socket;

    socket.onopen = () => setStatusMessage('Initializing AI agents...');

    socket.onmessage = async (event) => {
      const data = JSON.parse(event.data);

      if (data.type === 'question') {
        setMessages(prev => {
          const isDuplicate = prev.length > 0 &&
            prev[prev.length - 1].role === 'interviewer' &&
            prev[prev.length - 1].content === data.text;
          if (isDuplicate) return prev;
          return [...prev, { role: 'interviewer', content: data.text }];
        });
        setIsProcessing(false);
        setProcessingStage(null);
        setStatusMessage('');
        if (data.audio) {
          try {
            const blob = await fetch(`data:audio/mp3;base64,${data.audio}`).then(r => r.blob());
            new Audio(URL.createObjectURL(blob)).play();
          } catch (e) { console.error('Audio playback failed', e); }
        }
      } else if (data.type === 'transcript') {
        setMessages(prev => {
          const last = prev[prev.length - 1];
          if (last?.role === 'candidate') return [...prev.slice(0, -1), { role: 'candidate', content: data.text }];
          return [...prev, { role: 'candidate', content: data.text }];
        });
      } else if (data.type === 'processing') {
        setProcessingStage(data.stage);
      } else if (data.type === 'live_scores') {
        setLiveScores(data.scores);
        setCoveredTopics(data.covered_topics);
      } else if (data.type === 'final_report') {
        setIsCompleted(true);
        setReport(data.report);
        socket.close();
      } else if (data.type === 'error') {
        setError(data.message);
        setIsProcessing(false);
        setProcessingStage(null);
      }
    };

    socket.onerror = () => setError('Failed to connect to interview server.');

    return () => {
      if (socket.readyState === WebSocket.OPEN || socket.readyState === WebSocket.CONNECTING) socket.close();
      initializationRef.current = false;
    };
  }, [interviewId]);

  // Auto-scroll
  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: 'smooth' });
  }, [messages, isProcessing]);

  const startRecording = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const recorder = new MediaRecorder(stream);
      mediaRecorderRef.current = recorder;
      audioChunksRef.current = [];

      recorder.ondataavailable = (e) => { if (e.data.size > 0) audioChunksRef.current.push(e.data); };
      recorder.onstop = () => {
        const blob = new Blob(audioChunksRef.current, { type: 'audio/webm' });
        if (socketRef.current?.readyState === WebSocket.OPEN) {
          setIsProcessing(true);
          setProcessingStage('Transcribing your answer...');
          socketRef.current.send(blob);
        }
      };

      recorder.start();
      setIsRecording(true);
    } catch {
      setError('Microphone access denied. Please check your browser settings.');
    }
  };

  const stopRecording = () => {
    if (mediaRecorderRef.current && isRecording) {
      mediaRecorderRef.current.stop();
      setIsRecording(false);
      mediaRecorderRef.current.stream.getTracks().forEach(t => t.stop());
    }
  };

  const toggleRecording = () => isRecording ? stopRecording() : startRecording();

  // Completion screen
  if (isCompleted) {
    return (
      <div className="flex flex-col items-center justify-center min-h-screen bg-slate-50 p-6">
        <div className="max-w-3xl w-full animate-slide-up">
          <Card className="border-none shadow-2xl overflow-hidden rounded-[2.5rem]">
            <CardContent className="p-0">
              <div className="bg-primary-600 p-12 text-center text-white relative overflow-hidden">
                <div className="absolute top-0 right-0 p-8 opacity-10"><Award size={200} /></div>
                <div className="relative z-10">
                  <div className="w-20 h-20 bg-white/20 backdrop-blur-xl rounded-3xl flex items-center justify-center mx-auto mb-6 shadow-xl ring-1 ring-white/30">
                    <Sparkles size={40} className="text-yellow-300" />
                  </div>
                  <h1 className="text-4xl font-black mb-3">Interview Complete!</h1>
                  <p className="text-primary-100 font-medium max-w-md mx-auto leading-relaxed">
                    AI agents have finished analyzing your technical depth and communication skills.
                  </p>
                </div>
              </div>
              <div className="p-12 bg-white">
                <div className="grid grid-cols-1 md:grid-cols-2 gap-8 mb-12">
                  <div className="p-8 bg-slate-50 rounded-3xl border border-slate-100 flex flex-col items-center text-center">
                    <p className="text-xs font-bold text-slate-400 uppercase tracking-widest mb-2">Overall Score</p>
                    <div className="text-6xl font-black text-primary-600 mb-2">{report?.overall_score?.toFixed(1) || '0.0'}%</div>
                    <p className="text-sm font-semibold text-slate-600">Based on industry standards</p>
                  </div>
                  <div className="p-8 bg-slate-50 rounded-3xl border border-slate-100 flex flex-col items-center text-center">
                    <p className="text-xs font-bold text-slate-400 uppercase tracking-widest mb-2">Session Duration</p>
                    <div className="text-6xl font-black text-slate-900 mb-2">{formatTime(elapsedTime)}</div>
                    <p className="text-sm font-semibold text-slate-600">Total interview time</p>
                  </div>
                </div>
                <div className="space-y-4">
                  <Button
                    onClick={() => router.push(`/interview/review?id=${interviewId}`)}
                    className="w-full h-16 rounded-2xl text-xl font-black shadow-xl"
                  >
                    View Full Review & Feedback
                  </Button>
                  <Button
                    variant="outline"
                    onClick={() => router.push('/dashboard')}
                    className="w-full h-16 rounded-2xl text-lg font-bold"
                  >
                    Return to Dashboard
                  </Button>
                </div>
              </div>
            </CardContent>
          </Card>
        </div>
      </div>
    );
  }

  const topicTotal = coveredTopics.length + (liveScores?.remaining_topics_count || 0);
  const topicCoverage = liveScores?.topic_coverage || (topicTotal > 0 ? coveredTopics.length / topicTotal * 100 : 0);

  return (
    <div className="flex flex-col lg:flex-row h-screen bg-slate-50 overflow-hidden font-sans">

      {/* ── Left sidebar ── */}
      <div className="w-full lg:w-96 bg-white border-r border-slate-200 flex flex-col p-8 z-20">
        <div className="flex items-center justify-between mb-10">
          <div className="flex items-center space-x-3">
            <div className="w-10 h-10 bg-primary-600 rounded-xl flex items-center justify-center text-white shadow-lg shadow-primary-200">
              <Bot size={22} />
            </div>
            <h2 className="text-xl font-black text-slate-900 tracking-tight">AI Interview</h2>
          </div>
          <button
            onClick={() => router.push('/dashboard')}
            className="p-2 text-slate-400 hover:text-red-500 hover:bg-red-50 rounded-xl transition-all"
            title="Exit Session"
          >
            <LogOut size={20} />
          </button>
        </div>

        <div className="flex-1 space-y-8 overflow-y-auto">
          {/* Progress */}
          <div className="space-y-3">
            <div className="flex items-center justify-between text-xs font-bold text-slate-400 uppercase tracking-widest px-1">
              <span>Progress</span>
              <span>{Math.round(topicCoverage)}%</span>
            </div>
            <div className="h-3 w-full bg-slate-100 rounded-full overflow-hidden">
              <div
                className="h-full bg-primary-600 transition-all duration-1000 ease-out shadow-[0_0_10px_rgba(37,99,235,0.4)]"
                style={{ width: `${topicCoverage}%` }}
              />
            </div>
            <div className="flex flex-wrap gap-1.5 pt-1">
              {coveredTopics.map((t, i) => (
                <span key={i} className="text-[10px] font-bold px-2 py-0.5 bg-primary-50 text-primary-600 rounded-md border border-primary-100">
                  {t}
                </span>
              ))}
            </div>
          </div>

          {/* Timer + Role */}
          <div className="grid grid-cols-2 gap-3">
            <div className="flex flex-col p-5 bg-slate-50 rounded-2xl border border-slate-100">
              <div className="flex items-center gap-1.5 text-slate-400 mb-2">
                <Timer size={13} />
                <span className="text-[9px] font-black uppercase tracking-widest">Time</span>
              </div>
              <div className="text-2xl font-black text-slate-900 font-mono">{formatTime(elapsedTime)}</div>
            </div>
            <div className="flex flex-col p-5 bg-primary-50 rounded-2xl border border-primary-100">
              <div className="flex items-center gap-1.5 text-primary-400 mb-2">
                <ChevronRight size={13} />
                <span className="text-[9px] font-black uppercase tracking-widest">Role</span>
              </div>
              <div className="text-sm font-bold text-primary-900 leading-tight line-clamp-2">{targetRole}</div>
            </div>
          </div>

          {/* Current topic */}
          <div className="p-5 bg-slate-900 rounded-2xl text-white">
            <div className="flex items-center gap-2 mb-2">
              <Brain size={13} className="text-primary-400" />
              <p className="text-[9px] font-bold text-slate-400 uppercase tracking-widest">Current Topic</p>
            </div>
            <p className="text-sm font-bold">{liveScores?.current_topic || 'Initializing...'}</p>
          </div>

          <VapiAssistant targetRole={targetRole} />
        </div>

        <div className="mt-6">
          <div className="p-4 bg-emerald-50 rounded-2xl border border-emerald-100 flex items-center space-x-3">
            <div className="w-2.5 h-2.5 bg-emerald-500 rounded-full animate-pulse shadow-[0_0_8px_rgba(16,185,129,0.8)]" />
            <span className="text-xs font-bold text-emerald-800">Voice Session Active</span>
          </div>
        </div>
      </div>

      {/* ── Main interview area ── */}
      <div className="flex-1 flex flex-col h-full bg-slate-50 relative overflow-hidden">

        {/* Transcript */}
        <div
          ref={scrollRef}
          className="flex-1 overflow-y-auto px-8 py-10 lg:px-16 space-y-8 scrollbar-hide pb-64"
        >
          {error && (
            <div className="max-w-md mx-auto p-5 bg-red-50 text-red-600 rounded-2xl border border-red-100 flex items-center gap-3 shadow-lg">
              <AlertCircle size={20} className="flex-shrink-0" />
              <p className="text-sm font-bold">{error}</p>
            </div>
          )}

          {statusMessage && !error && messages.length === 0 && (
            <div className="h-full flex flex-col items-center justify-center text-center animate-fade-in pt-20">
              <div className="w-24 h-24 bg-white rounded-[2rem] shadow-xl flex items-center justify-center text-primary-600 mb-8 border border-slate-100 relative">
                <Bot size={44} className="animate-bounce" />
                <div className="absolute inset-0 rounded-[2rem] border-4 border-primary-500 border-t-transparent animate-spin" />
              </div>
              <h3 className="text-2xl font-black text-slate-900 mb-2">Warming up AI agents</h3>
              <p className="text-slate-400 max-w-sm font-medium animate-pulse">{statusMessage}</p>
            </div>
          )}

          {messages.map((msg, i) => (
            <div
              key={i}
              className={cn(
                "flex opacity-0 animate-slide-up [animation-fill-mode:forwards]",
                msg.role === 'candidate' ? 'justify-end' : 'justify-start'
              )}
              style={{ animationDelay: '0.05s' }}
            >
              <div className={cn("flex max-w-[85%] lg:max-w-[68%] group gap-3", msg.role === 'candidate' ? 'flex-row-reverse' : 'flex-row')}>
                <div className={cn(
                  "w-11 h-11 rounded-2xl flex-shrink-0 flex items-center justify-center shadow-sm transition-transform group-hover:scale-105",
                  msg.role === 'candidate' ? 'bg-slate-900 text-white' : 'bg-white text-primary-600 border border-slate-100'
                )}>
                  {msg.role === 'candidate' ? <User size={20} /> : <Bot size={20} />}
                </div>
                <div className={cn(
                  "p-5 rounded-[1.5rem] shadow-sm",
                  msg.role === 'candidate'
                    ? 'bg-primary-600 text-white rounded-tr-none'
                    : 'bg-white text-slate-800 rounded-tl-none border border-slate-100'
                )}>
                  <p className="text-[15px] font-medium leading-relaxed whitespace-pre-wrap">{msg.content}</p>
                  <div className={cn("text-[9px] font-bold uppercase tracking-widest mt-3 opacity-40", msg.role === 'candidate' ? 'text-white' : 'text-slate-400')}>
                    {msg.role === 'candidate' ? 'You' : 'AI Interviewer'}
                  </div>
                </div>
              </div>
            </div>
          ))}

          {isProcessing && (
            <div className="flex justify-start animate-fade-in">
              <div className="flex items-center space-x-3">
                <div className="w-11 h-11 rounded-2xl bg-white flex items-center justify-center shadow-sm border border-slate-100 text-primary-600">
                  <Bot size={20} className="animate-spin" />
                </div>
                <div className="bg-white px-5 py-4 rounded-2xl rounded-tl-none shadow-sm border border-slate-100">
                  <div className="flex items-center gap-2 mb-1">
                    <div className="flex gap-1">
                      {[0, 1, 2].map(i => (
                        <span key={i} className="w-1.5 h-1.5 bg-primary-400 rounded-full animate-bounce" style={{ animationDelay: `${i * 0.15}s` }} />
                      ))}
                    </div>
                    <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider">Analyzing...</span>
                  </div>
                  {processingStage && <p className="text-[11px] text-primary-500 font-medium animate-pulse">{processingStage}</p>}
                </div>
              </div>
            </div>
          )}
        </div>

        {/* ── Voice action bar ── */}
        <div className="absolute bottom-0 w-full p-8 lg:px-16 z-30">
          <div className="max-w-2xl mx-auto">
            <div className="bg-white rounded-[2rem] shadow-2xl border border-slate-100 p-6">

              {/* Voice visualizer */}
              <div className="mb-5">
                <VoiceVisualizer isActive={isRecording} />
              </div>

              {/* Status text */}
              <div className="text-center mb-5">
                {isRecording ? (
                  <div className="flex items-center justify-center gap-2">
                    <div className="w-2 h-2 bg-red-500 rounded-full animate-pulse" />
                    <span className="text-sm font-bold text-red-600">Recording — {formatTime(recordingDuration)}</span>
                  </div>
                ) : isProcessing ? (
                  <span className="text-sm font-bold text-primary-600 animate-pulse">{processingStage || 'Processing...'}</span>
                ) : messages.length > 0 ? (
                  <span className="text-sm font-medium text-slate-400">Press and hold to answer</span>
                ) : (
                  <span className="text-sm font-medium text-slate-300">Waiting for first question...</span>
                )}
              </div>

              {/* Big mic button */}
              <div className="flex items-center justify-center gap-6">
                <button
                  onClick={toggleRecording}
                  disabled={isProcessing || isCompleted}
                  className={cn(
                    "w-20 h-20 rounded-full flex items-center justify-center transition-all duration-300 shadow-lg active:scale-95 disabled:opacity-40 disabled:cursor-not-allowed",
                    isRecording
                      ? "bg-red-500 shadow-red-200 ring-8 ring-red-100 scale-110"
                      : "bg-primary-600 shadow-primary-200 hover:bg-primary-700 hover:scale-105"
                  )}
                >
                  {isRecording ? (
                    <MicOff size={32} className="text-white" />
                  ) : (
                    <Mic size={32} className="text-white" />
                  )}
                </button>
              </div>

              <p className="text-center text-[10px] font-bold text-slate-300 uppercase tracking-[0.2em] mt-5">
                {isRecording ? "Tap to stop and submit" : "Tap mic to start speaking"}
              </p>
            </div>
          </div>
        </div>
      </div>

      {/* ── Right sidebar — Live analytics ── */}
      <div className="hidden xl:flex w-80 bg-white border-l border-slate-200 flex-col p-6 overflow-y-auto">
        <h3 className="text-xs font-black text-slate-900 uppercase tracking-widest mb-6 flex items-center gap-2">
          <Radio size={14} className="text-red-500 animate-pulse" />
          Live Analytics
        </h3>

        <div className="space-y-6">
          {/* Score bars */}
          <div className="p-5 bg-slate-50 rounded-2xl border border-slate-100 space-y-4">
            <ScoreBar label="Technical" value={liveScores?.technical_score} color="text-blue-600" icon={Zap} />
            <ScoreBar label="Communication" value={liveScores?.communication_score} color="text-emerald-600" icon={MessageCircle} />
            <ScoreBar label="Confidence" value={liveScores?.confidence_score} color="text-purple-600" icon={TrendingUp} />
            <ScoreBar label="Depth" value={liveScores?.knowledge_depth} color="text-orange-600" icon={Brain} />
          </div>

          {/* Topic coverage */}
          <div className="p-5 bg-slate-50 rounded-2xl border border-slate-100">
            <div className="flex justify-between items-end mb-3">
              <div>
                <p className="text-[10px] font-bold text-slate-400 uppercase tracking-tight">Coverage</p>
                <p className="text-2xl font-black text-slate-900">{Math.round(topicCoverage)}%</p>
              </div>
              <p className="text-[10px] font-bold text-primary-600 bg-primary-50 px-2 py-1 rounded-lg">
                {coveredTopics.length}/{coveredTopics.length + (liveScores?.remaining_topics_count || 0)}
              </p>
            </div>
            <div className="h-2 w-full bg-slate-200 rounded-full overflow-hidden">
              <div className="h-full bg-primary-600 transition-all duration-1000" style={{ width: `${topicCoverage}%` }} />
            </div>
          </div>

          {/* Strengths */}
          <div>
            <p className="text-[10px] font-bold text-slate-400 uppercase tracking-tight mb-3">Strengths</p>
            <div className="flex flex-wrap gap-2">
              {liveScores?.strengths?.length > 0
                ? liveScores.strengths.map((s: string, i: number) => (
                  <span key={i} className="px-2.5 py-1 bg-emerald-50 text-emerald-700 text-[11px] font-bold rounded-lg border border-emerald-100">
                    {s}
                  </span>
                ))
                : <p className="text-[11px] text-slate-300 italic">Analyzing...</p>
              }
            </div>
          </div>

          {/* Improvements */}
          <div>
            <p className="text-[10px] font-bold text-slate-400 uppercase tracking-tight mb-3">Improvements</p>
            <div className="flex flex-wrap gap-2">
              {liveScores?.weaknesses?.length > 0
                ? liveScores.weaknesses.map((w: string, i: number) => (
                  <span key={i} className="px-2.5 py-1 bg-amber-50 text-amber-700 text-[11px] font-bold rounded-lg border border-amber-100">
                    {w}
                  </span>
                ))
                : <p className="text-[11px] text-slate-300 italic">Waiting for data...</p>
              }
            </div>
          </div>

          {/* Questions answered */}
          <div className="p-4 bg-slate-900 rounded-2xl text-white text-center">
            <p className="text-[10px] font-bold text-slate-400 uppercase tracking-tight mb-1">Questions Answered</p>
            <p className="text-3xl font-black">{messages.filter(m => m.role === 'candidate').length}</p>
            <p className="text-[10px] text-slate-500 mt-1">of 5 total</p>
          </div>
        </div>
      </div>

    </div>
  );
}

export default function InterviewPage() {
  return (
    <Suspense fallback={
      <div className="flex items-center justify-center min-h-screen bg-slate-50">
        <div className="flex flex-col items-center">
          <Loader2 className="w-12 h-12 text-primary-600 animate-spin mb-4" />
          <p className="text-sm font-bold text-slate-400 uppercase tracking-widest">Loading Session...</p>
        </div>
      </div>
    }>
      <InterviewContent />
    </Suspense>
  );
}
