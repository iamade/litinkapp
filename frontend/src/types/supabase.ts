export type Json =
  | string
  | number
  | boolean
  | null
  | { [key: string]: Json | undefined }
  | Json[]

export type Database = {
  // Allows to automatically instantiate createClient with right options
  // instead of createClient<Database, { PostgrestVersion: 'XX' }>(URL, KEY)
  __InternalSupabase: {
    PostgrestVersion: "12.2.3 (519615d)"
  }
  graphql_public: {
    Tables: {
      [_ in never]: never
    }
    Views: {
      [_ in never]: never
    }
    Functions: {
      graphql: {
        Args: {
          extensions?: Json
          operationName?: string
          query?: string
          variables?: Json
        }
        Returns: Json
      }
    }
    Enums: {
      [_ in never]: never
    }
    CompositeTypes: {
      [_ in never]: never
    }
  }
  public: {
    Tables: {
      audio_generations: {
        Row: {
          audio_format: string | null
          audio_length_seconds: number | null
          audio_type: Database["public"]["Enums"]["audio_type"]
          audio_url: string | null
          character_name: string | null
          created_at: string | null
          duration: number | null
          duration_seconds: number | null
          error_message: string | null
          file_size_bytes: number | null
          generation_status: string | null
          generation_time_seconds: number | null
          id: string
          metadata: Json | null
          model_id: string | null
          scene_id: string | null
          sequence_order: number | null
          service_provider: string | null
          status: string | null
          text_content: string | null
          video_generation_id: string | null
          voice_id: string | null
          voice_model: string | null
        }
        Insert: {
          audio_format?: string | null
          audio_length_seconds?: number | null
          audio_type: Database["public"]["Enums"]["audio_type"]
          audio_url?: string | null
          character_name?: string | null
          created_at?: string | null
          duration?: number | null
          duration_seconds?: number | null
          error_message?: string | null
          file_size_bytes?: number | null
          generation_status?: string | null
          generation_time_seconds?: number | null
          id?: string
          metadata?: Json | null
          model_id?: string | null
          scene_id?: string | null
          sequence_order?: number | null
          service_provider?: string | null
          status?: string | null
          text_content?: string | null
          video_generation_id?: string | null
          voice_id?: string | null
          voice_model?: string | null
        }
        Update: {
          audio_format?: string | null
          audio_length_seconds?: number | null
          audio_type?: Database["public"]["Enums"]["audio_type"]
          audio_url?: string | null
          character_name?: string | null
          created_at?: string | null
          duration?: number | null
          duration_seconds?: number | null
          error_message?: string | null
          file_size_bytes?: number | null
          generation_status?: string | null
          generation_time_seconds?: number | null
          id?: string
          metadata?: Json | null
          model_id?: string | null
          scene_id?: string | null
          sequence_order?: number | null
          service_provider?: string | null
          status?: string | null
          text_content?: string | null
          video_generation_id?: string | null
          voice_id?: string | null
          voice_model?: string | null
        }
        Relationships: [
          {
            foreignKeyName: "audio_generations_video_generation_id_fkey"
            columns: ["video_generation_id"]
            isOneToOne: false
            referencedRelation: "video_generations"
            referencedColumns: ["id"]
          },
        ]
      }
      badges: {
        Row: {
          created_at: string | null
          criteria: string
          description: string
          id: string
          image_url: string | null
          name: string
          points: number | null
          rarity: Database["public"]["Enums"]["badge_rarity"] | null
        }
        Insert: {
          created_at?: string | null
          criteria: string
          description: string
          id?: string
          image_url?: string | null
          name: string
          points?: number | null
          rarity?: Database["public"]["Enums"]["badge_rarity"] | null
        }
        Update: {
          created_at?: string | null
          criteria?: string
          description?: string
          id?: string
          image_url?: string | null
          name?: string
          points?: number | null
          rarity?: Database["public"]["Enums"]["badge_rarity"] | null
        }
        Relationships: []
      }
      book_embeddings: {
        Row: {
          book_id: string | null
          chunk_index: number
          chunk_size: number
          chunk_type: string
          content_chunk: string
          created_at: string | null
          embedding: string | null
          id: string
          metadata: Json | null
          updated_at: string | null
        }
        Insert: {
          book_id?: string | null
          chunk_index: number
          chunk_size: number
          chunk_type: string
          content_chunk: string
          created_at?: string | null
          embedding?: string | null
          id?: string
          metadata?: Json | null
          updated_at?: string | null
        }
        Update: {
          book_id?: string | null
          chunk_index?: number
          chunk_size?: number
          chunk_type?: string
          content_chunk?: string
          created_at?: string | null
          embedding?: string | null
          id?: string
          metadata?: Json | null
          updated_at?: string | null
        }
        Relationships: [
          {
            foreignKeyName: "book_embeddings_book_id_fkey"
            columns: ["book_id"]
            isOneToOne: false
            referencedRelation: "books"
            referencedColumns: ["id"]
          },
        ]
      }
      book_sections: {
        Row: {
          book_id: string | null
          created_at: string | null
          description: string | null
          id: string
          order_index: number
          section_number: string
          section_type: string
          title: string
          updated_at: string | null
        }
        Insert: {
          book_id?: string | null
          created_at?: string | null
          description?: string | null
          id?: string
          order_index: number
          section_number: string
          section_type: string
          title: string
          updated_at?: string | null
        }
        Update: {
          book_id?: string | null
          created_at?: string | null
          description?: string | null
          id?: string
          order_index?: number
          section_number?: string
          section_type?: string
          title?: string
          updated_at?: string | null
        }
        Relationships: [
          {
            foreignKeyName: "book_sections_book_id_fkey"
            columns: ["book_id"]
            isOneToOne: false
            referencedRelation: "books"
            referencedColumns: ["id"]
          },
        ]
      }
      books: {
        Row: {
          author_name: string | null
          book_type: Database["public"]["Enums"]["book_type"]
          content: string | null
          cover_image_path: string | null
          cover_image_url: string | null
          created_at: string | null
          description: string | null
          difficulty: Database["public"]["Enums"]["difficulty_level"] | null
          error_message: string | null
          estimated_duration: number | null
          has_sections: boolean | null
          id: string
          language: string | null
          original_file_storage_path: string | null
          payment_status: string | null
          progress: number | null
          progress_message: string | null
          status: Database["public"]["Enums"]["book_status"] | null
          stripe_checkout_session_id: string | null
          stripe_customer_id: string | null
          stripe_payment_intent_id: string | null
          structure_type: string | null
          tags: string[] | null
          title: string
          total_chapters: number | null
          total_steps: number | null
          updated_at: string | null
          user_id: string | null
        }
        Insert: {
          author_name?: string | null
          book_type: Database["public"]["Enums"]["book_type"]
          content?: string | null
          cover_image_path?: string | null
          cover_image_url?: string | null
          created_at?: string | null
          description?: string | null
          difficulty?: Database["public"]["Enums"]["difficulty_level"] | null
          error_message?: string | null
          estimated_duration?: number | null
          has_sections?: boolean | null
          id?: string
          language?: string | null
          original_file_storage_path?: string | null
          payment_status?: string | null
          progress?: number | null
          progress_message?: string | null
          status?: Database["public"]["Enums"]["book_status"] | null
          stripe_checkout_session_id?: string | null
          stripe_customer_id?: string | null
          stripe_payment_intent_id?: string | null
          structure_type?: string | null
          tags?: string[] | null
          title: string
          total_chapters?: number | null
          total_steps?: number | null
          updated_at?: string | null
          user_id?: string | null
        }
        Update: {
          author_name?: string | null
          book_type?: Database["public"]["Enums"]["book_type"]
          content?: string | null
          cover_image_path?: string | null
          cover_image_url?: string | null
          created_at?: string | null
          description?: string | null
          difficulty?: Database["public"]["Enums"]["difficulty_level"] | null
          error_message?: string | null
          estimated_duration?: number | null
          has_sections?: boolean | null
          id?: string
          language?: string | null
          original_file_storage_path?: string | null
          payment_status?: string | null
          progress?: number | null
          progress_message?: string | null
          status?: Database["public"]["Enums"]["book_status"] | null
          stripe_checkout_session_id?: string | null
          stripe_customer_id?: string | null
          stripe_payment_intent_id?: string | null
          structure_type?: string | null
          tags?: string[] | null
          title?: string
          total_chapters?: number | null
          total_steps?: number | null
          updated_at?: string | null
          user_id?: string | null
        }
        Relationships: [
          {
            foreignKeyName: "books_author_id_fkey"
            columns: ["user_id"]
            isOneToOne: false
            referencedRelation: "profiles"
            referencedColumns: ["id"]
          },
        ]
      }
      chapter_embeddings: {
        Row: {
          book_id: string | null
          chapter_id: string | null
          chunk_index: number
          chunk_size: number
          content_chunk: string
          created_at: string | null
          embedding: string | null
          id: string
          metadata: Json | null
          updated_at: string | null
        }
        Insert: {
          book_id?: string | null
          chapter_id?: string | null
          chunk_index: number
          chunk_size: number
          content_chunk: string
          created_at?: string | null
          embedding?: string | null
          id?: string
          metadata?: Json | null
          updated_at?: string | null
        }
        Update: {
          book_id?: string | null
          chapter_id?: string | null
          chunk_index?: number
          chunk_size?: number
          content_chunk?: string
          created_at?: string | null
          embedding?: string | null
          id?: string
          metadata?: Json | null
          updated_at?: string | null
        }
        Relationships: [
          {
            foreignKeyName: "chapter_embeddings_book_id_fkey"
            columns: ["book_id"]
            isOneToOne: false
            referencedRelation: "books"
            referencedColumns: ["id"]
          },
          {
            foreignKeyName: "chapter_embeddings_chapter_id_fkey"
            columns: ["chapter_id"]
            isOneToOne: false
            referencedRelation: "chapters"
            referencedColumns: ["id"]
          },
        ]
      }
      chapter_scripts: {
        Row: {
          acts: Json | null
          beats: Json | null
          chapter_id: string
          character_arcs: Json | null
          character_details: Json | null
          character_enhanced: boolean | null
          created_at: string | null
          generation_metadata: Json | null
          id: string
          plot_enhanced: boolean | null
          plot_overview_id: string | null
          scenes: Json | null
          script_id: string | null
          status: string | null
          updated_at: string | null
          user_id: string
          version: number | null
        }
        Insert: {
          acts?: Json | null
          beats?: Json | null
          chapter_id: string
          character_arcs?: Json | null
          character_details?: Json | null
          character_enhanced?: boolean | null
          created_at?: string | null
          generation_metadata?: Json | null
          id?: string
          plot_enhanced?: boolean | null
          plot_overview_id?: string | null
          scenes?: Json | null
          script_id?: string | null
          status?: string | null
          updated_at?: string | null
          user_id: string
          version?: number | null
        }
        Update: {
          acts?: Json | null
          beats?: Json | null
          chapter_id?: string
          character_arcs?: Json | null
          character_details?: Json | null
          character_enhanced?: boolean | null
          created_at?: string | null
          generation_metadata?: Json | null
          id?: string
          plot_enhanced?: boolean | null
          plot_overview_id?: string | null
          scenes?: Json | null
          script_id?: string | null
          status?: string | null
          updated_at?: string | null
          user_id?: string
          version?: number | null
        }
        Relationships: [
          {
            foreignKeyName: "chapter_scripts_chapter_id_fkey"
            columns: ["chapter_id"]
            isOneToOne: false
            referencedRelation: "chapters"
            referencedColumns: ["id"]
          },
          {
            foreignKeyName: "chapter_scripts_plot_overview_id_fkey"
            columns: ["plot_overview_id"]
            isOneToOne: false
            referencedRelation: "plot_overviews"
            referencedColumns: ["id"]
          },
          {
            foreignKeyName: "chapter_scripts_script_id_fkey"
            columns: ["script_id"]
            isOneToOne: false
            referencedRelation: "scripts"
            referencedColumns: ["id"]
          },
        ]
      }
      chapters: {
        Row: {
          ai_generated_content: Json | null
          book_id: string | null
          chapter_number: number
          content: string
          created_at: string | null
          duration: number | null
          id: string
          order_index: number | null
          section_id: string | null
          summary: string | null
          title: string
          updated_at: string | null
        }
        Insert: {
          ai_generated_content?: Json | null
          book_id?: string | null
          chapter_number: number
          content: string
          created_at?: string | null
          duration?: number | null
          id?: string
          order_index?: number | null
          section_id?: string | null
          summary?: string | null
          title: string
          updated_at?: string | null
        }
        Update: {
          ai_generated_content?: Json | null
          book_id?: string | null
          chapter_number?: number
          content?: string
          created_at?: string | null
          duration?: number | null
          id?: string
          order_index?: number | null
          section_id?: string | null
          summary?: string | null
          title?: string
          updated_at?: string | null
        }
        Relationships: [
          {
            foreignKeyName: "chapters_book_id_fkey"
            columns: ["book_id"]
            isOneToOne: false
            referencedRelation: "books"
            referencedColumns: ["id"]
          },
          {
            foreignKeyName: "chapters_section_id_fkey"
            columns: ["section_id"]
            isOneToOne: false
            referencedRelation: "book_sections"
            referencedColumns: ["id"]
          },
        ]
      }
      character_archetypes: {
        Row: {
          category: string | null
          created_at: string | null
          description: string | null
          example_characters: string | null
          id: string
          is_active: boolean | null
          name: string
          traits: Json | null
          typical_roles: Json | null
          updated_at: string | null
        }
        Insert: {
          category?: string | null
          created_at?: string | null
          description?: string | null
          example_characters?: string | null
          id?: string
          is_active?: boolean | null
          name: string
          traits?: Json | null
          typical_roles?: Json | null
          updated_at?: string | null
        }
        Update: {
          category?: string | null
          created_at?: string | null
          description?: string | null
          example_characters?: string | null
          id?: string
          is_active?: boolean | null
          name?: string
          traits?: Json | null
          typical_roles?: Json | null
          updated_at?: string | null
        }
        Relationships: []
      }
      characters: {
        Row: {
          archetypes: Json | null
          book_id: string
          character_arc: string | null
          created_at: string | null
          generation_method: string | null
          ghost: string | null
          id: string
          image_generation_prompt: string | null
          image_metadata: Json | null
          image_url: string | null
          lie: string | null
          model_used: string | null
          name: string
          need: string | null
          personality: string | null
          physical_description: string | null
          plot_overview_id: string
          role: string | null
          updated_at: string | null
          user_id: string
          want: string | null
        }
        Insert: {
          archetypes?: Json | null
          book_id: string
          character_arc?: string | null
          created_at?: string | null
          generation_method?: string | null
          ghost?: string | null
          id?: string
          image_generation_prompt?: string | null
          image_metadata?: Json | null
          image_url?: string | null
          lie?: string | null
          model_used?: string | null
          name: string
          need?: string | null
          personality?: string | null
          physical_description?: string | null
          plot_overview_id: string
          role?: string | null
          updated_at?: string | null
          user_id: string
          want?: string | null
        }
        Update: {
          archetypes?: Json | null
          book_id?: string
          character_arc?: string | null
          created_at?: string | null
          generation_method?: string | null
          ghost?: string | null
          id?: string
          image_generation_prompt?: string | null
          image_metadata?: Json | null
          image_url?: string | null
          lie?: string | null
          model_used?: string | null
          name?: string
          need?: string | null
          personality?: string | null
          physical_description?: string | null
          plot_overview_id?: string
          role?: string | null
          updated_at?: string | null
          user_id?: string
          want?: string | null
        }
        Relationships: [
          {
            foreignKeyName: "characters_book_id_fkey"
            columns: ["book_id"]
            isOneToOne: false
            referencedRelation: "books"
            referencedColumns: ["id"]
          },
          {
            foreignKeyName: "characters_plot_overview_id_fkey"
            columns: ["plot_overview_id"]
            isOneToOne: false
            referencedRelation: "plot_overviews"
            referencedColumns: ["id"]
          },
        ]
      }
      image_generations: {
        Row: {
          aspect_ratio: string | null
          batch_index: number | null
          character_name: string | null
          created_at: string | null
          enhancement_type: string | null
          error_message: string | null
          fetch_url: string | null
          file_size_bytes: number | null
          generation_time_seconds: number | null
          height: number | null
          id: string
          image_prompt: string | null
          image_type: string | null
          image_url: string | null
          metadata: Json | null
          model_id: string | null
          prompt: string | null
          request_id: string | null
          scene_description: string | null
          scene_id: string | null
          scene_number: number | null
          sequence_order: number | null
          service_provider: string | null
          shot_index: number | null
          status: string | null
          style: string | null
          text_prompt: string | null
          thumbnail_url: string | null
          video_generation_id: string | null
          width: number | null
        }
        Insert: {
          aspect_ratio?: string | null
          batch_index?: number | null
          character_name?: string | null
          created_at?: string | null
          enhancement_type?: string | null
          error_message?: string | null
          fetch_url?: string | null
          file_size_bytes?: number | null
          generation_time_seconds?: number | null
          height?: number | null
          id?: string
          image_prompt?: string | null
          image_type?: string | null
          image_url?: string | null
          metadata?: Json | null
          model_id?: string | null
          prompt?: string | null
          request_id?: string | null
          scene_description?: string | null
          scene_id?: string | null
          scene_number?: number | null
          sequence_order?: number | null
          service_provider?: string | null
          shot_index?: number | null
          status?: string | null
          style?: string | null
          text_prompt?: string | null
          thumbnail_url?: string | null
          video_generation_id?: string | null
          width?: number | null
        }
        Update: {
          aspect_ratio?: string | null
          batch_index?: number | null
          character_name?: string | null
          created_at?: string | null
          enhancement_type?: string | null
          error_message?: string | null
          fetch_url?: string | null
          file_size_bytes?: number | null
          generation_time_seconds?: number | null
          height?: number | null
          id?: string
          image_prompt?: string | null
          image_type?: string | null
          image_url?: string | null
          metadata?: Json | null
          model_id?: string | null
          prompt?: string | null
          request_id?: string | null
          scene_description?: string | null
          scene_id?: string | null
          scene_number?: number | null
          sequence_order?: number | null
          service_provider?: string | null
          shot_index?: number | null
          status?: string | null
          style?: string | null
          text_prompt?: string | null
          thumbnail_url?: string | null
          video_generation_id?: string | null
          width?: number | null
        }
        Relationships: [
          {
            foreignKeyName: "image_generations_video_generation_id_fkey"
            columns: ["video_generation_id"]
            isOneToOne: false
            referencedRelation: "video_generations"
            referencedColumns: ["id"]
          },
        ]
      }
      learning_content: {
        Row: {
          book_id: string | null
          chapter_id: string | null
          combined_video_url: string | null
          content_type: string
          content_url: string | null
          created_at: string | null
          duration: number | null
          error_message: string | null
          generation_progress: string | null
          id: string
          script: string | null
          status: string | null
          tavus_response: Json | null
          tavus_url: string | null
          tavus_video_id: string | null
          updated_at: string | null
          user_id: string | null
          video_segments: Json | null
        }
        Insert: {
          book_id?: string | null
          chapter_id?: string | null
          combined_video_url?: string | null
          content_type: string
          content_url?: string | null
          created_at?: string | null
          duration?: number | null
          error_message?: string | null
          generation_progress?: string | null
          id?: string
          script?: string | null
          status?: string | null
          tavus_response?: Json | null
          tavus_url?: string | null
          tavus_video_id?: string | null
          updated_at?: string | null
          user_id?: string | null
          video_segments?: Json | null
        }
        Update: {
          book_id?: string | null
          chapter_id?: string | null
          combined_video_url?: string | null
          content_type?: string
          content_url?: string | null
          created_at?: string | null
          duration?: number | null
          error_message?: string | null
          generation_progress?: string | null
          id?: string
          script?: string | null
          status?: string | null
          tavus_response?: Json | null
          tavus_url?: string | null
          tavus_video_id?: string | null
          updated_at?: string | null
          user_id?: string | null
          video_segments?: Json | null
        }
        Relationships: [
          {
            foreignKeyName: "learning_content_book_id_fkey"
            columns: ["book_id"]
            isOneToOne: false
            referencedRelation: "books"
            referencedColumns: ["id"]
          },
          {
            foreignKeyName: "learning_content_chapter_id_fkey"
            columns: ["chapter_id"]
            isOneToOne: false
            referencedRelation: "chapters"
            referencedColumns: ["id"]
          },
        ]
      }
      nft_collectibles: {
        Row: {
          animation_url: string | null
          book_id: string | null
          chapter_id: string | null
          created_at: string | null
          description: string
          id: string
          image_url: string | null
          name: string
          rarity: Database["public"]["Enums"]["badge_rarity"] | null
          story_moment: string
        }
        Insert: {
          animation_url?: string | null
          book_id?: string | null
          chapter_id?: string | null
          created_at?: string | null
          description: string
          id?: string
          image_url?: string | null
          name: string
          rarity?: Database["public"]["Enums"]["badge_rarity"] | null
          story_moment: string
        }
        Update: {
          animation_url?: string | null
          book_id?: string | null
          chapter_id?: string | null
          created_at?: string | null
          description?: string
          id?: string
          image_url?: string | null
          name?: string
          rarity?: Database["public"]["Enums"]["badge_rarity"] | null
          story_moment?: string
        }
        Relationships: [
          {
            foreignKeyName: "nft_collectibles_book_id_fkey"
            columns: ["book_id"]
            isOneToOne: false
            referencedRelation: "books"
            referencedColumns: ["id"]
          },
          {
            foreignKeyName: "nft_collectibles_chapter_id_fkey"
            columns: ["chapter_id"]
            isOneToOne: false
            referencedRelation: "chapters"
            referencedColumns: ["id"]
          },
        ]
      }
      pipeline_steps: {
        Row: {
          completed_at: string | null
          created_at: string | null
          error_message: string | null
          id: string
          retry_count: number | null
          started_at: string | null
          status: string
          step_data: Json | null
          step_name: string
          step_order: number
          video_generation_id: string | null
        }
        Insert: {
          completed_at?: string | null
          created_at?: string | null
          error_message?: string | null
          id?: string
          retry_count?: number | null
          started_at?: string | null
          status?: string
          step_data?: Json | null
          step_name: string
          step_order: number
          video_generation_id?: string | null
        }
        Update: {
          completed_at?: string | null
          created_at?: string | null
          error_message?: string | null
          id?: string
          retry_count?: number | null
          started_at?: string | null
          status?: string
          step_data?: Json | null
          step_name?: string
          step_order?: number
          video_generation_id?: string | null
        }
        Relationships: [
          {
            foreignKeyName: "pipeline_steps_video_generation_id_fkey"
            columns: ["video_generation_id"]
            isOneToOne: false
            referencedRelation: "video_generations"
            referencedColumns: ["id"]
          },
        ]
      }
      plot_overviews: {
        Row: {
          audience: string | null
          book_id: string
          created_at: string | null
          generation_cost: number | null
          generation_method: string | null
          genre: string | null
          id: string
          logline: string | null
          model_used: string | null
          setting: string | null
          status: string | null
          story_type: string | null
          themes: Json | null
          tone: string | null
          updated_at: string | null
          user_id: string
          version: number | null
        }
        Insert: {
          audience?: string | null
          book_id: string
          created_at?: string | null
          generation_cost?: number | null
          generation_method?: string | null
          genre?: string | null
          id?: string
          logline?: string | null
          model_used?: string | null
          setting?: string | null
          status?: string | null
          story_type?: string | null
          themes?: Json | null
          tone?: string | null
          updated_at?: string | null
          user_id: string
          version?: number | null
        }
        Update: {
          audience?: string | null
          book_id?: string
          created_at?: string | null
          generation_cost?: number | null
          generation_method?: string | null
          genre?: string | null
          id?: string
          logline?: string | null
          model_used?: string | null
          setting?: string | null
          status?: string | null
          story_type?: string | null
          themes?: Json | null
          tone?: string | null
          updated_at?: string | null
          user_id?: string
          version?: number | null
        }
        Relationships: [
          {
            foreignKeyName: "plot_overviews_book_id_fkey"
            columns: ["book_id"]
            isOneToOne: false
            referencedRelation: "books"
            referencedColumns: ["id"]
          },
        ]
      }
      profiles: {
        Row: {
          avatar_url: string | null
          bio: string | null
          created_at: string | null
          display_name: string | null
          email: string
          id: string
          role: Database["public"]["Enums"]["user_role"]
          updated_at: string | null
        }
        Insert: {
          avatar_url?: string | null
          bio?: string | null
          created_at?: string | null
          display_name?: string | null
          email: string
          id: string
          role?: Database["public"]["Enums"]["user_role"]
          updated_at?: string | null
        }
        Update: {
          avatar_url?: string | null
          bio?: string | null
          created_at?: string | null
          display_name?: string | null
          email?: string
          id?: string
          role?: Database["public"]["Enums"]["user_role"]
          updated_at?: string | null
        }
        Relationships: []
      }
      quiz_attempts: {
        Row: {
          answers: Json
          completed_at: string | null
          id: string
          quiz_id: string | null
          score: number
          time_taken: number | null
          user_id: string | null
        }
        Insert: {
          answers: Json
          completed_at?: string | null
          id?: string
          quiz_id?: string | null
          score: number
          time_taken?: number | null
          user_id?: string | null
        }
        Update: {
          answers?: Json
          completed_at?: string | null
          id?: string
          quiz_id?: string | null
          score?: number
          time_taken?: number | null
          user_id?: string | null
        }
        Relationships: [
          {
            foreignKeyName: "quiz_attempts_quiz_id_fkey"
            columns: ["quiz_id"]
            isOneToOne: false
            referencedRelation: "quizzes"
            referencedColumns: ["id"]
          },
          {
            foreignKeyName: "quiz_attempts_user_id_fkey"
            columns: ["user_id"]
            isOneToOne: false
            referencedRelation: "profiles"
            referencedColumns: ["id"]
          },
        ]
      }
      quizzes: {
        Row: {
          chapter_id: string | null
          created_at: string | null
          difficulty: Database["public"]["Enums"]["difficulty_level"] | null
          id: string
          questions: Json
          title: string
        }
        Insert: {
          chapter_id?: string | null
          created_at?: string | null
          difficulty?: Database["public"]["Enums"]["difficulty_level"] | null
          id?: string
          questions: Json
          title: string
        }
        Update: {
          chapter_id?: string | null
          created_at?: string | null
          difficulty?: Database["public"]["Enums"]["difficulty_level"] | null
          id?: string
          questions?: Json
          title?: string
        }
        Relationships: [
          {
            foreignKeyName: "quizzes_chapter_id_fkey"
            columns: ["chapter_id"]
            isOneToOne: false
            referencedRelation: "chapters"
            referencedColumns: ["id"]
          },
        ]
      }
      scripts: {
        Row: {
          chapter_id: string | null
          character_details: string | null
          characters: Json | null
          created_at: string | null
          id: string
          metadata: Json | null
          scene_descriptions: Json | null
          script: string
          script_name: string | null
          script_style: string
          service_used: string | null
          status: string | null
          updated_at: string | null
          user_id: string | null
        }
        Insert: {
          chapter_id?: string | null
          character_details?: string | null
          characters?: Json | null
          created_at?: string | null
          id?: string
          metadata?: Json | null
          scene_descriptions?: Json | null
          script: string
          script_name?: string | null
          script_style?: string
          service_used?: string | null
          status?: string | null
          updated_at?: string | null
          user_id?: string | null
        }
        Update: {
          chapter_id?: string | null
          character_details?: string | null
          characters?: Json | null
          created_at?: string | null
          id?: string
          metadata?: Json | null
          scene_descriptions?: Json | null
          script?: string
          script_name?: string | null
          script_style?: string
          service_used?: string | null
          status?: string | null
          updated_at?: string | null
          user_id?: string | null
        }
        Relationships: [
          {
            foreignKeyName: "scripts_chapter_id_fkey"
            columns: ["chapter_id"]
            isOneToOne: false
            referencedRelation: "chapters"
            referencedColumns: ["id"]
          },
        ]
      }
      story_choices: {
        Row: {
          chapter_id: string | null
          choice_order: number
          choice_text: string
          consequence: string
          created_at: string | null
          id: string
          next_chapter_id: string | null
        }
        Insert: {
          chapter_id?: string | null
          choice_order: number
          choice_text: string
          consequence: string
          created_at?: string | null
          id?: string
          next_chapter_id?: string | null
        }
        Update: {
          chapter_id?: string | null
          choice_order?: number
          choice_text?: string
          consequence?: string
          created_at?: string | null
          id?: string
          next_chapter_id?: string | null
        }
        Relationships: [
          {
            foreignKeyName: "story_choices_chapter_id_fkey"
            columns: ["chapter_id"]
            isOneToOne: false
            referencedRelation: "chapters"
            referencedColumns: ["id"]
          },
          {
            foreignKeyName: "story_choices_next_chapter_id_fkey"
            columns: ["next_chapter_id"]
            isOneToOne: false
            referencedRelation: "chapters"
            referencedColumns: ["id"]
          },
        ]
      }
      subscription_history: {
        Row: {
          amount_paid: number | null
          created_at: string | null
          currency: string | null
          event_type: string
          from_status: Database["public"]["Enums"]["subscription_status"] | null
          from_tier: Database["public"]["Enums"]["subscription_tier"] | null
          id: string
          metadata: Json | null
          reason: string | null
          stripe_event_id: string | null
          stripe_invoice_id: string | null
          subscription_id: string | null
          to_status: Database["public"]["Enums"]["subscription_status"] | null
          to_tier: Database["public"]["Enums"]["subscription_tier"] | null
          user_id: string
        }
        Insert: {
          amount_paid?: number | null
          created_at?: string | null
          currency?: string | null
          event_type: string
          from_status?:
            | Database["public"]["Enums"]["subscription_status"]
            | null
          from_tier?: Database["public"]["Enums"]["subscription_tier"] | null
          id?: string
          metadata?: Json | null
          reason?: string | null
          stripe_event_id?: string | null
          stripe_invoice_id?: string | null
          subscription_id?: string | null
          to_status?: Database["public"]["Enums"]["subscription_status"] | null
          to_tier?: Database["public"]["Enums"]["subscription_tier"] | null
          user_id: string
        }
        Update: {
          amount_paid?: number | null
          created_at?: string | null
          currency?: string | null
          event_type?: string
          from_status?:
            | Database["public"]["Enums"]["subscription_status"]
            | null
          from_tier?: Database["public"]["Enums"]["subscription_tier"] | null
          id?: string
          metadata?: Json | null
          reason?: string | null
          stripe_event_id?: string | null
          stripe_invoice_id?: string | null
          subscription_id?: string | null
          to_status?: Database["public"]["Enums"]["subscription_status"] | null
          to_tier?: Database["public"]["Enums"]["subscription_tier"] | null
          user_id?: string
        }
        Relationships: [
          {
            foreignKeyName: "subscription_history_subscription_id_fkey"
            columns: ["subscription_id"]
            isOneToOne: false
            referencedRelation: "user_subscriptions"
            referencedColumns: ["id"]
          },
        ]
      }
      subscription_tiers: {
        Row: {
          created_at: string | null
          description: string | null
          display_name: string
          display_order: number | null
          features: Json | null
          has_watermark: boolean
          id: string
          is_active: boolean | null
          max_video_duration: number | null
          monthly_price: number
          monthly_video_limit: number
          priority_processing: boolean | null
          stripe_price_id: string | null
          stripe_product_id: string | null
          tier: Database["public"]["Enums"]["subscription_tier"]
          updated_at: string | null
          video_quality: string
        }
        Insert: {
          created_at?: string | null
          description?: string | null
          display_name: string
          display_order?: number | null
          features?: Json | null
          has_watermark?: boolean
          id?: string
          is_active?: boolean | null
          max_video_duration?: number | null
          monthly_price: number
          monthly_video_limit: number
          priority_processing?: boolean | null
          stripe_price_id?: string | null
          stripe_product_id?: string | null
          tier: Database["public"]["Enums"]["subscription_tier"]
          updated_at?: string | null
          video_quality: string
        }
        Update: {
          created_at?: string | null
          description?: string | null
          display_name?: string
          display_order?: number | null
          features?: Json | null
          has_watermark?: boolean
          id?: string
          is_active?: boolean | null
          max_video_duration?: number | null
          monthly_price?: number
          monthly_video_limit?: number
          priority_processing?: boolean | null
          stripe_price_id?: string | null
          stripe_product_id?: string | null
          tier?: Database["public"]["Enums"]["subscription_tier"]
          updated_at?: string | null
          video_quality?: string
        }
        Relationships: []
      }
      usage_logs: {
        Row: {
          billing_period_end: string | null
          billing_period_start: string | null
          cost_usd: number | null
          created_at: string | null
          id: string
          metadata: Json | null
          resource_id: string | null
          resource_type: string
          subscription_id: string
          usage_count: number | null
          user_id: string
        }
        Insert: {
          billing_period_end?: string | null
          billing_period_start?: string | null
          cost_usd?: number | null
          created_at?: string | null
          id?: string
          metadata?: Json | null
          resource_id?: string | null
          resource_type?: string
          subscription_id: string
          usage_count?: number | null
          user_id: string
        }
        Update: {
          billing_period_end?: string | null
          billing_period_start?: string | null
          cost_usd?: number | null
          created_at?: string | null
          id?: string
          metadata?: Json | null
          resource_id?: string | null
          resource_type?: string
          subscription_id?: string
          usage_count?: number | null
          user_id?: string
        }
        Relationships: [
          {
            foreignKeyName: "usage_logs_subscription_id_fkey"
            columns: ["subscription_id"]
            isOneToOne: false
            referencedRelation: "user_subscriptions"
            referencedColumns: ["id"]
          },
        ]
      }
      user_badges: {
        Row: {
          badge_id: string | null
          blockchain_asset_id: number | null
          earned_at: string | null
          id: string
          transaction_id: string | null
          user_id: string | null
        }
        Insert: {
          badge_id?: string | null
          blockchain_asset_id?: number | null
          earned_at?: string | null
          id?: string
          transaction_id?: string | null
          user_id?: string | null
        }
        Update: {
          badge_id?: string | null
          blockchain_asset_id?: number | null
          earned_at?: string | null
          id?: string
          transaction_id?: string | null
          user_id?: string | null
        }
        Relationships: [
          {
            foreignKeyName: "user_badges_badge_id_fkey"
            columns: ["badge_id"]
            isOneToOne: false
            referencedRelation: "badges"
            referencedColumns: ["id"]
          },
          {
            foreignKeyName: "user_badges_user_id_fkey"
            columns: ["user_id"]
            isOneToOne: false
            referencedRelation: "profiles"
            referencedColumns: ["id"]
          },
        ]
      }
      user_collectibles: {
        Row: {
          blockchain_asset_id: number | null
          collectible_id: string | null
          earned_at: string | null
          id: string
          transaction_id: string | null
          user_id: string | null
        }
        Insert: {
          blockchain_asset_id?: number | null
          collectible_id?: string | null
          earned_at?: string | null
          id?: string
          transaction_id?: string | null
          user_id?: string | null
        }
        Update: {
          blockchain_asset_id?: number | null
          collectible_id?: string | null
          earned_at?: string | null
          id?: string
          transaction_id?: string | null
          user_id?: string | null
        }
        Relationships: [
          {
            foreignKeyName: "user_collectibles_collectible_id_fkey"
            columns: ["collectible_id"]
            isOneToOne: false
            referencedRelation: "nft_collectibles"
            referencedColumns: ["id"]
          },
          {
            foreignKeyName: "user_collectibles_user_id_fkey"
            columns: ["user_id"]
            isOneToOne: false
            referencedRelation: "profiles"
            referencedColumns: ["id"]
          },
        ]
      }
      user_progress: {
        Row: {
          book_id: string | null
          completed_at: string | null
          created_at: string | null
          current_chapter: number | null
          id: string
          last_read_at: string | null
          progress_percentage: number | null
          time_spent: number | null
          updated_at: string | null
          user_id: string | null
        }
        Insert: {
          book_id?: string | null
          completed_at?: string | null
          created_at?: string | null
          current_chapter?: number | null
          id?: string
          last_read_at?: string | null
          progress_percentage?: number | null
          time_spent?: number | null
          updated_at?: string | null
          user_id?: string | null
        }
        Update: {
          book_id?: string | null
          completed_at?: string | null
          created_at?: string | null
          current_chapter?: number | null
          id?: string
          last_read_at?: string | null
          progress_percentage?: number | null
          time_spent?: number | null
          updated_at?: string | null
          user_id?: string | null
        }
        Relationships: [
          {
            foreignKeyName: "user_progress_book_id_fkey"
            columns: ["book_id"]
            isOneToOne: false
            referencedRelation: "books"
            referencedColumns: ["id"]
          },
          {
            foreignKeyName: "user_progress_user_id_fkey"
            columns: ["user_id"]
            isOneToOne: false
            referencedRelation: "profiles"
            referencedColumns: ["id"]
          },
        ]
      }
      user_story_progress: {
        Row: {
          book_id: string | null
          choices_made: Json | null
          created_at: string | null
          current_branch: string
          id: string
          story_state: Json | null
          updated_at: string | null
          user_id: string | null
        }
        Insert: {
          book_id?: string | null
          choices_made?: Json | null
          created_at?: string | null
          current_branch: string
          id?: string
          story_state?: Json | null
          updated_at?: string | null
          user_id?: string | null
        }
        Update: {
          book_id?: string | null
          choices_made?: Json | null
          created_at?: string | null
          current_branch?: string
          id?: string
          story_state?: Json | null
          updated_at?: string | null
          user_id?: string | null
        }
        Relationships: [
          {
            foreignKeyName: "user_story_progress_book_id_fkey"
            columns: ["book_id"]
            isOneToOne: false
            referencedRelation: "books"
            referencedColumns: ["id"]
          },
          {
            foreignKeyName: "user_story_progress_user_id_fkey"
            columns: ["user_id"]
            isOneToOne: false
            referencedRelation: "profiles"
            referencedColumns: ["id"]
          },
        ]
      }
      user_subscriptions: {
        Row: {
          cancel_at_period_end: boolean | null
          cancelled_at: string | null
          created_at: string | null
          current_period_end: string | null
          current_period_start: string | null
          has_watermark: boolean | null
          id: string
          monthly_video_limit: number
          next_billing_date: string | null
          status: Database["public"]["Enums"]["subscription_status"]
          stripe_customer_id: string | null
          stripe_price_id: string | null
          stripe_subscription_id: string | null
          tier: Database["public"]["Enums"]["subscription_tier"]
          updated_at: string | null
          user_id: string
          video_quality: string | null
          videos_generated_this_period: number | null
        }
        Insert: {
          cancel_at_period_end?: boolean | null
          cancelled_at?: string | null
          created_at?: string | null
          current_period_end?: string | null
          current_period_start?: string | null
          has_watermark?: boolean | null
          id?: string
          monthly_video_limit?: number
          next_billing_date?: string | null
          status?: Database["public"]["Enums"]["subscription_status"]
          stripe_customer_id?: string | null
          stripe_price_id?: string | null
          stripe_subscription_id?: string | null
          tier?: Database["public"]["Enums"]["subscription_tier"]
          updated_at?: string | null
          user_id: string
          video_quality?: string | null
          videos_generated_this_period?: number | null
        }
        Update: {
          cancel_at_period_end?: boolean | null
          cancelled_at?: string | null
          created_at?: string | null
          current_period_end?: string | null
          current_period_start?: string | null
          has_watermark?: boolean | null
          id?: string
          monthly_video_limit?: number
          next_billing_date?: string | null
          status?: Database["public"]["Enums"]["subscription_status"]
          stripe_customer_id?: string | null
          stripe_price_id?: string | null
          stripe_subscription_id?: string | null
          tier?: Database["public"]["Enums"]["subscription_tier"]
          updated_at?: string | null
          user_id?: string
          video_quality?: string | null
          videos_generated_this_period?: number | null
        }
        Relationships: []
      }
      video_generations: {
        Row: {
          audio_files: Json | null
          audio_task_id: string | null
          can_resume: boolean | null
          chapter_id: string | null
          completed_at: string | null
          created_at: string | null
          duration_seconds: number | null
          error_message: string | null
          failed_at_step: string | null
          file_size_bytes: number | null
          generation_status:
            | Database["public"]["Enums"]["video_generation_status"]
            | null
          id: string
          image_data: Json | null
          image_files: Json | null
          lipsync_data: Json | null
          merge_data: Json | null
          pipeline_state: Json | null
          processing_time_seconds: number | null
          progress_log: Json | null
          quality_tier: Database["public"]["Enums"]["video_quality_tier"] | null
          retry_count: number | null
          script_data: Json | null
          script_id: string | null
          subtitle_url: string | null
          task_metadata: Json | null
          thumbnail_url: string | null
          updated_at: string | null
          user_id: string | null
          video_data: Json | null
          video_segments: Json | null
          video_url: string | null
        }
        Insert: {
          audio_files?: Json | null
          audio_task_id?: string | null
          can_resume?: boolean | null
          chapter_id?: string | null
          completed_at?: string | null
          created_at?: string | null
          duration_seconds?: number | null
          error_message?: string | null
          failed_at_step?: string | null
          file_size_bytes?: number | null
          generation_status?:
            | Database["public"]["Enums"]["video_generation_status"]
            | null
          id?: string
          image_data?: Json | null
          image_files?: Json | null
          lipsync_data?: Json | null
          merge_data?: Json | null
          pipeline_state?: Json | null
          processing_time_seconds?: number | null
          progress_log?: Json | null
          quality_tier?:
            | Database["public"]["Enums"]["video_quality_tier"]
            | null
          retry_count?: number | null
          script_data?: Json | null
          script_id?: string | null
          subtitle_url?: string | null
          task_metadata?: Json | null
          thumbnail_url?: string | null
          updated_at?: string | null
          user_id?: string | null
          video_data?: Json | null
          video_segments?: Json | null
          video_url?: string | null
        }
        Update: {
          audio_files?: Json | null
          audio_task_id?: string | null
          can_resume?: boolean | null
          chapter_id?: string | null
          completed_at?: string | null
          created_at?: string | null
          duration_seconds?: number | null
          error_message?: string | null
          failed_at_step?: string | null
          file_size_bytes?: number | null
          generation_status?:
            | Database["public"]["Enums"]["video_generation_status"]
            | null
          id?: string
          image_data?: Json | null
          image_files?: Json | null
          lipsync_data?: Json | null
          merge_data?: Json | null
          pipeline_state?: Json | null
          processing_time_seconds?: number | null
          progress_log?: Json | null
          quality_tier?:
            | Database["public"]["Enums"]["video_quality_tier"]
            | null
          retry_count?: number | null
          script_data?: Json | null
          script_id?: string | null
          subtitle_url?: string | null
          task_metadata?: Json | null
          thumbnail_url?: string | null
          updated_at?: string | null
          user_id?: string | null
          video_data?: Json | null
          video_segments?: Json | null
          video_url?: string | null
        }
        Relationships: [
          {
            foreignKeyName: "video_generations_chapter_id_fkey"
            columns: ["chapter_id"]
            isOneToOne: false
            referencedRelation: "chapters"
            referencedColumns: ["id"]
          },
          {
            foreignKeyName: "video_generations_script_id_fkey"
            columns: ["script_id"]
            isOneToOne: false
            referencedRelation: "scripts"
            referencedColumns: ["id"]
          },
        ]
      }
      video_segments: {
        Row: {
          created_at: string | null
          duration_seconds: number | null
          error_message: string | null
          file_size_bytes: number | null
          fps: number | null
          generation_method: string | null
          generation_time_seconds: number | null
          height: number | null
          id: string
          metadata: Json | null
          processing_model: string | null
          processing_service: string | null
          scene_description: string | null
          scene_id: string | null
          segment_index: number
          source_image_url: string | null
          status: string | null
          thumbnail_url: string | null
          updated_at: string | null
          video_generation_id: string | null
          video_url: string | null
          width: number | null
        }
        Insert: {
          created_at?: string | null
          duration_seconds?: number | null
          error_message?: string | null
          file_size_bytes?: number | null
          fps?: number | null
          generation_method?: string | null
          generation_time_seconds?: number | null
          height?: number | null
          id?: string
          metadata?: Json | null
          processing_model?: string | null
          processing_service?: string | null
          scene_description?: string | null
          scene_id?: string | null
          segment_index: number
          source_image_url?: string | null
          status?: string | null
          thumbnail_url?: string | null
          updated_at?: string | null
          video_generation_id?: string | null
          video_url?: string | null
          width?: number | null
        }
        Update: {
          created_at?: string | null
          duration_seconds?: number | null
          error_message?: string | null
          file_size_bytes?: number | null
          fps?: number | null
          generation_method?: string | null
          generation_time_seconds?: number | null
          height?: number | null
          id?: string
          metadata?: Json | null
          processing_model?: string | null
          processing_service?: string | null
          scene_description?: string | null
          scene_id?: string | null
          segment_index?: number
          source_image_url?: string | null
          status?: string | null
          thumbnail_url?: string | null
          updated_at?: string | null
          video_generation_id?: string | null
          video_url?: string | null
          width?: number | null
        }
        Relationships: [
          {
            foreignKeyName: "video_segments_video_generation_id_fkey"
            columns: ["video_generation_id"]
            isOneToOne: false
            referencedRelation: "video_generations"
            referencedColumns: ["id"]
          },
        ]
      }
      videos: {
        Row: {
          book_id: string | null
          chapter_id: string | null
          character_details: string | null
          created_at: number
          id: string
          klingai_video_url: string | null
          scene_prompt: string | null
          script: string | null
          source: string | null
          user_id: string | null
          video_url: string
        }
        Insert: {
          book_id?: string | null
          chapter_id?: string | null
          character_details?: string | null
          created_at: number
          id?: string
          klingai_video_url?: string | null
          scene_prompt?: string | null
          script?: string | null
          source?: string | null
          user_id?: string | null
          video_url: string
        }
        Update: {
          book_id?: string | null
          chapter_id?: string | null
          character_details?: string | null
          created_at?: number
          id?: string
          klingai_video_url?: string | null
          scene_prompt?: string | null
          script?: string | null
          source?: string | null
          user_id?: string | null
          video_url?: string
        }
        Relationships: [
          {
            foreignKeyName: "videos_book_id_fkey"
            columns: ["book_id"]
            isOneToOne: false
            referencedRelation: "books"
            referencedColumns: ["id"]
          },
          {
            foreignKeyName: "videos_chapter_id_fkey"
            columns: ["chapter_id"]
            isOneToOne: false
            referencedRelation: "chapters"
            referencedColumns: ["id"]
          },
          {
            foreignKeyName: "videos_user_id_fkey"
            columns: ["user_id"]
            isOneToOne: false
            referencedRelation: "profiles"
            referencedColumns: ["id"]
          },
        ]
      }
    }
    Views: {
      [_ in never]: never
    }
    Functions: {
      binary_quantize: {
        Args: { "": string } | { "": unknown }
        Returns: unknown
      }
      check_usage_limit: {
        Args: { p_user_id: string }
        Returns: boolean
      }
      halfvec_avg: {
        Args: { "": number[] }
        Returns: unknown
      }
      halfvec_out: {
        Args: { "": unknown }
        Returns: unknown
      }
      halfvec_send: {
        Args: { "": unknown }
        Returns: string
      }
      halfvec_typmod_in: {
        Args: { "": unknown[] }
        Returns: number
      }
      hnsw_bit_support: {
        Args: { "": unknown }
        Returns: unknown
      }
      hnsw_halfvec_support: {
        Args: { "": unknown }
        Returns: unknown
      }
      hnsw_sparsevec_support: {
        Args: { "": unknown }
        Returns: unknown
      }
      hnswhandler: {
        Args: { "": unknown }
        Returns: unknown
      }
      increment_usage: {
        Args: { p_resource_id?: string; p_user_id: string }
        Returns: undefined
      }
      ivfflat_bit_support: {
        Args: { "": unknown }
        Returns: unknown
      }
      ivfflat_halfvec_support: {
        Args: { "": unknown }
        Returns: unknown
      }
      ivfflathandler: {
        Args: { "": unknown }
        Returns: unknown
      }
      l2_norm: {
        Args: { "": unknown } | { "": unknown }
        Returns: number
      }
      l2_normalize: {
        Args: { "": string } | { "": unknown } | { "": unknown }
        Returns: string
      }
      match_book_embeddings: {
        Args: {
          match_count: number
          match_threshold: number
          query_embedding: string
        }
        Returns: {
          book_id: string
          chunk_index: number
          chunk_type: string
          content_chunk: string
          id: string
          similarity: number
        }[]
      }
      match_chapter_embeddings: {
        Args: {
          match_count: number
          match_threshold: number
          query_embedding: string
        }
        Returns: {
          book_id: string
          chapter_id: string
          chunk_index: number
          content_chunk: string
          id: string
          similarity: number
        }[]
      }
      reset_monthly_usage: {
        Args: Record<PropertyKey, never>
        Returns: number
      }
      sparsevec_out: {
        Args: { "": unknown }
        Returns: unknown
      }
      sparsevec_send: {
        Args: { "": unknown }
        Returns: string
      }
      sparsevec_typmod_in: {
        Args: { "": unknown[] }
        Returns: number
      }
      vector_avg: {
        Args: { "": number[] }
        Returns: string
      }
      vector_dims: {
        Args: { "": string } | { "": unknown }
        Returns: number
      }
      vector_norm: {
        Args: { "": string }
        Returns: number
      }
      vector_out: {
        Args: { "": string }
        Returns: unknown
      }
      vector_send: {
        Args: { "": string }
        Returns: string
      }
      vector_typmod_in: {
        Args: { "": unknown[] }
        Returns: number
      }
    }
    Enums: {
      audio_type:
        | "narrator"
        | "character"
        | "sound_effect"
        | "background_music"
        | "music"
        | "sfx"
      badge_rarity: "common" | "uncommon" | "rare" | "epic" | "legendary"
      book_status:
        | "PROCESSING"
        | "GENERATING"
        | "READY"
        | "FAILED"
        | "QUEUED"
        | "published"
        | "failed"
        | "PENDING_PAYMENT"
      book_type: "learning" | "entertainment"
      difficulty_level: "easy" | "medium" | "hard"
      subscription_status:
        | "active"
        | "cancelled"
        | "expired"
        | "past_due"
        | "trialing"
      subscription_tier: "free" | "basic" | "pro"
      user_role: "author" | "explorer" | "superadmin"
      video_generation_status:
        | "pending"
        | "generating_audio"
        | "generating_images"
        | "generating_video"
        | "combining"
        | "completed"
        | "failed"
        | "applying_lipsync"
        | "lipsync_completed"
        | "lipsync_failed"
        | "audio_completed"
        | "images_completed"
        | "video_completed"
        | "merging_audio"
        | "retrying"
      video_quality_tier: "basic" | "standard" | "standard_2" | "pro" | "master"
    }
    CompositeTypes: {
      [_ in never]: never
    }
  }
}

