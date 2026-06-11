import { useEffect } from 'react';
import { useRouter } from 'next/router';

export default function Home() {
  const router = useRouter();

  useEffect(() => {
    router.replace('/dashboard');
  }, [router]);

  return (
    <div className="min-h-screen bg-[#0d1117] flex items-center justify-center">
      <div className="flex flex-col items-center space-y-4">
        <div className="w-8 h-8 border-4 border-[#58a6ff] border-t-transparent rounded-full animate-spin"></div>
        <span className="text-xs text-[#7d8590] animate-pulse">Redirecting to console...</span>
      </div>
    </div>
  );
}
