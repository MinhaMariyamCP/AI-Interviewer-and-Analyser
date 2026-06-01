'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import api from '@/lib/api';
import { 
  Upload, 
  FileText, 
  CheckCircle2, 
  Loader2, 
  X, 
  ArrowRight,
  ShieldCheck,
  Zap
} from 'lucide-react';
import { Button } from '@/components/ui/Button';
import { Card, CardContent } from '@/components/ui/Card';

export default function UploadPage() {
  const [file, setFile] = useState<File | null>(null);
  const [isUploading, setIsUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const router = useRouter();

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      const selectedFile = e.target.files[0];
      const validTypes = ['application/pdf', 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'];
      
      if (!validTypes.includes(selectedFile.type)) {
        setError('Please upload a PDF or DOCX file.');
        return;
      }
      
      setFile(selectedFile);
      setError(null);
    }
  };

  const handleUpload = async () => {
    if (!file) return;

    setIsUploading(true);
    setError(null);

    const formData = new FormData();
    formData.append('file', file);

    try {
      const response = await api.post('/api/v1/resumes/upload', formData, {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
      });
      
      localStorage.setItem('resume_id', response.data.id || response.data.resume_id);
      router.push('/role-selection');
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to parse resume. Our AI might be busy, please try again.');
    } finally {
      setIsUploading(false);
    }
  };

  const removeFile = () => {
    setFile(null);
    setError(null);
  };

  return (
    <div className="min-h-screen bg-slate-50 flex flex-col items-center justify-center p-6">
      <div className="max-w-2xl w-full animate-slide-up">
        <div className="text-center mb-10">
          <h1 className="text-4xl font-black text-slate-900 mb-3 tracking-tight">Set the Context</h1>
          <p className="text-slate-500 font-medium max-w-md mx-auto">
            Upload your resume so our AI agents can tailor the interview to your specific background and skills.
          </p>
        </div>

        <Card className="overflow-hidden border-none shadow-2xl shadow-slate-200">
          <CardContent className="p-0">
            <div className="grid grid-cols-1 md:grid-cols-5 h-full">
              <div className="md:col-span-2 bg-primary-600 p-8 text-white flex flex-col justify-between">
                <div>
                  <h3 className="font-bold text-xl mb-6">Why this matters?</h3>
                  <ul className="space-y-6">
                    <li className="flex items-start gap-3">
                      <Zap className="mt-1 flex-shrink-0 text-primary-200" size={18} />
                      <p className="text-sm font-medium leading-relaxed opacity-90">Personalized technical questions based on your stack.</p>
                    </li>
                    <li className="flex items-start gap-3">
                      <ShieldCheck className="mt-1 flex-shrink-0 text-primary-200" size={18} />
                      <p className="text-sm font-medium leading-relaxed opacity-90">Project-deep dives to verify your real-world experience.</p>
                    </li>
                  </ul>
                </div>
                <div className="mt-10 pt-8 border-t border-primary-500/50">
                  <p className="text-[11px] font-bold uppercase tracking-widest opacity-60">Security First</p>
                  <p className="text-[11px] mt-1 opacity-80 leading-relaxed">Your resume is parsed in-memory and never shared with third parties.</p>
                </div>
              </div>

              <div className="md:col-span-3 p-10 bg-white">
                <div 
                  className={`relative group border-2 border-dashed rounded-3xl p-12 text-center transition-all duration-300 ${
                    file 
                      ? 'border-green-400 bg-green-50/30' 
                      : error 
                        ? 'border-red-300 bg-red-50/30'
                        : 'border-slate-200 hover:border-primary-400 hover:bg-slate-50'
                  }`}
                  onClick={() => !file && document.getElementById('resume-upload')?.click()}
                >
                  {!file && (
                    <input 
                      type="file" 
                      id="resume-upload" 
                      className="hidden" 
                      accept=".pdf,.docx" 
                      onChange={handleFileChange}
                    />
                  )}
                  
                  {file ? (
                    <div className="flex flex-col items-center animate-fade-in">
                      <div className="w-16 h-16 bg-green-100 rounded-2xl flex items-center justify-center text-green-600 mb-4 shadow-inner">
                        <FileText size={32} />
                      </div>
                      <p className="text-sm font-bold text-slate-900 mb-1 truncate max-w-[200px]">{file.name}</p>
                      <p className="text-xs text-slate-500 mb-6 uppercase tracking-wider font-bold">Ready to parse</p>
                      <button 
                        onClick={(e) => { e.stopPropagation(); removeFile(); }}
                        className="absolute top-4 right-4 p-2 rounded-full hover:bg-red-50 text-slate-400 hover:text-red-500 transition-colors"
                      >
                        <X size={18} />
                      </button>
                    </div>
                  ) : (
                    <div className="flex flex-col items-center cursor-pointer">
                      <div className="w-16 h-16 bg-slate-50 rounded-2xl flex items-center justify-center text-slate-400 group-hover:text-primary-500 group-hover:bg-primary-50 transition-all duration-300 mb-4">
                        <Upload size={32} />
                      </div>
                      <p className="text-sm font-bold text-slate-900 mb-2">Drag and drop or click to upload</p>
                      <p className="text-xs text-slate-400 font-medium">Supports PDF and DOCX (Max 10MB)</p>
                    </div>
                  )}
                </div>

                {error && (
                  <div className="mt-4 p-3 bg-red-50 text-red-600 text-xs font-bold rounded-xl border border-red-100 flex items-center gap-2 animate-shake">
                    <X size={14} />
                    {error}
                  </div>
                )}

                <Button
                  onClick={handleUpload}
                  disabled={!file || isUploading}
                  className="w-full mt-8 h-14 rounded-2xl font-black shadow-lg"
                  isLoading={isUploading}
                >
                  {isUploading ? 'Analyzing Your Experience...' : 'Initialize AI Agents'}
                  {!isUploading && <ArrowRight className="ml-2" size={20} />}
                </Button>
                
                <p className="text-center text-[10px] text-slate-400 mt-6 font-bold uppercase tracking-widest leading-relaxed">
                  Next Step: Target Role Selection
                </p>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