type DatabaseWithoutInternals = Omit<Database, "__InternalSupabase">

type DefaultSchema = DatabaseWithoutInternals[Extract<keyof Database, "public">]

export type Tables<
  DefaultSchemaTableNameOrOptions extends
    | keyof (DefaultSchema["Tables"] & DefaultSchema["Views"])
    | { schema: keyof DatabaseWithoutInternals },
  TableName extends DefaultSchemaTableNameOrOptions extends {
    schema: keyof DatabaseWithoutInternals
  }
    ? keyof (DatabaseWithoutInternals[DefaultSchemaTableNameOrOptions["schema"]]["Tables"] &
        DatabaseWithoutInternals[DefaultSchemaTableNameOrOptions["schema"]]["Views"])
    : never = never,
> = DefaultSchemaTableNameOrOptions extends {
  schema: keyof DatabaseWithoutInternals
}
  ? (DatabaseWithoutInternals[DefaultSchemaTableNameOrOptions["schema"]]["Tables"] &
      DatabaseWithoutInternals[DefaultSchemaTableNameOrOptions["schema"]]["Views"])[TableName] extends {
      Row: infer R
    }
    ? R
    : never
  : DefaultSchemaTableNameOrOptions extends keyof (DefaultSchema["Tables"] &
        DefaultSchema["Views"])
    ? (DefaultSchema["Tables"] &
        DefaultSchema["Views"])[DefaultSchemaTableNameOrOptions] extends {
        Row: infer R
      }
      ? R
      : never
    : never

