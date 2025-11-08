'use client';

import { useEffect, useState } from 'react';

type Job = {
  id: number;
  status: string;
  pdf_filename: string;
  audio_filename: string | null;
  // No need for result_text or timestamps here, only needed on player page
};

export default function Dashboard() {
  const [jobs, setJobs] = useState<Job[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const handleLogout = () => {
    localStorage.removeItem('polyvox_token');
    window.location.href = '/'; // Redirect to login page
  };

  // --- DELETE FUNCTION ---
  const handleDeleteJob = async (jobId: number) => {
    if (!window.confirm(`Are you sure you want to delete job ${jobId}? This cannot be undone.`)) {
      return;
    }
    const token = localStorage.getItem('polyvox_token');
    if (!token) {
      setError('Authentication error. Please log in again.');
      return;
    }
    try {
      const res = await fetch(`http://127.0.0.1:8000/jobs/${jobId}`, {
        method: 'DELETE',
        headers: { 'Authorization': `Bearer ${token}` },
      });
      if (res.status === 401) {
        localStorage.removeItem('polyvox_token');
        setError('Session expired. Redirecting to login...');
        setTimeout(() => window.location.href = '/', 2000);
        return;
      }
      if (res.status === 404) { throw new Error('Job not found (perhaps already deleted?).'); }
      if (!res.ok) { throw new Error(`Failed to delete job. Server responded with status ${res.status}`); }

      // Remove job from local state on success
      setJobs(currentJobs => currentJobs.filter(job => job.id !== jobId));
      setError(null);
    } catch (err: any) {
      setError(`Deletion failed: ${err.message}`);
    }
  };

  useEffect(() => {
    const fetchJobs = async () => {
      const token = localStorage.getItem('polyvox_token');
      if (!token) {
        setError('You are not logged in. Redirecting to login...');
        setIsLoading(false);
        setTimeout(() => window.location.href = '/', 2000);
        return;
      }
      try {
        const res = await fetch('http://127.0.0.1:8000/jobs/me', {
          headers: { 'Authorization': `Bearer ${token}` },
        });
        if (res.status === 401) {
            localStorage.removeItem('polyvox_token');
            throw new Error('Your session has expired. Redirecting to login...');
        }
        if (!res.ok) { throw new Error('Failed to fetch jobs.'); }
        const data: Job[] = await res.json();
        setJobs(data);
      } catch (err: any) {
        setError(err.message);
        if (err.message.includes('expired')) {
            setTimeout(() => window.location.href = '/', 2000);
        }
      } finally {
        setIsLoading(false);
      }
    };
    fetchJobs();
  }, []);

  return (
    <main className="min-h-screen bg-gray-900 text-white p-8">
      <div className="container mx-auto">
        <div className="flex justify-between items-center mb-6">
          <h1 className="text-3xl font-bold">My Job History</h1>
          <div>
            <a href="/" className="text-blue-400 hover:underline mr-4">
              Process New PDF &rarr;
            </a>
            <button onClick={handleLogout} className="text-red-400 hover:underline font-semibold">
              Logout
            </button>
          </div>
        </div>

        {/* Display Error if any */}
        {error && <p className="text-red-400 text-center bg-red-900 bg-opacity-30 p-3 rounded mb-4">{error}</p>}

        <div className="bg-gray-800 rounded-lg shadow-lg p-6">
          {isLoading && <p className="text-center">Loading jobs...</p>}
          {!isLoading && (
            <table className="w-full text-left">
              <thead>
                <tr className="border-b border-gray-700">
                  <th className="p-3">PDF Filename</th>
                  <th className="p-3">Status</th>
                  <th className="p-3">Actions</th>
                </tr>
              </thead>
              <tbody>
                {jobs.length > 0 ? (
                  jobs.map((job) => (
                    <tr key={job.id} className="border-b border-gray-700 last:border-b-0 hover:bg-gray-700 transition-colors">
                      <td className="p-3">{job.pdf_filename}</td>
                      <td className="p-3">
                        <span className={`px-2 py-1 rounded-full text-xs font-semibold ${
                          job.status === 'SUCCESS' ? 'bg-green-700 text-green-100' :
                          job.status === 'PENDING' ? 'bg-yellow-700 text-yellow-100' :
                          job.status === 'FAILURE' ? 'bg-red-700 text-red-100' :
                          'bg-gray-700 text-gray-100'
                        }`}>
                          {job.status}
                        </span>
                      </td>
                      <td className="p-3 space-x-4">
                        <a href={`/player/${job.id}`} className="text-green-400 hover:underline text-sm">Play</a>
                        {job.status === 'SUCCESS' && job.audio_filename && (
                          <a href={`http://127.0.0.1:8000/audio/${job.audio_filename}`} target="_blank" rel="noopener noreferrer" className="text-blue-400 hover:underline text-sm">Download</a>
                        )}
                        <button onClick={() => handleDeleteJob(job.id)} className="text-red-400 hover:underline text-sm font-semibold" title="Delete Job">
                          Delete
                        </button>
                      </td>
                    </tr>
                  ))
                ) : (
                  <tr>
                    <td colSpan={3} className="p-3 text-center text-gray-400">
                      You have no jobs yet.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          )}
        </div>
      </div>
    </main>
  );
}