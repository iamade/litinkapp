4. Create Additional Migrations as Needed

# Create new migration for adding features
supabase migration new add_video_analytics_features

# Create migration for performance optimizations  
supabase migration new optimize_video_generation_indexes

# Create migration for new video services
supabase migration new add_new_video_services


5. Apply the Migration
# Apply migrations to local database
supabase db push

# Or if you want to reset everything and apply all migrations
supabase db reset

supabase migration repair --status reverted 20250622172107 20250622172143 20250629205410 20250629205651

updates from alpha

use loguru for logging
rewrite the config for Literal["local","staging","production"] 