"use client";

import { useState, useEffect, useCallback } from "react";
import { createClient } from "@/lib/supabase";
import { useRouter } from "next/navigation";
import * as XLSX from "xlsx";

interface Upload {
  id: string;
  original_filename: string;
  file_content: string;
  created_at: string;
}

interface Birthday {
  id: string;
  name: string;
  phone: string;
  birthday: string;
}

export default function Dashboard() {
  const [file, setFile] = useState<File | null>(null);
  const [uploading, setUploading] = useState(false);
  const [message, setMessage] = useState("");
  const [uploads, setUploads] = useState<Upload[]>([]);
  const [birthdays, setBirthdays] = useState<Birthday[]>([]);
  const [userEmail, setUserEmail] = useState("");
  const router = useRouter();
  const supabase = createClient();

  const loadData = useCallback(async () => {
    const { data: { user } } = await supabase.auth.getUser();
    if (!user) {
      router.push("/login");
      return;
    }
    setUserEmail(user.email || "");

    // Load recent uploads
    const { data: uploadData } = await supabase
      .from("uploads")
      .select("*")
      .eq("user_id", user.id)
      .order("created_at", { ascending: false })
      .limit(5);

    if (uploadData) setUploads(uploadData);

    // Load current birthdays
    const { data: birthdayData } = await supabase
      .from("birthdays")
      .select("*")
      .eq("user_id", user.id)
      .order("birthday", { ascending: true });

    if (birthdayData) setBirthdays(birthdayData);
  }, [supabase, router]);

  useEffect(() => {
    loadData();
  }, [loadData]);

  const handleUpload = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!file) return;

    setUploading(true);
    setMessage("");

    try {
      let entries: { name: string; phone: string; birthday: string }[];
      let fileContentToStore: string;

      // Parse file based on type
      if (file.name.endsWith(".json")) {
        const text = await file.text();
        entries = JSON.parse(text);
        fileContentToStore = text;
      } else if (file.name.endsWith(".csv")) {
        const text = await file.text();
        // Simple CSV parser (name,phone,birthday)
        const lines = text.trim().split("\n");
        const header = lines[0].toLowerCase();
        const hasHeader = header.includes("name") || header.includes("phone");
        const dataLines = hasHeader ? lines.slice(1) : lines;

        entries = dataLines.map((line) => {
          const [name, phone, birthday] = line.split(",").map((s) => s.trim());
          return { name, phone, birthday };
        });
        fileContentToStore = text;
      } else if (file.name.endsWith(".xlsx") || file.name.endsWith(".xls")) {
        // Parse Excel file
        const buffer = await file.arrayBuffer();
        const workbook = XLSX.read(buffer, { type: "array" });
        const sheet = workbook.Sheets[workbook.SheetNames[0]];
        const rows = XLSX.utils.sheet_to_json<Record<string, string>>(sheet);

        entries = rows.map((row) => {
          // Try common column name variations
          const name = row["Name"] || row["name"] || row["NAME"] || "";
          const phone = row["Phone"] || row["phone"] || row["PHONE"] || row["Mobile"] || row["mobile"] || "";
          const birthday = row["Birthday"] || row["birthday"] || row["BIRTHDAY"] || row["DOB"] || row["dob"] || "";
          return { name: String(name), phone: String(phone), birthday: String(birthday) };
        });

        // Store as JSON for download later
        fileContentToStore = JSON.stringify(entries, null, 2);
      } else {
        setMessage("Please upload a .json, .csv, or .xlsx file");
        setUploading(false);
        return;
      }

      // Validate entries
      if (!entries || entries.length === 0) {
        setMessage("File is empty or invalid format");
        setUploading(false);
        return;
      }

      const { data: { user } } = await supabase.auth.getUser();
      if (!user) return;

      // 1. Save the upload (keep last 5)
      await supabase.from("uploads").insert({
        user_id: user.id,
        original_filename: file.name,
        file_content: fileContentToStore,
      });

      // Delete old uploads beyond 5
      const { data: allUploads } = await supabase
        .from("uploads")
        .select("id")
        .eq("user_id", user.id)
        .order("created_at", { ascending: false });

      if (allUploads && allUploads.length > 5) {
        const idsToDelete = allUploads.slice(5).map((u) => u.id);
        await supabase.from("uploads").delete().in("id", idsToDelete);
      }

      // 2. Replace all birthdays (delete old, insert new)
      await supabase.from("birthdays").delete().eq("user_id", user.id);

      const birthdayRows = entries.map((entry) => ({
        user_id: user.id,
        name: entry.name,
        phone: entry.phone || "",
        birthday: entry.birthday,
      }));

      await supabase.from("birthdays").insert(birthdayRows);

      setMessage(`✅ Uploaded ${entries.length} contacts successfully!`);
      setFile(null);
      loadData();
    } catch (err) {
      setMessage(`❌ Error: ${err instanceof Error ? err.message : "Invalid file format"}`);
    }

    setUploading(false);
  };

  const handleDownload = (upload: Upload) => {
    const blob = new Blob([upload.file_content], { type: "text/plain" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = upload.original_filename;
    a.click();
    URL.revokeObjectURL(url);
  };

  const handleDeleteAll = async () => {
    const confirmed = window.confirm(
      "Are you sure you want to delete ALL your data? This removes your birthday list and all past uploads. This cannot be undone."
    );
    if (!confirmed) return;

    const { data: { user } } = await supabase.auth.getUser();
    if (!user) return;

    await supabase.from("birthdays").delete().eq("user_id", user.id);
    await supabase.from("uploads").delete().eq("user_id", user.id);

    setMessage("🗑️ All your data has been deleted.");
    setBirthdays([]);
    setUploads([]);
  };

  const handleLogout = async () => {
    await supabase.auth.signOut();
    router.push("/");
  };

  return (
    <div className="min-h-screen p-8 max-w-4xl mx-auto">
      {/* Header */}
      <div className="flex justify-between items-center mb-8">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">🎂 Dashboard</h1>
          <p className="text-sm text-gray-500">{userEmail}</p>
        </div>
        <button
          onClick={handleLogout}
          className="text-sm text-gray-600 hover:text-red-600 transition"
        >
          Log out
        </button>
      </div>

      {/* Upload Section */}
      <div className="bg-white rounded-xl shadow-sm border p-6 mb-8">
        <h2 className="text-lg font-semibold text-gray-900 mb-4">
          Upload Birthday List
        </h2>
        <p className="text-sm text-gray-500 mb-4">
          Upload a CSV, JSON, or Excel (.xlsx) file with columns: name, phone, birthday (DD-MM format).
          This replaces your current list.
        </p>

        <form onSubmit={handleUpload} className="flex gap-4 items-end">
          <div className="flex-1">
            <input
              type="file"
              accept=".json,.csv,.xlsx,.xls"
              onChange={(e) => setFile(e.target.files?.[0] || null)}
              className="w-full text-sm text-gray-500 file:mr-4 file:py-2 file:px-4 file:rounded-lg file:border-0 file:bg-indigo-50 file:text-indigo-700 hover:file:bg-indigo-100"
            />
          </div>
          <button
            type="submit"
            disabled={!file || uploading}
            className="bg-indigo-600 text-white py-2 px-6 rounded-lg font-medium hover:bg-indigo-700 transition disabled:opacity-50"
          >
            {uploading ? "Uploading..." : "Upload"}
          </button>
        </form>

        {message && (
          <p className="mt-3 text-sm">{message}</p>
        )}
      </div>

      {/* Current Birthdays */}
      <div className="bg-white rounded-xl shadow-sm border p-6 mb-8">
        <h2 className="text-lg font-semibold text-gray-900 mb-4">
          Current Birthday List ({birthdays.length} contacts)
        </h2>

        {birthdays.length === 0 ? (
          <p className="text-gray-500 text-sm">No birthdays uploaded yet. Upload a file above.</p>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b text-left text-gray-500">
                  <th className="py-2 pr-4">Name</th>
                  <th className="py-2 pr-4">Phone</th>
                  <th className="py-2">Birthday</th>
                </tr>
              </thead>
              <tbody>
                {birthdays.map((b) => (
                  <tr key={b.id} className="border-b last:border-0">
                    <td className="py-2 pr-4">{b.name}</td>
                    <td className="py-2 pr-4 text-gray-500">{b.phone}</td>
                    <td className="py-2">{b.birthday}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Past Uploads */}
      <div className="bg-white rounded-xl shadow-sm border p-6 mb-8">
        <h2 className="text-lg font-semibold text-gray-900 mb-4">
          Past Uploads (last 5)
        </h2>

        {uploads.length === 0 ? (
          <p className="text-gray-500 text-sm">No uploads yet.</p>
        ) : (
          <div className="space-y-3">
            {uploads.map((upload) => (
              <div
                key={upload.id}
                className="flex justify-between items-center py-2 border-b last:border-0"
              >
                <div>
                  <p className="text-sm font-medium text-gray-900">
                    {upload.original_filename}
                  </p>
                  <p className="text-xs text-gray-500">
                    {new Date(upload.created_at).toLocaleDateString("en-IN", {
                      day: "numeric",
                      month: "short",
                      year: "numeric",
                      hour: "2-digit",
                      minute: "2-digit",
                    })}
                  </p>
                </div>
                <button
                  onClick={() => handleDownload(upload)}
                  className="text-indigo-600 text-sm hover:underline"
                >
                  Download
                </button>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Danger Zone */}
      <div className="bg-white rounded-xl shadow-sm border border-red-200 p-6">
        <h2 className="text-lg font-semibold text-red-700 mb-2">Danger Zone</h2>
        <p className="text-sm text-gray-500 mb-4">
          Delete all your birthday data and upload history. This cannot be undone.
        </p>
        <button
          onClick={handleDeleteAll}
          className="bg-red-600 text-white py-2 px-4 rounded-lg text-sm font-medium hover:bg-red-700 transition"
        >
          Delete All My Data
        </button>
      </div>
    </div>
  );
}
