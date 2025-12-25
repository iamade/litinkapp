-- Ensure profiles has a primary key named profiles_pkey
DO $$
BEGIN
    -- Check if profiles_pkey exists
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'profiles_pkey') THEN
        -- Check if ANY primary key exists
        IF NOT EXISTS (
            SELECT 1 FROM pg_constraint 
            WHERE conrelid = 'public.profiles'::regclass 
            AND contype = 'p'
        ) THEN
            -- No PK exists, add it
            ALTER TABLE public.profiles ADD CONSTRAINT profiles_pkey PRIMARY KEY (id);
        ELSE
            -- PK exists but with different name. Rename it to profiles_pkey
            DECLARE
                existing_pk_name text;
            BEGIN
                SELECT conname INTO existing_pk_name 
                FROM pg_constraint 
                WHERE conrelid = 'public.profiles'::regclass 
                AND contype = 'p';
                
                EXECUTE 'ALTER TABLE public.profiles RENAME CONSTRAINT ' || quote_ident(existing_pk_name) || ' TO profiles_pkey';
            END;
        END IF;
    END IF;
END $$;
