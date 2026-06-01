import React from 'react';
import Link from 'next/link';
import { 
  Bot, 
  Mic, 
  ShieldCheck, 
  BarChart3, 
  ArrowRight,
  Cpu,
  FileText,
  Upload,
  MessageSquareText,
  LineChart
} from 'lucide-react';
import { Button } from '@/components/ui/Button';

export default function Home() {
  return (
    <div className="flex flex-col min-h-screen bg-white dark:bg-slate-950">
      {/* Navigation */}
      <header className="fixed top-0 w-full z-50 bg-white/90 backdrop-blur-md border-b border-slate-100 dark:bg-slate-950/90 dark:border-slate-800">
        <div className="max-w-7xl mx-auto px-6 h-20 flex items-center justify-between">
          <div className="flex items-center space-x-3">
            <div className="w-10 h-10 bg-primary-600 rounded-xl flex items-center justify-center text-white shadow-lg shadow-primary-200">
              <Bot size={24} />
            </div>
            <span className="text-xl font-bold text-slate-900 tracking-tight dark:text-white">AI Interview</span>
          </div>
          
          <nav className="hidden md:flex items-center space-x-8">
            <a href="#features" className="text-sm font-medium text-slate-600 hover:text-primary-600 transition-colors dark:text-slate-300 dark:hover:text-primary-300">Features</a>
            <a href="#how-it-works" className="text-sm font-medium text-slate-600 hover:text-primary-600 transition-colors dark:text-slate-300 dark:hover:text-primary-300">How it Works</a>
            <Link href="/login" className="text-sm font-bold text-slate-700 hover:text-primary-600 transition-colors dark:text-white dark:hover:text-primary-300">Login</Link>
            <Link href="/signup">
              <Button size="sm">Get Started</Button>
            </Link>
          </nav>

          <div className="flex md:hidden items-center gap-3">
            <a href="#how-it-works" className="text-sm font-bold text-slate-700 dark:text-white">How</a>
            <Link href="/login" className="text-sm font-bold text-slate-700 dark:text-white">Login</Link>
            <Link href="/signup">
              <Button size="sm">Start</Button>
            </Link>
          </div>
        </div>
      </header>

      <main>
        {/* Hero Section */}
        <section className="pt-32 pb-20 px-6 overflow-hidden">
          <div className="max-w-7xl mx-auto flex flex-col lg:flex-row items-center gap-16">
            <div className="flex-1 text-center lg:text-left animate-slide-up">
              <div className="inline-flex items-center px-4 py-2 rounded-full bg-primary-50 border border-primary-100 text-primary-700 text-sm font-bold mb-6">
                <Cpu size={16} className="mr-2" />
                Powered by Next-Gen AI
              </div>
              <h1 className="text-5xl lg:text-7xl font-black text-slate-900 leading-[1.1] mb-8">
                Master Your Next <br />
                <span className="text-primary-600 italic">Technical Interview</span>
              </h1>
              <p className="text-xl text-slate-600 mb-10 max-w-2xl leading-relaxed">
                Experience the world's most realistic AI-powered technical interviews. 
                Get real-time feedback, deep performance analytics, and professional 
                assessment reports.
              </p>
              <div className="flex flex-col sm:flex-row items-center justify-center lg:justify-start gap-4">
                <Link href="/upload" className="w-full sm:w-auto">
                  <Button size="lg" className="w-full group">
                    Start Free Interview
                    <ArrowRight className="ml-2 transition-transform group-hover:translate-x-1" size={20} />
                  </Button>
                </Link>
                <Link href="/dashboard" className="w-full sm:w-auto">
                  <Button variant="outline" size="lg" className="w-full">View Demo Dashboard</Button>
                </Link>
              </div>
              
              <div className="mt-12 flex items-center justify-center lg:justify-start space-x-8">
                <div className="flex -space-x-3">
                  {[1,2,3,4].map(i => (
                    <div key={i} className="w-10 h-10 rounded-full border-2 border-white bg-slate-200"></div>
                  ))}
                </div>
                <div className="text-sm text-slate-500 font-medium">
                  Trusted by <span className="text-slate-900 font-bold">2,000+</span> software engineers
                </div>
              </div>
            </div>

            <div className="flex-1 relative animate-fade-in">
              <div className="relative z-10 bg-white rounded-3xl shadow-2xl border border-slate-100 overflow-hidden aspect-[4/3] lg:aspect-auto">
                {/* Mock UI Element */}
                <div className="absolute inset-0 bg-gradient-to-br from-primary-50 to-white">
                  <div className="p-8 h-full flex flex-col">
                    <div className="flex items-center space-x-4 mb-10">
                      <div className="w-12 h-12 bg-primary-600 rounded-full flex items-center justify-center text-white shadow-lg shadow-primary-200">
                        <Bot size={28} />
                      </div>
                      <div>
                        <div className="h-4 w-48 bg-slate-200 rounded-full mb-2 animate-pulse"></div>
                        <div className="h-3 w-32 bg-slate-100 rounded-full animate-pulse delay-75"></div>
                      </div>
                    </div>
                    <div className="space-y-6">
                      <div className="bg-white p-6 rounded-2xl shadow-sm border border-slate-100 max-w-[80%]">
                        <div className="h-3 w-full bg-slate-50 rounded-full mb-3"></div>
                        <div className="h-3 w-5/6 bg-slate-50 rounded-full mb-3"></div>
                        <div className="h-3 w-4/6 bg-slate-50 rounded-full"></div>
                      </div>
                      <div className="bg-primary-600 p-6 rounded-2xl shadow-md text-white max-w-[80%] self-end ml-auto">
                        <div className="h-3 w-full bg-primary-500/50 rounded-full mb-3"></div>
                        <div className="h-3 w-3/4 bg-primary-500/50 rounded-full"></div>
                      </div>
                    </div>
                    
                    <div className="mt-auto pt-10 grid grid-cols-2 gap-4">
                      <div className="p-4 bg-green-50 rounded-xl border border-green-100 flex items-center space-x-3">
                        <ShieldCheck className="text-green-600" size={20} />
                        <div className="text-xs font-bold text-green-800">85% Correctness</div>
                      </div>
                      <div className="p-4 bg-blue-50 rounded-xl border border-blue-100 flex items-center space-x-3">
                        <BarChart3 className="text-blue-600" size={20} />
                        <div className="text-xs font-bold text-blue-800">Deep Technical Score</div>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
              {/* Decorative elements */}
              <div className="absolute -top-10 -right-10 w-64 h-64 bg-primary-200/30 blur-3xl rounded-full -z-10 animate-pulse-slow"></div>
              <div className="absolute -bottom-10 -left-10 w-64 h-64 bg-blue-200/30 blur-3xl rounded-full -z-10 animate-pulse-slow delay-1000"></div>
            </div>
          </div>
        </section>

        {/* Features Grid */}
        <section id="features" className="py-24 bg-slate-50 dark:bg-slate-950">
          <div className="max-w-7xl mx-auto px-6">
            <div className="text-center mb-20">
              <h2 className="text-4xl font-black text-slate-900 mb-4 tracking-tight">Built for Serious Career Growth</h2>
              <p className="text-lg text-slate-500 max-w-2xl mx-auto leading-relaxed">
                Everything you need to practice, evaluate, and excel in modern technical recruitment pipelines.
              </p>
            </div>
            
            <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
              {[
                { 
                  title: 'Real-time Voice & Audio', 
                  desc: 'Talk naturally to the AI. Whisper-powered STT ensures your technical terms are understood perfectly.',
                  icon: Mic,
                  color: 'text-blue-600',
                  bg: 'bg-blue-50'
                },
                { 
                  title: 'Production-Grade Evaluation', 
                  desc: 'Multi-agent analysis for architectural depth, edge-case awareness, and technical tradeoffs.',
                  icon: ShieldCheck,
                  color: 'text-purple-600',
                  bg: 'bg-purple-50'
                },
                { 
                  title: 'Deep Analytics Dashboard', 
                  desc: 'Track your growth across sessions. See where you excel and where you need more practice.',
                  icon: BarChart3,
                  color: 'text-orange-600',
                  bg: 'bg-orange-50'
                },
                { 
                  title: 'Instant PDF Reports', 
                  desc: 'Generate professional reports with strengths, weaknesses, and hiring recommendations.',
                  icon: FileText,
                  color: 'text-emerald-600',
                  bg: 'bg-emerald-50'
                },
                { 
                  title: 'Resume-Linked Context', 
                  desc: 'AI agents read your resume to ask questions specific to your real-world experience.',
                  icon: Bot,
                  color: 'text-primary-600',
                  bg: 'bg-primary-50'
                },
                { 
                  title: 'Dynamic Follow-ups', 
                  desc: 'The AI probes deeper into your answers, just like a real engineering manager would.',
                  icon: Cpu,
                  color: 'text-rose-600',
                  bg: 'bg-rose-50'
                },
              ].map((feature, i) => (
                <div key={i} className="p-10 bg-white rounded-3xl border border-slate-100 shadow-sm hover:shadow-xl hover:-translate-y-1 transition-all duration-300">
                  <div className={`w-14 h-14 ${feature.bg} ${feature.color} rounded-2xl flex items-center justify-center mb-8 shadow-inner`}>
                    <feature.icon size={28} />
                  </div>
                  <h3 className="text-xl font-bold text-slate-900 mb-4">{feature.title}</h3>
                  <p className="text-slate-500 leading-relaxed text-sm">{feature.desc}</p>
                </div>
              ))}
            </div>
          </div>
        </section>

        <section id="how-it-works" className="scroll-mt-24 py-24 bg-white dark:bg-slate-950">
          <div className="max-w-7xl mx-auto px-6">
            <div className="text-center mb-16">
              <h2 className="text-4xl font-black text-slate-900 mb-4 tracking-tight dark:text-white">How It Works</h2>
              <p className="text-lg text-slate-500 max-w-2xl mx-auto leading-relaxed dark:text-slate-300">
                Three simple steps: upload your resume, answer focused interview questions, then review your scores.
              </p>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
              {[
                {
                  title: 'Upload your resume',
                  desc: 'The platform reads your resume and role target so the questions fit your real experience.',
                  icon: Upload,
                },
                {
                  title: 'Take the interview',
                  desc: 'Answer five focused questions by voice or text while live scoring tracks your progress.',
                  icon: MessageSquareText,
                },
                {
                  title: 'Review your results',
                  desc: 'Use the dashboard and report to see strengths, weak spots, and next-practice areas.',
                  icon: LineChart,
                },
              ].map((step, i) => (
                <div key={step.title} className="relative p-8 bg-slate-50 rounded-3xl border border-slate-100 dark:bg-slate-900 dark:border-slate-800">
                  <div className="mb-8 flex items-center justify-between">
                    <div className="w-14 h-14 bg-primary-600 text-white rounded-2xl flex items-center justify-center shadow-lg shadow-primary-200/70">
                      <step.icon size={26} />
                    </div>
                    <span className="text-5xl font-black text-slate-200 dark:text-slate-800">0{i + 1}</span>
                  </div>
                  <h3 className="text-xl font-bold text-slate-900 mb-3 dark:text-white">{step.title}</h3>
                  <p className="text-sm text-slate-500 leading-relaxed dark:text-slate-300">{step.desc}</p>
                </div>
              ))}
            </div>
          </div>
        </section>
      </main>

      <footer className="bg-slate-900 py-20 text-white">
        <div className="max-w-7xl mx-auto px-6 flex flex-col md:flex-row justify-between items-center gap-10">
          <div>
            <div className="flex items-center space-x-3 mb-6">
              <div className="w-10 h-10 bg-primary-600 rounded-xl flex items-center justify-center text-white">
                <Bot size={24} />
              </div>
              <span className="text-xl font-bold tracking-tight">AI Interview</span>
            </div>
            <p className="text-slate-400 max-w-xs text-sm leading-relaxed">
              Empowering engineers to reach their full potential through AI-driven simulation and feedback.
            </p>
          </div>
          <div className="flex gap-10 text-sm font-medium">
            <a href="#" className="text-slate-400 hover:text-white transition-colors">Privacy Policy</a>
            <a href="#" className="text-slate-400 hover:text-white transition-colors">Terms of Service</a>
            <a href="#" className="text-slate-400 hover:text-white transition-colors">Support</a>
          </div>
          <p className="text-slate-500 text-xs mt-10 md:mt-0">
            © 2026 AI Interview Platform. All rights reserved.
          </p>
        </div>
      </footer>
    </div>
  );
}
