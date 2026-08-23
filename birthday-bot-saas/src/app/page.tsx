import Link from "next/link";

export default function Home() {
  return (
    <div className="min-h-screen flex flex-col items-center justify-center p-8">
      <div className="max-w-md w-full text-center space-y-8">
        <div>
          <h1 className="text-4xl font-bold text-gray-900">🎂 Birthday Bot</h1>
          <p className="mt-3 text-gray-600">
            Never miss a birthday again. Upload your contacts and get email
            reminders automatically.
          </p>
        </div>

        <div className="space-y-4">
          <Link
            href="/login"
            className="block w-full bg-indigo-600 text-white py-3 px-4 rounded-lg font-medium hover:bg-indigo-700 transition"
          >
            Log In
          </Link>
          <Link
            href="/signup"
            className="block w-full bg-white text-indigo-600 py-3 px-4 rounded-lg font-medium border border-indigo-600 hover:bg-indigo-50 transition"
          >
            Sign Up
          </Link>
        </div>

        <div className="text-sm text-gray-500 space-y-2">
          <p>✅ Free forever</p>
          <p>✅ Monthly summary + daily reminders</p>
          <p>✅ Upload CSV, Excel, or JSON</p>
        </div>
      </div>
    </div>
  );
}
