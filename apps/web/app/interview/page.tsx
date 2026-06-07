'use client';

import { useState, useEffect, useRef, Suspense } from 'react';
import { useSearchParams, useRouter } from 'next/navigation';
import { 
  Send, 
  User, 
  Bot, 
  Loader2, 
  Award, 
  LogOut, 
  Mic, 
  MicOff, 
  Volume2, 
  Timer,
  ChevronRight,
  Sparkles,
  Info,
  Clock,
  AlertCircle
} from 'lucide-react';
import { Button } from '@/components/ui/Button';
import { Card, CardContent } from '@/components/ui/Card';
import { VapiAssistant } from '@/components/voice/VapiAssistant';
import { cn } from '@/lib/utils';

interface Message {
  role: 'interviewer' | 'candidate';
  content: string;
}

function InterviewContent() {
  const searchParams = useSearchParams();
  const interviewId = searchParams.get('id');
  const router = useRouter();
  
  const [messages, setMessages] = useState<Message[]>([]);
  const [currentQuestion, setCurrentQuestion] = useState('');
  const [answer, setAnswer] = useState('');
  const [isProcessing, setIsProcessing] = useState(false);
  const [isCompleted, setIsCompleted] = useState(false);
  const [report, setReport] = useState<any>(null);
  const [elapsedTime, setElapsedTime] = useState(0);
  const [statusMessage, setStatusMessage] = useState('Connecting to interview stream...');
  const [error, setError] = useState<string | null>(null);
  const [processingStage, setProcessingStage] = useState<string | null>(null);
  const [targetRole, setTargetRole] = useState('Software Engineer');
  
  // Real-Time Dashboard State
  const [liveScores, setLiveScores] = useState<any>(null);
  const [coveredTopics, setCoveredTopics] = useState<string[]>([]);
  
  // Voice State
  const [isRecording, setIsRecording] = useState(false);
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const audioChunksRef = useRef<Blob[]>([]);

  const socketRef = useRef<WebSocket | null>(null);
  const scrollRef = useRef<HTMLDivElement>(null);
  const initializationRef = useRef(false);

  // Timer
  useEffect(() => {
    if (isCompleted) return;
    const interval = setInterval(() => {
      setElapsedTime(prev => prev + 1);
    }, 1000);
    return () => clearInterval(interval);
  }, [isCompleted]);

  const formatTime = (seconds: number) => {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins}:${secs.toString().padStart(2, '0')}`;
  };

  useEffect(() => {
    if (!interviewId || initializationRef.current) return;
    initializationRef.current = true;
    setTargetRole(localStorage.getItem('selected_role') || 'Software Engineer');

    setStatusMessage('Establishing WebSocket connection...');
    const token = localStorage.getItem('token');
    const wsUrl = `${process.env.NEXT_PUBLIC_WS_URL || 'ws://localhost:8000'}/api/v1/interviews/${interviewId}/stream?token=${token}`;
    const socket = new WebSocket(wsUrl);
    socketRef.current = socket;

    socket.onopen = () => {
      console.log('WebSocket: Connected');
      setStatusMessage('Initializing AI Agents and generating first question...');
    };
    
    socket.onmessage = async (event) => {
      const data = JSON.parse(event.data);
      console.log('WebSocket: Message received', data.type);
      
      if (data.type === 'question') {
        setCurrentQuestion(data.text);
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
            const audioBlob = await fetch(`data:audio/mp3;base64,${data.audio}`).then(res => res.blob());
            const audioUrl = URL.createObjectURL(audioBlob);
            const audio = new Audio(audioUrl);
            audio.play();
          } catch (e) {
            console.error("Audio playback failed", e);
          }
        }
      } 
      else if (data.type === 'transcript') {
        setMessages(prev => {
          const last = prev[prev.length - 1];
          if (last && last.role === 'candidate') {
            return [...prev.slice(0, -1), { role: 'candidate', content: data.text }];
          }
          return [...prev, { role: 'candidate', content: data.text }];
        });
      }
      else if (data.type === 'processing') {
        setProcessingStage(data.stage);
      }
      else if (data.type === 'final_report') {
        setIsCompleted(true);
        setReport(data.report);
        socket.close();
      } else if (data.type === 'live_scores') {
        setLiveScores(data.scores);
        setCoveredTopics(data.covered_topics);
      } else if (data.type === 'error') {
        console.error('Interview Error:', data.message);
        setError(data.message);
        setIsProcessing(false);
        setProcessingStage(null);
      }
    };

    socket.onerror = (err) => {
      console.error('WebSocket Error:', err);
      setError('Failed to connect to the interview server.');
    };

    return () => {
      console.log('WebSocket: Cleaning up');
      if (socket.readyState === WebSocket.OPEN || socket.readyState === WebSocket.CONNECTING) {
        socket.close();
      }
      initializationRef.current = false;
    };
  }, [interviewId]);

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTo({ top: scrollRef.current.scrollHeight, behavior: 'smooth' });
    }
  }, [messages, isProcessing]);

  // --- Voice Controls ---
  const startRecording = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const mediaRecorder = new MediaRecorder(stream);
      mediaRecorderRef.current = mediaRecorder;
      audioChunksRef.current = [];

      mediaRecorder.ondataavailable = (event) => {
        if (event.data.size > 0) {
          audioChunksRef.current.push(event.data);
        }
      };

      mediaRecorder.onstop = () => {
        const audioBlob = new Blob(audioChunksRef.current, { type: 'audio/webm' });
        if (socketRef.current?.readyState === WebSocket.OPEN) {
          setIsProcessing(true);
          setProcessingStage('Processing audio...');
          socketRef.current.send(audioBlob);
        }
      };

      mediaRecorder.start();
      setIsRecording(true);
    } catch (err) {
      console.error("Microphone access denied:", err);
      setError("Microphone access denied. Please check your browser settings.");
    }
  };

  const stopRecording = () => {
    if (mediaRecorderRef.current && isRecording) {
      mediaRecorderRef.current.stop();
      setIsRecording(false);
      mediaRecorderRef.current.stream.getTracks().forEach(track => track.stop());
    }
  };

  const handleSubmitAnswer = () => {
    if (!answer.trim() || !socketRef.current || isProcessing) return;
    setIsProcessing(true);
    setProcessingStage('Sending response...');
    setMessages(prev => [...prev, { role: 'candidate', content: answer }]);
    
    socketRef.current.send(JSON.stringify({
      type: 'answer',
      text: answer
    }));
    
    setAnswer('');
  };

  if (isCompleted) {
    return (
      <div className="flex flex-col items-center justify-center min-h-screen bg-slate-50 p-6">
        <div className="max-w-3xl w-full animate-slide-up">
          <Card className="border-none shadow-2xl overflow-hidden rounded-[2.5rem]">
            <CardContent className="p-0">
              <div className="bg-primary-600 p-12 text-center text-white relative overflow-hidden">
                <div className="absolute top-0 right-0 p-8 opacity-10">
                  <Award size={200} />
                </div>
                <div className="relative z-10">
                  <div className="w-20 h-20 bg-white/20 backdrop-blur-xl rounded-3xl flex items-center justify-center mx-auto mb-6 shadow-xl ring-1 ring-white/30">
                    <Sparkles size={40} className="text-yellow-300" />
                  </div>
                  <h1 className="text-4xl font-black mb-3">Interview Evaluated!</h1>
                  <p className="text-primary-100 font-medium max-w-md mx-auto leading-relaxed">
                    Great session! Our AI agents have finished analyzing your technical depth and communication skills.
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
                    <p className="text-xs font-bold text-slate-400 uppercase tracking-widest mb-2">Completion Time</p>
                    <div className="text-6xl font-black text-slate-900 mb-2">{formatTime(elapsedTime)}</div>
                    <p className="text-sm font-semibold text-slate-600">Duration of session</p>
                  </div>
                </div>

                <div className="space-y-4">
                  <Button 
                    onClick={() => router.push('/dashboard/analytics')}
                    className="w-full h-16 rounded-2xl text-xl font-black shadow-xl"
                  >
                    Deep-Dive Analytics
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

  return (
    <div className="flex flex-col lg:flex-row h-screen bg-slate-50 overflow-hidden font-sans">
      {/* Left Sidebar - Meta Info */}
      <div className="w-full lg:w-96 bg-white border-r border-slate-200 flex flex-col p-8 z-20">
        <div className="flex items-center justify-between mb-12">
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
        
        <div className="flex-1 space-y-10">
          <div className="space-y-4">
            <div className="flex items-center justify-between text-xs font-bold text-slate-400 uppercase tracking-widest mb-1 px-1">
              <span>Interview Progress</span>
              <span>{liveScores?.topic_coverage ? `${Math.round(liveScores.topic_coverage)}%` : `${Math.min(messages.length * 10, 100)}%`}</span>
            </div>
            <div className="h-3 w-full bg-slate-100 rounded-full overflow-hidden">
              <div 
                className="h-full bg-primary-600 transition-all duration-1000 ease-out shadow-[0_0_10px_rgba(37,99,235,0.5)]" 
                style={{ width: `${liveScores?.topic_coverage || Math.min(messages.length * 10, 100)}%` }}
              ></div>
            </div>
          </div>

          <div className="space-y-6">
            <div className="flex flex-col p-6 bg-slate-50 rounded-3xl border border-slate-100 relative overflow-hidden group">
              <div className="absolute top-0 right-0 p-4 opacity-5 group-hover:scale-110 transition-transform">
                <Clock size={80} />
              </div>
              <div className="flex items-center space-x-2 text-slate-400 mb-2">
                <Timer size={16} />
                <span className="text-[10px] font-black uppercase tracking-widest">Session Time</span>
              </div>
              <div className="text-4xl font-black text-slate-900 font-mono tracking-tighter">
                {formatTime(elapsedTime)}
              </div>
            </div>

            <div className="flex flex-col p-6 bg-primary-50 rounded-3xl border border-primary-100 relative overflow-hidden group">
              <div className="absolute top-0 right-0 p-4 opacity-5 group-hover:scale-110 transition-transform">
                <Info size={80} />
              </div>
              <div className="flex items-center space-x-2 text-primary-400 mb-2">
                <ChevronRight size={16} />
                <span className="text-[10px] font-black uppercase tracking-widest">Target Role</span>
              </div>
              <div className="text-lg font-bold text-primary-900 leading-tight">
                {targetRole}
              </div>
            </div>
          </div>

          <VapiAssistant targetRole={targetRole} />
        </div>

        <div className="mt-auto">
          <div className="p-5 bg-emerald-50 rounded-2xl border border-emerald-100 flex items-center space-x-4">
            <div className="w-3 h-3 bg-emerald-500 rounded-full animate-pulse shadow-[0_0_8px_rgba(16,185,129,0.8)]"></div>
            <span className="text-xs font-bold text-emerald-800">Connection Secured</span>
          </div>
        </div>
      </div>

      {/* Main Interview Area */}
      <div className="flex-1 flex flex-col h-full bg-slate-50 relative">
        {/* Messages / Transcript Panel */}
        <div 
          ref={scrollRef}
          className="flex-1 overflow-y-auto px-8 py-12 lg:px-20 space-y-10 scrollbar-hide pb-40"
        >
          {error && (
            <div className="max-w-md mx-auto p-6 bg-red-50 text-red-600 rounded-3xl border border-red-100 flex items-center gap-4 animate-shake shadow-xl relative z-50">
              <AlertCircle size={24} className="flex-shrink-0" />
              <div className="text-sm font-bold">{error}</div>
            </div>
          )}

          {statusMessage && !error && messages.length === 0 && (
            <div className="h-full flex flex-col items-center justify-center text-center animate-fade-in">
              <div className="w-24 h-24 bg-white rounded-[2.5rem] shadow-xl flex items-center justify-center text-primary-600 mb-8 border border-slate-100 relative">
                <Bot size={48} className="animate-bounce" />
                <div className="absolute inset-0 rounded-[2.5rem] border-4 border-primary-500 border-t-transparent animate-spin"></div>
              </div>
              <h3 className="text-2xl font-black text-slate-900 mb-2 tracking-tight">Buffering AI Session</h3>
              <p className="text-slate-400 max-w-sm font-medium animate-pulse">{statusMessage}</p>
            </div>
          )}

          {messages.length === 0 && !isProcessing && !statusMessage && !error && (
            <div className="h-full flex flex-col items-center justify-center text-center animate-fade-in">
              <div className="w-24 h-24 bg-white rounded-[2.5rem] shadow-xl flex items-center justify-center text-primary-600 mb-8 border border-slate-100">
                <Bot size={48} />
              </div>
              <h3 className="text-2xl font-black text-slate-900 mb-2 tracking-tight">Ready to Begin</h3>
              <p className="text-slate-400 max-w-sm font-medium">Please wait a moment while the interviewer initializes.</p>
            </div>
          )}

          {messages.map((msg, i) => (
            <div 
              key={i}
              className={cn(
                "flex opacity-0 animate-slide-up [animation-fill-mode:forwards]",
                msg.role === 'candidate' ? 'justify-end' : 'justify-start'
              )}
              style={{ animationDelay: '0.1s' }}
            >
              <div className={cn(
                "flex max-w-[85%] lg:max-w-[70%] group gap-4",
                msg.role === 'candidate' ? 'flex-row-reverse' : 'flex-row'
              )}>
                <div className={cn(
                  "w-12 h-12 rounded-2xl flex-shrink-0 flex items-center justify-center shadow-md transition-transform group-hover:scale-110",
                  msg.role === 'candidate' 
                    ? 'bg-slate-900 text-white shadow-slate-200' 
                    : 'bg-white text-primary-600 shadow-slate-200 border border-slate-100'
                )}>
                  {msg.role === 'candidate' ? <User size={24} /> : <Bot size={24} />}
                </div>
                <div className={cn(
                  "p-6 rounded-[2rem] shadow-sm relative group-hover:shadow-md transition-all duration-300",
                  msg.role === 'candidate' 
                    ? 'bg-primary-600 text-white rounded-tr-none shadow-primary-100' 
                    : 'bg-white text-slate-800 rounded-tl-none shadow-slate-200 border border-slate-100'
                )}>
                  <p className="text-[15px] font-medium leading-relaxed whitespace-pre-wrap">{msg.content}</p>
                  <div className={cn(
                    "text-[9px] font-bold uppercase tracking-widest mt-4 opacity-40",
                    msg.role === 'candidate' ? 'text-white' : 'text-slate-400'
                  )}>
                    {msg.role === 'candidate' ? 'Me' : 'Interviewer'}
                  </div>
                </div>
              </div>
            </div>
          ))}

          {isProcessing && (
            <div className="flex justify-start animate-fade-in">
              <div className="flex items-center space-x-4">
                <div className="w-12 h-12 rounded-2xl bg-white flex items-center justify-center shadow-md border border-slate-100 text-primary-600">
                  <Bot size={24} className="animate-spin" />
                </div>
                <div className="bg-white px-6 py-4 rounded-3xl rounded-tl-none shadow-sm border border-slate-100 flex flex-col gap-1">
                  <div className="flex items-center gap-3">
                    <div className="flex gap-1">
                      <span className="w-2 h-2 bg-primary-200 rounded-full animate-bounce [animation-delay:-0.3s]"></span>
                      <span className="w-2 h-2 bg-primary-400 rounded-full animate-bounce [animation-delay:-0.15s]"></span>
                      <span className="w-2 h-2 bg-primary-600 rounded-full animate-bounce"></span>
                    </div>
                    <span className="text-xs font-bold text-slate-400 uppercase tracking-widest">AI is working...</span>
                  </div>
                  {processingStage && (
                    <p className="text-[11px] font-medium text-primary-500 animate-pulse">{processingStage}</p>
                  )}
                </div>
              </div>
            </div>
          )}
        </div>

        {/* Immersive Action Bar */}
        <div className="absolute bottom-0 w-full p-8 lg:p-12 z-30 pointer-events-none">
          <div className="max-w-5xl mx-auto flex items-end gap-4 pointer-events-auto">
            
            {/* Input Card */}
            <Card className="flex-1 border-none shadow-2xl rounded-[2.5rem] overflow-hidden p-2 bg-white ring-1 ring-slate-100">
              <div className="flex items-end gap-2 p-1">
                {/* Voice Toggle */}
                <button
                  onClick={isRecording ? stopRecording : startRecording}
                  className={cn(
                    "w-16 h-16 rounded-[1.8rem] text-white transition-all duration-300 flex items-center justify-center flex-shrink-0 active:scale-90",
                    isRecording 
                      ? 'bg-red-500 animate-pulse ring-8 ring-red-50' 
                      : 'bg-slate-900 hover:bg-slate-800'
                  )}
                >
                  {isRecording ? <MicOff size={28} /> : <Mic size={28} />}
                </button>

                <div className="flex-1 relative">
                  <textarea 
                    value={answer} 
                    onChange={(e) => setAnswer(e.target.value)} 
                    placeholder={isRecording ? "Listening to your answer..." : "Type your technical response here..."} 
                    disabled={isProcessing || isCompleted || isRecording} 
                    className="w-full px-6 py-5 bg-transparent border-none text-slate-900 font-semibold text-[15px] placeholder:text-slate-300 outline-none resize-none min-h-[64px] max-h-40 scrollbar-hide" 
                    onKeyDown={(e) => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); handleSubmitAnswer(); } }} 
                  />
                </div>

                <Button 
                  onClick={handleSubmitAnswer} 
                  disabled={!answer.trim() || isProcessing || isCompleted || isRecording} 
                  className="w-16 h-16 rounded-[1.8rem] p-0 flex items-center justify-center flex-shrink-0"
                >
                  <Send size={24} />
                </Button>
              </div>
            </Card>

            {/* Quick Actions / Tips */}
            <div className="hidden xl:flex flex-col gap-3 pb-2 w-48">
              <div className="p-4 bg-white/80 backdrop-blur-md border border-slate-100 rounded-2xl shadow-sm text-center">
                <Volume2 className="w-5 h-5 mx-auto text-primary-500 mb-1" />
                <p className="text-[10px] font-black text-slate-400 uppercase tracking-tighter">Audio Playback Active</p>
              </div>
            </div>
          </div>
          
          <div className="max-w-5xl mx-auto flex justify-center mt-6">
            <p className="text-[10px] font-bold text-slate-400 uppercase tracking-[0.2em]">
              {isRecording ? "Capturing voice - Click mic to finish" : "Pro-tip: Focus on tradeoffs and architectural patterns"}
            </p>
          </div>
        </div>
      </div>

      {/* Right Sidebar - Analytics Panel */}
      <div className="hidden xl:flex w-80 bg-white border-l border-slate-200 flex-col p-6 overflow-y-auto">
        <h3 className="text-sm font-black text-slate-900 uppercase tracking-widest mb-6 flex items-center gap-2">
          <Sparkles size={16} className="text-primary-600" />
          Live Analytics
        </h3>

        <div className="space-y-6">
          {/* Real-time Scores */}
          <div className="grid grid-cols-2 gap-3">
            {[
              { label: 'Technical', value: liveScores?.technical_score, color: 'text-blue-600', bg: 'bg-blue-50' },
              { label: 'Comm.', value: liveScores?.communication_score, color: 'text-emerald-600', bg: 'bg-emerald-50' },
              { label: 'Confidence', value: liveScores?.confidence_score, color: 'text-purple-600', bg: 'bg-purple-50' },
              { label: 'Depth', value: liveScores?.knowledge_depth, color: 'text-orange-600', bg: 'bg-orange-50' },
            ].map((stat, i) => (
              <div key={i} className={cn("p-4 rounded-2xl border border-transparent transition-all", stat.bg)}>
                <p className="text-[10px] font-bold text-slate-400 uppercase tracking-tight mb-1">{stat.label}</p>
                <p className={cn("text-xl font-black", stat.color)}>{stat.value ? `${stat.value.toFixed(0)}%` : '--'}</p>
              </div>
            ))}
          </div>

          {/* Topic Coverage */}
          <div className="p-5 bg-slate-50 rounded-2xl border border-slate-100">
            <div className="flex justify-between items-end mb-3">
              <div>
                <p className="text-[10px] font-bold text-slate-400 uppercase tracking-tight">Topic Coverage</p>
                <p className="text-lg font-black text-slate-900">{liveScores?.topic_coverage?.toFixed(0) || 0}%</p>
              </div>
              <p className="text-[10px] font-bold text-primary-600 bg-primary-50 px-2 py-1 rounded-md">
                {coveredTopics.length} / {coveredTopics.length + (liveScores?.remaining_topics_count || 0)}
              </p>
            </div>
            <div className="h-2 w-full bg-slate-200 rounded-full overflow-hidden">
              <div 
                className="h-full bg-primary-600 transition-all duration-1000" 
                style={{ width: `${liveScores?.topic_coverage || 0}%` }}
              ></div>
            </div>
          </div>

          {/* Current Topic */}
          <div className="p-5 bg-slate-900 rounded-2xl text-white shadow-xl">
            <p className="text-[10px] font-bold text-slate-400 uppercase tracking-tight mb-2">Current Topic</p>
            <p className="text-sm font-bold">{liveScores?.current_topic || 'Initializing...'}</p>
          </div>

          {/* Strengths & Weaknesses */}
          <div className="space-y-4">
            <div>
              <p className="text-[10px] font-bold text-slate-400 uppercase tracking-tight mb-3 px-1">Discovered Strengths</p>
              <div className="flex flex-wrap gap-2">
                {liveScores?.strengths?.map((s: string, i: number) => (
                  <span key={i} className="px-3 py-1.5 bg-emerald-50 text-emerald-700 text-[11px] font-bold rounded-lg border border-emerald-100 animate-fade-in">
                    {s}
                  </span>
                )) || <p className="text-[11px] text-slate-300 italic px-1">Analyzing first response...</p>}
              </div>
            </div>

            <div>
              <p className="text-[10px] font-bold text-slate-400 uppercase tracking-tight mb-3 px-1">Areas for Improvement</p>
              <div className="flex flex-wrap gap-2">
                {liveScores?.weaknesses?.map((w: string, i: number) => (
                  <span key={i} className="px-3 py-1.5 bg-amber-50 text-amber-700 text-[11px] font-bold rounded-lg border border-amber-100 animate-fade-in">
                    {w}
                  </span>
                )) || <p className="text-[11px] text-slate-300 italic px-1">Waiting for data...</p>}
              </div>
            </div>
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