export type TablesInsert<
  DefaultSchemaTableNameOrOptions extends
    | keyof DefaultSchema["Tables"]
    | { schema: keyof DatabaseWithoutInternals },
  TableName extends DefaultSchemaTableNameOrOptions extends {
    schema: keyof DatabaseWithoutInternals
  }
    ? keyof DatabaseWithoutInternals[DefaultSchemaTableNameOrOptions["schema"]]["Tables"]
    : never = never,
> = DefaultSchemaTableNameOrOptions extends {
  schema: keyof DatabaseWithoutInternals
}
  ? DatabaseWithoutInternals[DefaultSchemaTableNameOrOptions["schema"]]["Tables"][TableName] extends {
      Insert: infer I
    }
    ? I
    : never
  : DefaultSchemaTableNameOrOptions extends keyof DefaultSchema["Tables"]
    ? DefaultSchema["Tables"][DefaultSchemaTableNameOrOptions] extends {
        Insert: infer I
      }
      ? I
      : never
    : never

export type TablesUpdate<
  DefaultSchemaTableNameOrOptions extends
    | keyof DefaultSchema["Tables"]
    | { schema: keyof DatabaseWithoutInternals },
  TableName extends DefaultSchemaTableNameOrOptions extends {
    schema: keyof DatabaseWithoutInternals
  }
    ? keyof DatabaseWithoutInternals[DefaultSchemaTableNameOrOptions["schema"]]["Tables"]
    : never = never,
