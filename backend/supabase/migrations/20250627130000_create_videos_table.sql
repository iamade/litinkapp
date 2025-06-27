-- Migration: Create videos table for storing generated video metadata
create table if not exists videos (
    id uuid primary key default gen_random_uuid(),
    book_id uuid references books(id) on delete set null,
    chapter_id uuid references chapters(id) on delete set null,
    user_id uuid references profiles(id) on delete set null,
    video_url text not null,
    script text,
    character_details text,
    scene_prompt text,
    created_at bigint not null
);

-- Optional: index for fast lookup by book/chapter/user
create index if not exists idx_videos_book_id on videos(book_id);
create index if not exists idx_videos_chapter_id on videos(chapter_id);
create index if not exists idx_videos_user_id on videos(user_id); 