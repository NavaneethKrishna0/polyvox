'use client';

import { useState, FormEvent, useEffect } from 'react';
import Link from 'next/link';

// Define response types
type JobResponse = { job_id?: number; error?: string }; // Expect DB Job ID now
type AuthResponse = { access_token: string; token_type: string };
type StatusResult = { status: 'SUCCESS' | 'FAILURE'; audio_filename?: string; error?: string };

export default function Home() {
  const [file, setFile] = useState<File | null>(null);
  const [statusMessage, setStatusMessage] = useState<string>('');
  const [result, setResult] = useState<StatusResult | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [authToken, setAuthToken] = useState<string | null>(null);

  useEffect(() => {
    const token = localStorage.getItem('polyvox_token');
    if (token) {
      setAuthToken(token);
    }
  }, []);

  const handleLogin = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setIsLoading(true);
    const formData = new FormData(event.currentTarget);
    try {
      console.log("Attempting login..."); // Debug
      const res = await fetch('http://127.0.0.1:8000/token', { method: 'POST', body: formData });

      // --- ADD THESE DEBUG LOGS ---
      console.log("Login Response Status:", res.status);
      console.log("Login Response OK:", res.ok);
      // Clone the response to log its body safely, as .json() consumes it
      const resClone = res.clone();
      const rawBody = await resClone.text();
      console.log("Login Raw Response Body:", rawBody);
      // --- END DEBUG LOGS ---

      if (!res.ok) {
         console.error("Login fetch failed with status:", res.status); // Debug error
         throw new Error('Login failed');
      }

      console.log("Attempting to parse JSON..."); // Debug
      const data: AuthResponse = await res.json(); // Attempt to parse
      console.log("Parsed JSON data:", data); // Debug parsed data

      if (!data || !data.access_token) {
        console.error("Access token missing in response data:", data); // Debug missing token
        throw new Error("Access token not found in response.");
      }

      console.log("Setting token in localStorage and state..."); // Debug
      localStorage.setItem('polyvox_token', data.access_token);
      setAuthToken(data.access_token);
      console.log("Token set successfully."); // Debug success

    } catch (error) {
      // --- MODIFY CATCH BLOCK ---
      console.error("Error during login:", error); // Log the actual error
      alert(`Login failed: ${error instanceof Error ? error.message : 'Unknown error'}`); // Show more specific alert
      // --- END MODIFICATION ---
    } finally {
      setIsLoading(false);
    }
  };

  const handleLogout = () => {
    localStorage.removeItem('polyvox_token');
    setAuthToken(null);
    window.location.reload();
  };

  const handlePdfSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!file) {
      alert("Please select a PDF file first.");
      return;
    }
    if (!authToken) {
      alert("You are not logged in. Please refresh and log in again.");
      return;
    }

    setIsLoading(true);
    setStatusMessage('Uploading and starting job...');
    setResult(null);

    const formData = new FormData(event.currentTarget);
    // Append file separately if needed, ensure names match backend Form fields
    if(file) formData.set('uploaded_file', file);

    try {
      const res = await fetch('http://127.0.0.1:8000/process-pdf/', {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${authToken}`,
          // DO NOT set Content-Type, let the browser handle it for FormData
        },
        body: formData,
      });

      if (res.status === 401) {
          throw new Error("Authorization failed. Your session may have expired. Please log out and log in again.");
      }

      const data: JobResponse = await res.json();
      if (data.job_id) {
        // Now using DB Job ID
        setStatusMessage(`Job started successfully! Check the dashboard for progress (Job ID: ${data.job_id}).`);
      } else {
        setStatusMessage(data.error || 'Failed to start job.');
      }
    } catch (error: any) {
      setStatusMessage(`Error: ${error.message}`);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <main className="flex min-h-screen flex-col items-center justify-center bg-gray-900 text-white p-8">
      {!authToken ? (
        // --- VIEW 1: LOGIN FORM ---
        <div className="w-full max-w-md p-8 space-y-6 bg-gray-800 rounded-lg shadow-lg">
          <h1 className="text-3xl font-bold text-center">Login to Polyvox</h1>
          <form onSubmit={handleLogin} className="space-y-4">
            <div>
              <label htmlFor="username">Email</label>
              <input type="email" name="username" required className="mt-1 block w-full rounded-md border-gray-600 bg-gray-700 py-2 px-3 text-white"/>
            </div>
            <div>
              <label htmlFor="password">Password</label>
              <input type="password" name="password" required className="mt-1 block w-full rounded-md border-gray-600 bg-gray-700 py-2 px-3 text-white"/>
            </div>
            <button type="submit" disabled={isLoading} className="w-full py-2 px-4 bg-blue-600 hover:bg-blue-700 rounded-md disabled:opacity-50">
              {isLoading ? 'Logging in...' : 'Login'}
            </button>
          </form>
           <p className="text-center text-sm text-gray-400 pt-4">
             Don't have an account?{' '}
             <Link href="/signup" className="font-medium text-blue-400 hover:underline">
                Sign up here
             </Link>
          </p>
        </div>
      ) : (
        // --- VIEW 2: PDF UPLOAD FORM ---
        <div className="w-full max-w-md p-8 space-y-6 bg-gray-800 rounded-lg shadow-lg">
          <div className="flex justify-between items-center">
            <h1 className="text-3xl font-bold">Polyvox</h1>
            <div>
              <a href="/dashboard" className="text-blue-400 hover:underline text-sm mr-4">
                Dashboard
              </a>
              <button onClick={handleLogout} className="text-red-400 hover:underline text-sm font-semibold">
                Logout
              </button>
            </div>
          </div>
          <p className="text-gray-400">Upload a PDF to get started</p>
          <form onSubmit={handlePdfSubmit} className="space-y-4">
            <div>
              <label htmlFor="pdf-upload" className="block text-sm font-medium text-gray-300">PDF File</label>
              <input
                id="pdf-upload"
                // name="uploaded_file" // Name is set when appending file to FormData
                type="file"
                accept=".pdf"
                required
                onChange={(e) => setFile(e.target.files ? e.target.files[0] : null)}
                className="mt-1 block w-full text-sm text-gray-400 file:mr-4 file:py-2 file:px-4 file:rounded-md file:border-0 file:text-sm file:font-semibold file:bg-blue-500 file:text-white hover:file:bg-blue-600"
              />
            </div>
            <div>
              <label htmlFor="language" className="block text-sm font-medium text-gray-300">Target Language</label>
              <select
                id="language"
                name="target_lang" // This name needs to match backend Form field
                defaultValue="es"
                className="mt-1 block w-full rounded-md border-gray-600 bg-gray-700 py-2 px-3 text-white shadow-sm"
              >
                <option value="es">Spanish</option>
                <option value="fr">French</option>
                <option value="de">German</option>
                <option value="hi">Hindi</option>
                <option value="en">English</option>
              </select>
            </div>
            <div className="flex items-center">
              <input
                id="summarize"
                name="summarize" // This name needs to match backend Form field
                type="checkbox"
                value="true" // Checkbox needs a value to be sent
                className="h-4 w-4 rounded border-gray-600 bg-gray-700 text-blue-600 focus:ring-blue-500"
              />
              <label htmlFor="summarize" className="ml-2 block text-sm text-gray-300">
                Generate audio of summary only
              </label>
            </div>
            <button type="submit" disabled={isLoading || !file} className="w-full py-2 px-4 bg-blue-600 hover:bg-blue-700 rounded-md disabled:opacity-50">
              {isLoading ? 'Processing...' : 'Generate Audio'}
            </button>
          </form>
          {(statusMessage) && (
            <div className="mt-6 p-4 bg-gray-700 rounded-md text-center">
              <p>{statusMessage}</p>
            </div>
          )}
        </div>
      )}
    </main>
  );
}