'use client';

import { Suspense, useEffect, useState, type FormEvent } from 'react';
import Link from 'next/link';
import { useSearchParams } from 'next/navigation';
import { ArrowRight, Bot, Lock, Mail, Loader2 } from 'lucide-react';
import { Button } from '@/components/ui/Button';

function ResetPasswordContent() {
  const searchParams = useSearchParams();
  const [email, setEmail] = useState('');
  const [token, setToken] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [message, setMessage] = useState('');
  const [error, setError] = useState('');
  const [isLoading, setIsLoading] = useState(false);

  useEffect(() => {
    setEmail(searchParams.get('email') || '');
    setToken(searchParams.get('token') || '');
  }, [searchParams]);

  const handleSubmit = async (event: FormEvent) => {
    event.preventDefault();
    setError('');
    setMessage('');

    if (newPassword.length < 8) {
      setError('Password must be at least 8 characters long.');
      return;
    }

    if (newPassword !== confirmPassword) {
      setError('Passwords do not match.');
      return;
    }

    setIsLoading(true);
    try {
      const apiBaseUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
      const response = await fetch(`${apiBaseUrl}/api/v1/auth/reset-password`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email, token, new_password: newPassword }),
      });

      const data = await response.json();
      if (!response.ok) throw new Error(data?.detail || 'Unable to reset your password.');
      setMessage(data.message || 'Password updated successfully.');
      setNewPassword('');
      setConfirmPassword('');
    } catch (err: any) {
      setError(err?.message || 'Unable to reset your password.');
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
          <h2 className="text-3xl font-bold text-slate-900 dark:text-white">Set a new password</h2>
          <p className="mt-2 text-slate-500 font-medium dark:text-slate-300">Use the token from your email and choose a new password.</p>
        </div>

        <div className="bg-white p-8 rounded-3xl shadow-xl border border-slate-100 dark:bg-slate-900 dark:border-slate-800 dark:shadow-black/30">
          <form className="space-y-6" onSubmit={handleSubmit}>
            {error && <div className="p-4 bg-red-50 border border-red-100 text-red-600 rounded-xl text-sm font-medium">{error}</div>}
            {message && <div className="p-4 bg-emerald-50 border border-emerald-100 text-emerald-700 rounded-xl text-sm font-medium">{message}</div>}

            <div className="space-y-2">
              <label htmlFor="email" className="text-sm font-bold text-slate-700 ml-1 dark:text-slate-200">Email Address</label>
              <div className="relative group">
                <div className="absolute inset-y-0 left-0 pl-4 flex items-center pointer-events-none text-slate-400 group-focus-within:text-primary-500 transition-colors"><Mail size={18} /></div>
                <input id="email" type="email" required className="block w-full pl-11 pr-4 py-3.5 bg-slate-50 border border-slate-200 text-slate-900 text-sm rounded-2xl focus:ring-2 focus:ring-primary-500 focus:border-transparent outline-none transition-all placeholder:text-slate-400 dark:bg-slate-950 dark:border-slate-700 dark:text-white" value={email} onChange={(e) => setEmail(e.target.value)} />
              </div>
            </div>

            <div className="space-y-2">
              <label htmlFor="token" className="text-sm font-bold text-slate-700 ml-1 dark:text-slate-200">Reset Token</label>
              <input id="token" type="text" required className="block w-full px-4 py-3.5 bg-slate-50 border border-slate-200 text-slate-900 text-sm rounded-2xl focus:ring-2 focus:ring-primary-500 focus:border-transparent outline-none transition-all placeholder:text-slate-400 dark:bg-slate-950 dark:border-slate-700 dark:text-white" value={token} onChange={(e) => setToken(e.target.value)} />
            </div>

            <div className="space-y-2">
              <label htmlFor="newPassword" className="text-sm font-bold text-slate-700 ml-1 dark:text-slate-200">New Password</label>
              <div className="relative group">
                <div className="absolute inset-y-0 left-0 pl-4 flex items-center pointer-events-none text-slate-400 group-focus-within:text-primary-500 transition-colors"><Lock size={18} /></div>
                <input id="newPassword" type="password" required className="block w-full pl-11 pr-4 py-3.5 bg-slate-50 border border-slate-200 text-slate-900 text-sm rounded-2xl focus:ring-2 focus:ring-primary-500 focus:border-transparent outline-none transition-all placeholder:text-slate-400 dark:bg-slate-950 dark:border-slate-700 dark:text-white" value={newPassword} onChange={(e) => setNewPassword(e.target.value)} />
              </div>
            </div>

            <div className="space-y-2">
              <label htmlFor="confirmPassword" className="text-sm font-bold text-slate-700 ml-1 dark:text-slate-200">Confirm Password</label>
              <div className="relative group">
                <div className="absolute inset-y-0 left-0 pl-4 flex items-center pointer-events-none text-slate-400 group-focus-within:text-primary-500 transition-colors"><Lock size={18} /></div>
                <input id="confirmPassword" type="password" required className="block w-full pl-11 pr-4 py-3.5 bg-slate-50 border border-slate-200 text-slate-900 text-sm rounded-2xl focus:ring-2 focus:ring-primary-500 focus:border-transparent outline-none transition-all placeholder:text-slate-400 dark:bg-slate-950 dark:border-slate-700 dark:text-white" value={confirmPassword} onChange={(e) => setConfirmPassword(e.target.value)} />
              </div>
            </div>

            <Button type="submit" className="w-full h-14 rounded-2xl text-lg font-bold shadow-lg shadow-primary-200" isLoading={isLoading}>
              Update Password
              {!isLoading && <ArrowRight className="ml-2" size={20} />}
            </Button>
          </form>

          <p className="mt-6 text-center text-xs text-slate-400 dark:text-slate-500">
            Need a fresh token? <Link href="/forgot-password" className="font-black text-primary-600 dark:text-primary-300">Generate one here</Link>
          </p>
        </div>
      </div>
    </div>
  );
}

export default function ResetPasswordPage() {
  return (
    <Suspense fallback={
      <div className="min-h-screen flex items-center justify-center bg-slate-50 px-4 dark:bg-slate-950">
        <div className="flex flex-col items-center">
          <Loader2 className="w-12 h-12 text-primary-600 animate-spin mb-4" />
          <p className="text-sm font-bold text-slate-400 uppercase tracking-widest">Loading Reset Page...</p>
        </div>
      </div>
    }>
      <ResetPasswordContent />
    </Suspense>
  );
}