> = DefaultSchemaTableNameOrOptions extends {
  schema: keyof DatabaseWithoutInternals
}
  ? DatabaseWithoutInternals[DefaultSchemaTableNameOrOptions["schema"]]["Tables"][TableName] extends {
      Update: infer U
    }
    ? U
    : never
  : DefaultSchemaTableNameOrOptions extends keyof DefaultSchema["Tables"]
    ? DefaultSchema["Tables"][DefaultSchemaTableNameOrOptions] extends {
        Update: infer U
      }
      ? U
      : never
    : never

export type Enums<
  DefaultSchemaEnumNameOrOptions extends
    | keyof DefaultSchema["Enums"]
    | { schema: keyof DatabaseWithoutInternals },
  EnumName extends DefaultSchemaEnumNameOrOptions extends {
    schema: keyof DatabaseWithoutInternals
  }
    ? keyof DatabaseWithoutInternals[DefaultSchemaEnumNameOrOptions["schema"]]["Enums"]
    : never = never,
> = DefaultSchemaEnumNameOrOptions extends {
  schema: keyof DatabaseWithoutInternals
}
  ? DatabaseWithoutInternals[DefaultSchemaEnumNameOrOptions["schema"]]["Enums"][EnumName]
  : DefaultSchemaEnumNameOrOptions extends keyof DefaultSchema["Enums"]
    ? DefaultSchema["Enums"][DefaultSchemaEnumNameOrOptions]
    : never

