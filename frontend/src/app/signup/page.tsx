// frontend/src/app/signup/page.tsx
'use client';

import { useState, FormEvent } from 'react';
import Link from 'next/link'; // For linking back to login

export default function SignupPage() {
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  const handleSignup = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setIsLoading(true);
    setError(null);
    setSuccess(null);

    const formData = new FormData(event.currentTarget);
    const email = formData.get('email') as string;
    const password = formData.get('password') as string;

    // Basic validation (can add more complex checks)
    if (!email || !password || password.length < 8) {
      setError("Please provide a valid email and a password of at least 8 characters.");
      setIsLoading(false);
      return;
    }

    try {
      const res = await fetch('http://127.0.0.1:8000/users/', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email, password }),
      });

      if (res.status === 400) { // Specific check for email already registered
        const data = await res.json();
        throw new Error(data.detail || "Email already registered.");
      }
      if (!res.ok) {
        throw new Error(`Signup failed with status: ${res.status}`);
      }

      // Successful signup
      setSuccess("Account created successfully! You can now log in.");
      (event.target as HTMLFormElement).reset(); // Clear the form

    } catch (err: any) {
      setError(err.message);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <main className="flex min-h-screen flex-col items-center justify-center bg-gray-900 text-white p-8">
      <div className="w-full max-w-md p-8 space-y-6 bg-gray-800 rounded-lg shadow-lg">
        <h1 className="text-3xl font-bold text-center">Create Polyvox Account</h1>

        {/* Display Success/Error Messages */}
        {error && <p className="text-red-400 text-center bg-red-900 bg-opacity-30 p-2 rounded">{error}</p>}
        {success && <p className="text-green-400 text-center bg-green-900 bg-opacity-30 p-2 rounded">{success}</p>}

        <form onSubmit={handleSignup} className="space-y-4">
          <div>
            <label htmlFor="email">Email Address</label>
            <input
              id="email"
              name="email"
              type="email"
              required
              className="mt-1 block w-full rounded-md border-gray-600 bg-gray-700 py-2 px-3 text-white focus:border-blue-500 focus:ring-blue-500"
              disabled={isLoading || !!success} // Disable if loading or success
            />
          </div>
          <div>
            <label htmlFor="password">Password (min. 8 characters)</label>
            <input
              id="password"
              name="password"
              type="password"
              required
              minLength={8}
              className="mt-1 block w-full rounded-md border-gray-600 bg-gray-700 py-2 px-3 text-white focus:border-blue-500 focus:ring-blue-500"
              disabled={isLoading || !!success} // Disable if loading or success
            />
          </div>
          <button
            type="submit"
            disabled={isLoading || !!success} // Disable if loading or success
            className="w-full py-2 px-4 bg-blue-600 hover:bg-blue-700 rounded-md disabled:opacity-50"
          >
            {isLoading ? 'Creating Account...' : 'Sign Up'}
          </button>
        </form>

        <p className="text-center text-sm text-gray-400">
          Already have an account?{' '}
          <Link href="/" className="font-medium text-blue-400 hover:underline">
            Log in here
          </Link>
        </p>
      </div>
    </main>
  );
}