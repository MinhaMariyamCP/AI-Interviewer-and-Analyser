'use client';

import { useEffect, useMemo, useRef, useState } from 'react';
import Vapi from '@vapi-ai/web';
import { AlertCircle, Bot, Phone, PhoneOff, Radio } from 'lucide-react';
import { cn } from '@/lib/utils';

type VapiMessage = {
  type?: string;
  role?: 'assistant' | 'user' | string;
  transcript?: string;
  transcriptType?: 'partial' | 'final' | string;
};

interface VapiAssistantProps {
  className?: string;
  targetRole?: string;
  compact?: boolean;
}

export function VapiAssistant({ className, targetRole, compact = false }: VapiAssistantProps) {
  const publicKey = process.env.NEXT_PUBLIC_VAPI_PUBLIC_KEY;
  const assistantId = process.env.NEXT_PUBLIC_VAPI_ASSISTANT_ID;
  const vapiRef = useRef<Vapi | null>(null);
  const [isReady, setIsReady] = useState(false);
  const [isCalling, setIsCalling] = useState(false);
  const [status, setStatus] = useState('Ready');
  const [error, setError] = useState<string | null>(null);
  const [lastTranscript, setLastTranscript] = useState('');

  const isConfigured = useMemo(() => Boolean(publicKey && assistantId), [publicKey, assistantId]);

  useEffect(() => {
    if (!isConfigured || !publicKey) {
      setIsReady(false);
      return;
    }

    const vapi = new Vapi(publicKey);
    vapiRef.current = vapi;

    vapi.on('call-start', () => {
      setIsCalling(true);
      setStatus('Live call active');
      setError(null);
    });

    vapi.on('call-end', () => {
      setIsCalling(false);
      setStatus('Call ended');
    });

    vapi.on('speech-start', () => {
      setStatus('Assistant speaking');
    });

    vapi.on('speech-end', () => {
      setStatus('Listening');
    });

    vapi.on('message', (message: VapiMessage) => {
      if (message.type === 'transcript' && message.transcript) {
        const speaker = message.role === 'assistant' ? 'Assistant' : 'You';
        setLastTranscript(`${speaker}: ${message.transcript}`);
      }
    });

    vapi.on('error', (event: unknown) => {
      console.error('Vapi error:', event);
      setIsCalling(false);
      setError('Vapi call failed. Check microphone permission and Vapi environment variables.');
      setStatus('Error');
    });

    setIsReady(true);

    return () => {
      try {
        vapi.stop();
      } catch {
        // No-op: stopping an idle Vapi client may throw in some browser states.
      }
      vapiRef.current = null;
    };
  }, [isConfigured, publicKey]);

  const startCall = async () => {
    if (!vapiRef.current || !assistantId) return;
    try {
      setError(null);
      setStatus('Starting call...');
      await vapiRef.current.start(assistantId, {
        variableValues: {
          targetRole: targetRole || 'Software Engineer',
        },
      });
    } catch (err) {
      console.error('Failed to start Vapi call:', err);
      setIsCalling(false);
      setStatus('Error');
      setError('Unable to start Vapi assistant. Verify your public key and assistant ID.');
    }
  };

  const stopCall = () => {
    try {
      vapiRef.current?.stop();
      setIsCalling(false);
      setStatus('Call ended');
    } catch (err) {
      console.error('Failed to stop Vapi call:', err);
    }
  };

  if (!isConfigured) {
    return (
      <div className={cn('rounded-2xl border border-amber-100 bg-amber-50 p-4 text-amber-800', className)}>
        <div className="flex items-start gap-3">
          <AlertCircle size={18} className="mt-0.5 flex-shrink-0" />
          <div>
            <p className="text-xs font-black uppercase tracking-widest">Vapi Not Configured</p>
            <p className="mt-1 text-xs font-semibold leading-relaxed">
              Add NEXT_PUBLIC_VAPI_PUBLIC_KEY and NEXT_PUBLIC_VAPI_ASSISTANT_ID in Render to enable the voice assistant.
            </p>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className={cn('rounded-2xl border border-primary-100 bg-primary-50 p-4', className)}>
      <div className="flex items-center justify-between gap-3">
        <div className="flex min-w-0 items-center gap-3">
          <div className={cn(
            'flex h-10 w-10 flex-shrink-0 items-center justify-center rounded-xl text-white shadow-lg',
            isCalling ? 'bg-emerald-600 shadow-emerald-100' : 'bg-primary-600 shadow-primary-100'
          )}>
            {isCalling ? <Radio size={18} className="animate-pulse" /> : <Bot size={18} />}
          </div>
          <div className="min-w-0">
            <p className="text-xs font-black uppercase tracking-widest text-primary-900">Vapi Assistant</p>
            <p className="truncate text-xs font-bold text-primary-500">{isReady ? status : 'Loading...'}</p>
          </div>
        </div>

        <button
          type="button"
          onClick={isCalling ? stopCall : startCall}
          disabled={!isReady}
          className={cn(
            'flex h-11 w-11 flex-shrink-0 items-center justify-center rounded-xl text-white transition-all active:scale-95 disabled:cursor-not-allowed disabled:opacity-50',
            isCalling ? 'bg-red-500 hover:bg-red-600' : 'bg-slate-900 hover:bg-slate-800'
          )}
          title={isCalling ? 'End Vapi call' : 'Start Vapi voice assistant'}
        >
          {isCalling ? <PhoneOff size={18} /> : <Phone size={18} />}
        </button>
      </div>

      {!compact && lastTranscript && (
        <div className="mt-4 rounded-xl bg-white/80 p-3 text-xs font-semibold leading-relaxed text-slate-600">
          {lastTranscript}
        </div>
      )}

      {error && (
        <p className="mt-3 text-xs font-bold leading-relaxed text-red-600">{error}</p>
      )}
    </div>
  );
}