export type CompositeTypes<
  PublicCompositeTypeNameOrOptions extends
    | keyof DefaultSchema["CompositeTypes"]
    | { schema: keyof DatabaseWithoutInternals },
  CompositeTypeName extends PublicCompositeTypeNameOrOptions extends {
    schema: keyof DatabaseWithoutInternals
  }
    ? keyof DatabaseWithoutInternals[PublicCompositeTypeNameOrOptions["schema"]]["CompositeTypes"]
    : never = never,
> = PublicCompositeTypeNameOrOptions extends {
  schema: keyof DatabaseWithoutInternals
}
  ? DatabaseWithoutInternals[PublicCompositeTypeNameOrOptions["schema"]]["CompositeTypes"][CompositeTypeName]
  : PublicCompositeTypeNameOrOptions extends keyof DefaultSchema["CompositeTypes"]
    ? DefaultSchema["CompositeTypes"][PublicCompositeTypeNameOrOptions]
    : never

export const Constants = {
  graphql_public: {
    Enums: {},
  },
  public: {
    Enums: {
      audio_type: [
        "narrator",
        "character",
        "sound_effect",
        "background_music",
        "music",
        "sfx",
      ],
      badge_rarity: ["common", "uncommon", "rare", "epic", "legendary"],
      book_status: [
        "PROCESSING",
        "GENERATING",
        "READY",
        "FAILED",
        "QUEUED",
        "published",
        "failed",
        "PENDING_PAYMENT",
      ],
      book_type: ["learning", "entertainment"],
      difficulty_level: ["easy", "medium", "hard"],
      subscription_status: [
        "active",
        "cancelled",
        "expired",
        "past_due",
        "trialing",
      ],
      subscription_tier: ["free", "basic", "pro"],
      user_role: ["author", "explorer", "superadmin"],
      video_generation_status: [
        "pending",
        "generating_audio",
        "generating_images",
        "generating_video",
        "combining",
        "completed",
        "failed",
        "applying_lipsync",
        "lipsync_completed",
        "lipsync_failed",
        "audio_completed",
        "images_completed",
        "video_completed",
        "merging_audio",
        "retrying",
      ],
      video_quality_tier: ["basic", "standard", "standard_2", "pro", "master"],
    },
  },
} as const
