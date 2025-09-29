-- Enable uuid-ossp extension for UUID generation
CREATE EXTENSION IF NOT EXISTS "uuid-ossp" WITH SCHEMA "extensions";

-- Create character_archetypes table
-- Stores predefined character archetypes for plot generation
CREATE TABLE IF NOT EXISTS character_archetypes (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name TEXT NOT NULL UNIQUE,
    description TEXT,
    category TEXT,
    traits JSONB,
    typical_roles JSONB,
    example_characters TEXT,
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Create plot_overviews table
-- Stores high-level plot summaries and metadata for books
CREATE TABLE IF NOT EXISTS plot_overviews (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    book_id UUID NOT NULL REFERENCES books(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    logline TEXT,
    themes JSONB,
    story_type TEXT,
    genre TEXT,
    tone TEXT,
    audience TEXT,
    setting TEXT,
    generation_method TEXT,
    model_used TEXT,
    generation_cost DECIMAL(10,4),
    status TEXT DEFAULT 'pending',
    version INTEGER DEFAULT 1,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    CONSTRAINT unique_book_user_version UNIQUE(book_id, user_id, version)
);

-- Create characters table
-- Stores character details for plot generation
CREATE TABLE IF NOT EXISTS characters (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    plot_overview_id UUID NOT NULL REFERENCES plot_overviews(id) ON DELETE CASCADE,
    book_id UUID NOT NULL REFERENCES books(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    role TEXT,
    character_arc TEXT,
    physical_description TEXT,
    personality TEXT,
    archetypes JSONB,
    want TEXT,
    need TEXT,
    lie TEXT,
    ghost TEXT,
    image_url TEXT,
    image_generation_prompt TEXT,
    image_metadata JSONB,
    generation_method TEXT,
    model_used TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    CONSTRAINT unique_plot_overview_name UNIQUE(plot_overview_id, name)
);

-- Create chapter_scripts table
-- Stores enhanced chapter scripts with plot and character integration
CREATE TABLE IF NOT EXISTS chapter_scripts (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    chapter_id UUID NOT NULL REFERENCES chapters(id) ON DELETE CASCADE,
    plot_overview_id UUID REFERENCES plot_overviews(id) ON DELETE CASCADE,
    script_id UUID REFERENCES scripts(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    plot_enhanced BOOLEAN DEFAULT false,
    character_enhanced BOOLEAN DEFAULT false,
    scenes JSONB,
    acts JSONB,
    beats JSONB,
    character_details JSONB,
    character_arcs JSONB,
    status TEXT DEFAULT 'pending',
    version INTEGER DEFAULT 1,
    generation_metadata JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Create indexes for plot_overviews
CREATE INDEX idx_plot_overviews_book_user ON plot_overviews(book_id, user_id);
CREATE INDEX idx_plot_overviews_status ON plot_overviews(status);
CREATE INDEX idx_plot_overviews_created_at ON plot_overviews(created_at);

-- Create indexes for characters
CREATE INDEX idx_characters_plot_overview ON characters(plot_overview_id);
CREATE INDEX idx_characters_book_user ON characters(book_id, user_id);
CREATE INDEX idx_characters_role ON characters(role);
CREATE INDEX idx_characters_archetypes ON characters USING GIN(archetypes);

-- Create indexes for chapter_scripts
CREATE INDEX idx_chapter_scripts_chapter ON chapter_scripts(chapter_id);
CREATE INDEX idx_chapter_scripts_plot ON chapter_scripts(plot_overview_id);
CREATE INDEX idx_chapter_scripts_user ON chapter_scripts(user_id);
CREATE INDEX idx_chapter_scripts_status ON chapter_scripts(status);

-- Create indexes for character_archetypes
CREATE INDEX idx_character_archetypes_category ON character_archetypes(category);
CREATE INDEX idx_character_archetypes_active ON character_archetypes(is_active);

-- Create function to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Create triggers for updated_at
CREATE TRIGGER update_plot_overviews_updated_at BEFORE UPDATE
    ON plot_overviews FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_characters_updated_at BEFORE UPDATE
    ON characters FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_chapter_scripts_updated_at BEFORE UPDATE
    ON chapter_scripts FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_character_archetypes_updated_at BEFORE UPDATE
    ON character_archetypes FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Enable Row Level Security
ALTER TABLE plot_overviews ENABLE ROW LEVEL SECURITY;
ALTER TABLE characters ENABLE ROW LEVEL SECURITY;
ALTER TABLE chapter_scripts ENABLE ROW LEVEL SECURITY;
ALTER TABLE character_archetypes ENABLE ROW LEVEL SECURITY;

-- RLS Policies for plot_overviews
CREATE POLICY "Users can view own plot overviews" ON plot_overviews
    FOR SELECT USING (auth.uid() = user_id);

CREATE POLICY "Users can insert own plot overviews" ON plot_overviews
    FOR INSERT WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can update own plot overviews" ON plot_overviews
    FOR UPDATE USING (auth.uid() = user_id);

CREATE POLICY "Users can delete own plot overviews" ON plot_overviews
    FOR DELETE USING (auth.uid() = user_id);

CREATE POLICY "Service role full access to plot overviews" ON plot_overviews
    FOR ALL USING (auth.jwt() ->> 'role' = 'service_role');

-- RLS Policies for characters
CREATE POLICY "Users can view own characters" ON characters
    FOR SELECT USING (auth.uid() = user_id);

CREATE POLICY "Users can insert own characters" ON characters
    FOR INSERT WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can update own characters" ON characters
    FOR UPDATE USING (auth.uid() = user_id);

CREATE POLICY "Users can delete own characters" ON characters
    FOR DELETE USING (auth.uid() = user_id);

CREATE POLICY "Service role full access to characters" ON characters
    FOR ALL USING (auth.jwt() ->> 'role' = 'service_role');

-- RLS Policies for chapter_scripts
CREATE POLICY "Users can view own chapter scripts" ON chapter_scripts
    FOR SELECT USING (auth.uid() = user_id);

CREATE POLICY "Users can insert own chapter scripts" ON chapter_scripts
    FOR INSERT WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can update own chapter scripts" ON chapter_scripts
    FOR UPDATE USING (auth.uid() = user_id);

CREATE POLICY "Users can delete own chapter scripts" ON chapter_scripts
    FOR DELETE USING (auth.uid() = user_id);

CREATE POLICY "Service role full access to chapter scripts" ON chapter_scripts
    FOR ALL USING (auth.jwt() ->> 'role' = 'service_role');

-- RLS Policies for character_archetypes
CREATE POLICY "Everyone can view active character archetypes" ON character_archetypes
    FOR SELECT USING (is_active = true);

CREATE POLICY "Service role full access to character archetypes" ON character_archetypes
    FOR ALL USING (auth.jwt() ->> 'role' = 'service_role');