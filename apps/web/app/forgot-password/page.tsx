'use client';

import { useState, type FormEvent } from 'react';
import Link from 'next/link';
import { ArrowRight, Bot, Mail } from 'lucide-react';
import { Button } from '@/components/ui/Button';

export default function ForgotPasswordPage() {
  const [email, setEmail] = useState('');
  const [token, setToken] = useState('');
  const [message, setMessage] = useState('');
  const [error, setError] = useState('');
  const [isLoading, setIsLoading] = useState(false);

  const handleSubmit = async (event: FormEvent) => {
    event.preventDefault();
    setIsLoading(true);
    setError('');
    setMessage('');

    try {
      const apiBaseUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
      const response = await fetch(`${apiBaseUrl}/api/v1/auth/forgot-password`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email }),
      });

      const data = await response.json();
      if (!response.ok) {
        throw new Error(data?.detail || 'Unable to start the reset flow.');
      }

      setToken(data.reset_token || '');
      setMessage(data.message || 'Reset token generated.');
    } catch (err: any) {
      setError(err?.message || 'Unable to generate a password reset token.');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-slate-50 px-4 dark:bg-slate-950">
      <div className="max-w-md w-full animate-slide-up">
        <div className="text-center mb-8">
          <Link href="/login" className="inline-flex items-center space-x-3 mb-6 group">
            <div className="w-12 h-12 bg-primary-600 rounded-2xl flex items-center justify-center text-white shadow-lg shadow-primary-200 transition-transform group-hover:scale-110">
              <Bot size={32} />
            </div>
            <span className="text-2xl font-black text-slate-900 tracking-tight dark:text-white">AI Interview</span>
          </Link>
          <h2 className="text-3xl font-bold text-slate-900 dark:text-white">Reset your password</h2>
          <p className="mt-2 text-slate-500 font-medium dark:text-slate-300">Enter your email and we’ll create the reset token you need for the next step.</p>
        </div>

        <div className="bg-white p-8 rounded-3xl shadow-xl border border-slate-100 dark:bg-slate-900 dark:border-slate-800 dark:shadow-black/30">
          <form className="space-y-6" onSubmit={handleSubmit}>
            {error && <div className="p-4 bg-red-50 border border-red-100 text-red-600 rounded-xl text-sm font-medium">{error}</div>}
            {message && <div className="p-4 bg-emerald-50 border border-emerald-100 text-emerald-700 rounded-xl text-sm font-medium">{message}</div>}

            <div className="space-y-2">
              <label htmlFor="email" className="text-sm font-bold text-slate-700 ml-1 dark:text-slate-200">Email Address</label>
              <div className="relative group">
                <div className="absolute inset-y-0 left-0 pl-4 flex items-center pointer-events-none text-slate-400 group-focus-within:text-primary-500 transition-colors">
                  <Mail size={18} />
                </div>
                <input
                  id="email"
                  type="email"
                  required
                  className="block w-full pl-11 pr-4 py-3.5 bg-slate-50 border border-slate-200 text-slate-900 text-sm rounded-2xl focus:ring-2 focus:ring-primary-500 focus:border-transparent outline-none transition-all placeholder:text-slate-400 dark:bg-slate-950 dark:border-slate-700 dark:text-white"
                  placeholder="name@company.com"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                />
              </div>
            </div>

            <Button type="submit" className="w-full h-14 rounded-2xl text-lg font-bold shadow-lg shadow-primary-200" isLoading={isLoading}>
              Generate Reset Token
              {!isLoading && <ArrowRight className="ml-2" size={20} />}
            </Button>

            {token && (
              <div className="rounded-2xl border border-primary-100 bg-primary-50 p-4 text-sm text-primary-900 dark:border-primary-900 dark:bg-primary-950/60 dark:text-primary-100">
                <p className="font-black uppercase tracking-widest text-[10px] mb-1">Reset Token</p>
                <p className="font-mono break-all">{token}</p>
                <Link href={`/reset-password?email=${encodeURIComponent(email)}&token=${encodeURIComponent(token)}`} className="mt-3 inline-flex items-center text-sm font-black text-primary-700 dark:text-primary-300">Continue to reset password →</Link>
              </div>
            )}
          </form>

          <p className="mt-6 text-center text-xs text-slate-400 dark:text-slate-500">
            Remembered your password? <Link href="/login" className="font-black text-primary-600 dark:text-primary-300">Return to sign in</Link>
          </p>
        </div>
      </div>
    </div>
  );
}
