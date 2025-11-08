// frontend/src/app/player/[jobId]/page.tsx
'use client';

import { useEffect, useState, useRef } from 'react';
import { useParams } from 'next/navigation';

// Type for the timestamp data chunks
type TimestampChunk = {
  chunk: string;
  start: number; // seconds
  end: number;   // seconds
};

// Type for the full job details from API
type JobDetails = {
  id: number;
  status: string;
  pdf_filename: string;
  audio_filename: string | null;
  result_text: string | null;
  timestamps_json: string | null; // Timestamps as JSON string
};

export default function PlayerPage() {
  const params = useParams();
  const jobId = params?.jobId;

  const [jobDetails, setJobDetails] = useState<JobDetails | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [timestamps, setTimestamps] = useState<TimestampChunk[]>([]);
  const [activeChunkIndex, setActiveChunkIndex] = useState<number>(-1);

  // Ref to access the audio element
  const audioRef = useRef<HTMLAudioElement>(null);

  // Effect to fetch job details
  useEffect(() => {
    if (!jobId) {
      setError("Job ID not found in URL.");
      setIsLoading(false);
      return;
    }

    const fetchJobDetails = async () => {
      setIsLoading(true); // Ensure loading is true at the start
      setError(null); // Clear previous errors
      setTimestamps([]); // Clear previous timestamps
      setActiveChunkIndex(-1); // Reset highlight

      const token = localStorage.getItem('polyvox_token');
      if (!token) {
        setError('You are not logged in. Redirecting...');
        setIsLoading(false);
        setTimeout(() => window.location.href = '/', 2000);
        return;
      }

      try {
        const res = await fetch(`http://127.0.0.1:8000/jobs/${jobId}`, {
          headers: { 'Authorization': `Bearer ${token}` },
        });

        if (res.status === 401) {
          localStorage.removeItem('polyvox_token');
          throw new Error('Session expired. Redirecting...');
        }
        if (res.status === 404) {
          throw new Error('Job not found.');
        }
        if (!res.ok) {
          throw new Error('Failed to fetch job details.');
        }

        const data: JobDetails = await res.json();
        setJobDetails(data);

        // --- NEW: Parse Timestamps ---
        if (data.timestamps_json) {
          try {
            const parsedTimestamps: TimestampChunk[] = JSON.parse(data.timestamps_json);
            setTimestamps(parsedTimestamps);
          } catch (parseError) {
            console.error("Failed to parse timestamps JSON:", parseError);
            setError("Error loading text timing data.");
          }
        } else if (data.status === 'SUCCESS') {
           setError("Timestamp data is missing for this job.");
        }

      } catch (err: any) {
        setError(err.message);
        if (err.message.includes('expired')) {
            setTimeout(() => window.location.href = '/', 2000);
        }
      } finally {
        setIsLoading(false);
      }
    };

    fetchJobDetails();
  }, [jobId]);

  // Effect to handle audio time updates for highlighting
  useEffect(() => {
    const audio = audioRef.current;
    if (!audio || timestamps.length === 0) return;

    const handleTimeUpdate = () => {
      const currentTime = audio.currentTime;
      // Find the index of the chunk that contains the current time
      const currentIndex = timestamps.findIndex(
        (chunk) => currentTime >= chunk.start && currentTime < chunk.end
      );
      // Update the active chunk index if it has changed
      if (currentIndex !== activeChunkIndex) {
        setActiveChunkIndex(currentIndex);
      }
    };

    const handleAudioEnd = () => {
      setActiveChunkIndex(-1); // Reset highlight when audio finishes
    };

    // Add event listeners
    audio.addEventListener('timeupdate', handleTimeUpdate);
    audio.addEventListener('ended', handleAudioEnd);

    // Cleanup function to remove listeners when component unmounts or dependencies change
    return () => {
      audio.removeEventListener('timeupdate', handleTimeUpdate);
      audio.removeEventListener('ended', handleAudioEnd);
    };
  }, [timestamps, activeChunkIndex]); // Rerun effect if timestamps load or active index changes

  return (
    <main className="min-h-screen bg-gray-900 text-white p-8">
      <div className="container mx-auto">
        <div className="flex justify-between items-center mb-6">
          <h1 className="text-3xl font-bold">Audio Player</h1>
          <a href="/dashboard" className="text-blue-400 hover:underline">
            &larr; Back to Dashboard
          </a>
        </div>

        {isLoading && <p className="text-center">Loading job details...</p>}
        {error && <p className="text-red-400 text-center">{error}</p>}

        {!isLoading && !error && jobDetails && (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {/* Text Display Box */}
            <div className="bg-gray-800 rounded-lg shadow-lg p-6">
              <h2 className="text-xl font-semibold mb-4">Generated Text</h2>
              <div className="max-h-96 overflow-y-auto bg-gray-700 p-4 rounded text-sm">
                {/* --- NEW: Render text with highlighting --- */}
                {timestamps.length > 0 ? (
                  timestamps.map((chunk, index) => (
                    <span
                      key={index}
                      className={`transition-colors duration-150 ease-in-out ${ // Added transition
                        index === activeChunkIndex
                          ? 'bg-yellow-500 bg-opacity-50' // Style for active chunk
                          : ''
                      }`}
                    >
                      {chunk.chunk}{' '} {/* Add space between chunks */}
                    </span>
                  ))
                ) : (
                  // Fallback if timestamps are missing or failed to parse
                  <span className="whitespace-pre-wrap">{jobDetails.result_text || "No text available."}</span>
                )}
              </div>
            </div>

            {/* Audio Player Box */}
            <div className="bg-gray-800 rounded-lg shadow-lg p-6 flex flex-col items-center justify-center">
              <h2 className="text-xl font-semibold mb-4">Audio Output for "{jobDetails.pdf_filename}"</h2>
              {jobDetails.status === 'SUCCESS' && jobDetails.audio_filename ? (
                // Add the ref to the audio element
                <audio ref={audioRef} controls className="w-full">
                  <source
                    src={`http://127.0.0.1:8000/audio/${jobDetails.audio_filename}`}
                    type="audio/mpeg"
                  />
                  Your browser does not support the audio element.
                </audio>
              ) : jobDetails.status === 'PENDING' ? (
                 <p className="text-yellow-400">Audio is still processing...</p>
              ) : (
                 <p className="text-red-400">Audio generation failed or file not found.</p>
              )}
            </div>
          </div>
        )}
      </div>
    </main>
  );
}