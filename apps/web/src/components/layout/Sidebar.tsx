'use client';

import React from 'react';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { 
  LayoutDashboard, 
  History, 
  BarChart3, 
  Settings, 
  PlusCircle, 
  LogOut,
  Bot,
  User as UserIcon
} from 'lucide-react';
import { useAuth } from '@/context/AuthContext';
import { cn } from '@/lib/utils';

export const Sidebar = () => {
  const pathname = usePathname();
  const { logout, user } = useAuth();

  const menuItems = [
    { name: 'Dashboard', icon: LayoutDashboard, href: '/dashboard' },
    { name: 'Analytics', icon: BarChart3, href: '/dashboard/analytics' },
    { name: 'History', icon: History, href: '/dashboard/interview' },
    { name: 'Settings', icon: Settings, href: '/dashboard/settings' },
  ];

  return (
    <aside className="w-64 bg-white border-r border-slate-200 h-screen flex flex-col sticky top-0 transition-all duration-300 ease-in-out">
      <div className="p-6">
        <Link href="/" className="flex items-center space-x-3 group">
          <div className="w-10 h-10 bg-primary-600 rounded-xl flex items-center justify-center text-white shadow-lg shadow-primary-200 transition-transform group-hover:scale-110">
            <Bot size={24} />
          </div>
          <span className="text-xl font-bold text-slate-900 tracking-tight">AI Interview</span>
        </Link>
      </div>

      <nav className="flex-1 px-4 space-y-1 mt-4">
        {menuItems.map((item) => {
          const isActive = pathname === item.href;
          return (
            <Link
              key={item.name}
              href={item.href}
              className={cn(
                "flex items-center space-x-3 px-4 py-3 rounded-xl font-medium transition-all duration-200",
                isActive 
                  ? "bg-primary-50 text-primary-700 shadow-sm" 
                  : "text-slate-600 hover:bg-slate-50 hover:text-slate-900"
              )}
            >
              <item.icon size={20} className={cn(isActive ? "text-primary-600" : "text-slate-400")} />
              <span>{item.name}</span>
            </Link>
          );
        })}
      </nav>

      <div className="p-4 space-y-4">
        <Link 
          href="/upload"
          className="flex items-center justify-center space-x-2 w-full py-3 bg-primary-600 text-white rounded-xl font-bold hover:bg-primary-700 transition-all shadow-md hover:shadow-lg active:scale-95"
        >
          <PlusCircle size={18} />
          <span>New Interview</span>
        </Link>

        <div className="pt-4 border-t border-slate-100">
          <div className="flex items-center space-x-3 px-2 py-2 mb-2">
            <div className="w-8 h-8 rounded-full bg-slate-100 flex items-center justify-center text-slate-600 border border-slate-200">
              <UserIcon size={16} />
            </div>
            <div className="flex-1 min-w-0 text-sm text-slate-900 font-semibold truncate">
              {user?.email || 'Candidate'}
            </div>
          </div>
          <button 
            onClick={logout}
            className="flex items-center space-x-3 w-full px-4 py-2 text-sm text-slate-500 hover:text-red-600 hover:bg-red-50 rounded-lg transition-colors group"
          >
            <LogOut size={18} className="group-hover:text-red-500" />
            <span>Logout</span>
          </button>
        </div>
      </div>
    </aside>
  );
};
