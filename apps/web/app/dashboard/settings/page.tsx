'use client';

import React, { useState, useEffect } from 'react';
import { 
  User, 
  Mail, 
  Lock, 
  Shield, 
  Bell, 
  Save, 
  Loader2,
  CheckCircle2,
  AlertCircle
} from 'lucide-react';
import { Sidebar } from '@/components/layout/Sidebar';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import api from '@/lib/api';

export default function SettingsPage() {
  const [profile, setProfile] = useState({
    full_name: '',
    email: '',
  });
  const [passwords, setPasswords] = useState({
    current: '',
    new: '',
    confirm: ''
  });
  
  const [isLoading, setIsLoading] = useState(true);
  const [isSaving, setIsSaving] = useState(false);
  const [feedback, setFeedback] = useState<{type: 'success' | 'error', message: string} | null>(null);

  useEffect(() => {
    const fetchProfile = async () => {
      try {
        const response = await api.get('/api/v1/users/me');
        setProfile({
          full_name: response.data.full_name || '',
          email: response.data.email || '',
        });
      } catch (err) {
        console.error("Failed to fetch profile", err);
      } finally {
        setIsLoading(false);
      }
    };
    fetchProfile();
  }, []);

  const handleUpdateProfile = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsSaving(true);
    setFeedback(null);
    try {
      await api.put('/api/v1/users/me', {
        full_name: profile.full_name,
        email: profile.email
      });
      setFeedback({ type: 'success', message: 'Profile updated successfully!' });
    } catch (err: any) {
      setFeedback({ type: 'error', message: err.response?.data?.detail || 'Failed to update profile.' });
    } finally {
      setIsSaving(false);
    }
  };

  const handleUpdatePassword = async (e: React.FormEvent) => {
    e.preventDefault();
    if (passwords.new !== passwords.confirm) {
      setFeedback({ type: 'error', message: 'New passwords do not match.' });
      return;
    }
    
    setIsSaving(true);
    setFeedback(null);
    try {
      await api.put('/api/v1/users/me', {
        password: passwords.new
      });
      setFeedback({ type: 'success', message: 'Password changed successfully!' });
      setPasswords({ current: '', new: '', confirm: '' });
    } catch (err: any) {
      setFeedback({ type: 'error', message: err.response?.data?.detail || 'Failed to update password.' });
    } finally {
      setIsSaving(false);
    }
  };

  if (isLoading) {
    return (
      <div className="flex h-screen bg-slate-50 overflow-hidden">
        <Sidebar />
        <main className="flex-1 flex items-center justify-center">
          <Loader2 className="w-12 h-12 text-primary-600 animate-spin" />
        </main>
      </div>
    );
  }

  return (
    <div className="flex h-screen bg-slate-50 overflow-hidden font-sans text-slate-900">
      <Sidebar />

      <main className="flex-1 overflow-y-auto p-8 lg:p-12 animate-fade-in">
        <header className="mb-12">
          <h1 className="text-4xl font-black tracking-tight mb-2">Account Settings</h1>
          <p className="text-slate-500 font-medium">Manage your personal information and security preferences.</p>
        </header>

        {feedback && (
          <div className={`max-w-3xl mb-8 p-4 rounded-2xl border flex items-center gap-3 animate-slide-up ${
            feedback.type === 'success' ? 'bg-emerald-50 border-emerald-100 text-emerald-700' : 'bg-red-50 border-red-100 text-red-700'
          }`}>
            {feedback.type === 'success' ? <CheckCircle2 size={20}/> : <AlertCircle size={20}/>}
            <span className="text-sm font-bold">{feedback.message}</span>
          </div>
        )}

        <div className="max-w-4xl space-y-8">
          {/* Profile Section */}
          <Card className="border-none shadow-sm ring-1 ring-slate-100">
            <CardHeader className="p-8 border-b border-slate-50">
              <div className="flex items-center gap-4">
                <div className="w-12 h-12 bg-primary-50 text-primary-600 rounded-2xl flex items-center justify-center">
                  <User size={24} />
                </div>
                <div>
                  <CardTitle className="text-xl font-black">Personal Profile</CardTitle>
                  <CardDescription className="font-medium">Your basic information used for reports and identity.</CardDescription>
                </div>
              </div>
            </CardHeader>
            <CardContent className="p-8">
              <form onSubmit={handleUpdateProfile} className="space-y-6">
                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                  <div className="space-y-2">
                    <label className="text-[10px] font-black text-slate-400 uppercase tracking-widest ml-1">Full Name</label>
                    <input 
                      type="text" 
                      value={profile.full_name}
                      onChange={(e) => setProfile({...profile, full_name: e.target.value})}
                      className="w-full px-5 py-3.5 bg-slate-50 border border-slate-100 rounded-2xl focus:ring-2 focus:ring-primary-500 outline-none transition-all font-semibold"
                    />
                  </div>
                  <div className="space-y-2">
                    <label className="text-[10px] font-black text-slate-400 uppercase tracking-widest ml-1">Email Address</label>
                    <input 
                      type="email" 
                      value={profile.email}
                      onChange={(e) => setProfile({...profile, email: e.target.value})}
                      className="w-full px-5 py-3.5 bg-slate-50 border border-slate-100 rounded-2xl focus:ring-2 focus:ring-primary-500 outline-none transition-all font-semibold"
                    />
                  </div>
                </div>
                <div className="flex justify-end">
                  <Button type="submit" isLoading={isSaving} className="rounded-xl px-10 shadow-lg shadow-primary-200">
                    <Save size={18} className="mr-2" />
                    Save Changes
                  </Button>
                </div>
              </form>
            </CardContent>
          </Card>

          {/* Security Section */}
          <Card className="border-none shadow-sm ring-1 ring-slate-100">
            <CardHeader className="p-8 border-b border-slate-50">
              <div className="flex items-center gap-4">
                <div className="w-12 h-12 bg-amber-50 text-amber-600 rounded-2xl flex items-center justify-center">
                  <Shield size={24} />
                </div>
                <div>
                  <CardTitle className="text-xl font-black">Security & Password</CardTitle>
                  <CardDescription className="font-medium">Ensure your account remains protected.</CardDescription>
                </div>
              </div>
            </CardHeader>
            <CardContent className="p-8">
              <form onSubmit={handleUpdatePassword} className="space-y-6">
                <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                  <div className="space-y-2">
                    <label className="text-[10px] font-black text-slate-400 uppercase tracking-widest ml-1">Current Password</label>
                    <input 
                      type="password" 
                      placeholder="••••••••"
                      value={passwords.current}
                      onChange={(e) => setPasswords({...passwords, current: e.target.value})}
                      className="w-full px-5 py-3.5 bg-slate-50 border border-slate-100 rounded-2xl focus:ring-2 focus:ring-primary-500 outline-none transition-all font-semibold"
                    />
                  </div>
                  <div className="space-y-2">
                    <label className="text-[10px] font-black text-slate-400 uppercase tracking-widest ml-1">New Password</label>
                    <input 
                      type="password" 
                      placeholder="New password"
                      value={passwords.new}
                      onChange={(e) => setPasswords({...passwords, new: e.target.value})}
                      className="w-full px-5 py-3.5 bg-slate-50 border border-slate-100 rounded-2xl focus:ring-2 focus:ring-primary-500 outline-none transition-all font-semibold"
                    />
                  </div>
                  <div className="space-y-2">
                    <label className="text-[10px] font-black text-slate-400 uppercase tracking-widest ml-1">Confirm Password</label>
                    <input 
                      type="password" 
                      placeholder="Confirm new"
                      value={passwords.confirm}
                      onChange={(e) => setPasswords({...passwords, confirm: e.target.value})}
                      className="w-full px-5 py-3.5 bg-slate-50 border border-slate-100 rounded-2xl focus:ring-2 focus:ring-primary-500 outline-none transition-all font-semibold"
                    />
                  </div>
                </div>
                <div className="flex justify-end">
                  <Button type="submit" variant="secondary" isLoading={isSaving} className="rounded-xl px-10">
                    Update Password
                  </Button>
                </div>
              </form>
            </CardContent>
          </Card>

          {/* Preferences Section (UI Only) */}
          <Card className="border-none shadow-sm ring-1 ring-slate-100 opacity-60 grayscale pointer-events-none">
            <CardHeader className="p-8 border-b border-slate-50">
              <div className="flex items-center gap-4">
                <div className="w-12 h-12 bg-purple-50 text-purple-600 rounded-2xl flex items-center justify-center">
                  <Bell size={24} />
                </div>
                <div>
                  <CardTitle className="text-xl font-black">Notifications</CardTitle>
                  <CardDescription className="font-medium text-purple-600">Coming soon in v2.0</CardDescription>
                </div>
              </div>
            </CardHeader>
          </Card>
        </div>
      </main>
    </div>
  );
}
