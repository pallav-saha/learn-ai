-- Run this in Supabase SQL Editor (Dashboard → SQL Editor → New query)

-- Birthdays table (stores parsed birthday entries)
CREATE TABLE birthdays (
  id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE NOT NULL,
  name TEXT NOT NULL,
  phone TEXT DEFAULT '',
  birthday TEXT NOT NULL,  -- DD-MM format
  created_at TIMESTAMPTZ DEFAULT now()
);

-- Uploads table (stores raw file content for download, last 5 per user)
CREATE TABLE uploads (
  id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE NOT NULL,
  original_filename TEXT NOT NULL,
  file_content TEXT NOT NULL,
  created_at TIMESTAMPTZ DEFAULT now()
);

-- Indexes for fast queries
CREATE INDEX idx_birthdays_user_id ON birthdays(user_id);
CREATE INDEX idx_birthdays_birthday ON birthdays(birthday);
CREATE INDEX idx_uploads_user_id ON uploads(user_id);

-- Row Level Security (RLS) - users can only see their own data
ALTER TABLE birthdays ENABLE ROW LEVEL SECURITY;
ALTER TABLE uploads ENABLE ROW LEVEL SECURITY;

-- Policies: users can only CRUD their own rows
CREATE POLICY "Users can view own birthdays"
  ON birthdays FOR SELECT
  USING (auth.uid() = user_id);

CREATE POLICY "Users can insert own birthdays"
  ON birthdays FOR INSERT
  WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can delete own birthdays"
  ON birthdays FOR DELETE
  USING (auth.uid() = user_id);

CREATE POLICY "Users can view own uploads"
  ON uploads FOR SELECT
  USING (auth.uid() = user_id);

CREATE POLICY "Users can insert own uploads"
  ON uploads FOR INSERT
  WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can delete own uploads"
  ON uploads FOR DELETE
  USING (auth.uid() = user_id);
