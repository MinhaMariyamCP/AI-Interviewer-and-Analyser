'use client';

import React, { useState } from 'react';
import { useAuth } from '@/context/AuthContext';
import Link from 'next/link';
import { Bot, Mail, Lock, User, Loader2, ArrowRight } from 'lucide-react';
import { Button } from '@/components/ui/Button';

export default function SignupPage() {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [name, setName] = useState('');
  const [error, setError] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const { signup } = useAuth();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsLoading(true);
    setError('');
    try {
      await signup(email, password, name);
    } catch (err: any) {
      setError(err?.message || 'Signup failed. Please try again.');
      setIsLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-slate-50 px-4 dark:bg-slate-950">
      <div className="max-w-md w-full animate-slide-up">
        <div className="text-center mb-10">
          <Link href="/" className="inline-flex items-center space-x-3 mb-6 group">
            <div className="w-12 h-12 bg-primary-600 rounded-2xl flex items-center justify-center text-white shadow-lg shadow-primary-200 transition-transform group-hover:scale-110">
              <Bot size={32} />
            </div>
            <span className="text-2xl font-black text-slate-900 tracking-tight dark:text-white">AI Interview</span>
          </Link>
          <h2 className="text-3xl font-bold text-slate-900 dark:text-white">Start Your Journey</h2>
          <p className="mt-2 text-slate-500 font-medium dark:text-slate-300">
            Already have an account?{' '}
            <Link href="/login" className="text-primary-600 hover:text-primary-700 font-bold underline-offset-4 hover:underline dark:text-primary-300">
              Sign in here
            </Link>
          </p>
        </div>

        <div className="bg-white p-10 rounded-3xl shadow-xl shadow-slate-200/60 border border-slate-100 dark:bg-slate-900 dark:border-slate-800 dark:shadow-black/30">
          <form className="space-y-6" onSubmit={handleSubmit}>
            {error && (
              <div className="p-4 bg-red-50 border border-red-100 text-red-600 text-sm font-medium rounded-xl text-center animate-shake">
                {error}
              </div>
            )}
            
            <div className="space-y-2">
              <label className="text-sm font-bold text-slate-700 ml-1 dark:text-slate-200">Full Name</label>
              <div className="relative group">
                <div className="absolute inset-y-0 left-0 pl-4 flex items-center pointer-events-none text-slate-400 group-focus-within:text-primary-500 transition-colors">
                  <User size={18} />
                </div>
                <input
                  type="text"
                  required
                  className="block w-full pl-11 pr-4 py-3.5 bg-slate-50 border border-slate-200 text-slate-900 text-sm rounded-2xl focus:ring-2 focus:ring-primary-500 focus:border-transparent outline-none transition-all placeholder:text-slate-400 dark:bg-slate-950 dark:border-slate-700 dark:text-white"
                  placeholder="John Doe"
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                />
              </div>
            </div>

            <div className="space-y-2">
              <label className="text-sm font-bold text-slate-700 ml-1 dark:text-slate-200">Email Address</label>
              <div className="relative group">
                <div className="absolute inset-y-0 left-0 pl-4 flex items-center pointer-events-none text-slate-400 group-focus-within:text-primary-500 transition-colors">
                  <Mail size={18} />
                </div>
                <input
                  type="email"
                  required
                  className="block w-full pl-11 pr-4 py-3.5 bg-slate-50 border border-slate-200 text-slate-900 text-sm rounded-2xl focus:ring-2 focus:ring-primary-500 focus:border-transparent outline-none transition-all placeholder:text-slate-400 dark:bg-slate-950 dark:border-slate-700 dark:text-white"
                  placeholder="name@company.com"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                />
              </div>
            </div>

            <div className="space-y-2">
              <label className="text-sm font-bold text-slate-700 ml-1 dark:text-slate-200">Password</label>
              <div className="relative group">
                <div className="absolute inset-y-0 left-0 pl-4 flex items-center pointer-events-none text-slate-400 group-focus-within:text-primary-500 transition-colors">
                  <Lock size={18} />
                </div>
                <input
                  type="password"
                  required
                  className="block w-full pl-11 pr-4 py-3.5 bg-slate-50 border border-slate-200 text-slate-900 text-sm rounded-2xl focus:ring-2 focus:ring-primary-500 focus:border-transparent outline-none transition-all placeholder:text-slate-400 dark:bg-slate-950 dark:border-slate-700 dark:text-white"
                  placeholder="Create a secure password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                />
              </div>
              <p className="text-[10px] text-slate-400 ml-1">Must be at least 8 characters with numbers and symbols</p>
            </div>

            <Button 
              type="submit" 
              className="w-full h-14 rounded-2xl text-lg font-bold shadow-lg shadow-primary-200 mt-4"
              isLoading={isLoading}
            >
              Create Account
              {!isLoading && <ArrowRight className="ml-2" size={20} />}
            </Button>
          </form>
          
          <div className="mt-8 pt-8 border-t border-slate-50 dark:border-slate-800">
            <p className="text-[11px] text-slate-400 leading-relaxed text-center dark:text-slate-500">
              By signing up, you agree to our <a href="#" className="font-bold underline">Terms of Service</a> and <a href="#" className="font-bold underline">Privacy Policy</a>.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
