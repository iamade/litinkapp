export type SequenceUnitType =
  | 'ident_title'
  | 'prologue'
  | 'dialogue_act'
  | 'climax_resolution'
  | 'closing_bookend'
  | 'end_title_credits';

export type SequenceUnitStatus = 'pending' | 'active' | 'completed' | 'skipped';

export type LineTrackingStage =
  | 'unassigned'
  | 'character_assigned'
  | 'voice_assigned'
  | 'scene_assigned'
  | 'shot_assigned'
  | 'audio_generated'
  | 'lipsync_queued'
  | 'lipsync_complete'
  | 'placed';

export type ShotDiversityStatus = 'pending' | 'analyzing' | 'completed' | 'failed';

export type ContinuityReferenceType = 'character' | 'world' | 'prop' | 'location';

export interface SequenceUnit {
  id: string;
  video_generation_id: string;
  unit_type: SequenceUnitType;
  unit_order: number;
  title: string;
  script_content?: string;
  duration_seconds?: number;
  status: SequenceUnitStatus;
  metadata: Record<string, unknown>;
  created_at: string;
  updated_at: string;
}

export interface LineTracking {
  id: string;
  sequence_unit_id: string;
  video_generation_id: string;
  line_text: string;
  character_name?: string;
  voice_id?: string;
  scene_id?: string;
  shot_id?: string;
  source_audio_url?: string;
  lipsync_task_id?: string;
  resolved_provider?: string;
  resolved_model?: string;
  timeline_position_ms?: number;
  status: LineTrackingStage;
  metadata: Record<string, unknown>;
  created_at: string;
  updated_at: string;
}

export interface ShotDiversityEntry {
  shot_id: string;
  hash: string;
  duplicates: string[];
  near_duplicates: string[];
  is_intentional_motif: boolean;
  motif_reason?: string;
}

export interface ShotDiversityReport {
  id: string;
  video_generation_id: string;
  total_shots: number;
  duplicate_count: number;
  near_duplicate_count: number;
  unique_count: number;
  intentional_motif_count: number;
  report_data: ShotDiversityEntry[];
  status: ShotDiversityStatus;
  created_at: string;
  updated_at: string;
}

export interface ContinuityReference {
  id: string;
  video_generation_id: string;
  reference_type: ContinuityReferenceType;
  reference_id: string;
  reference_data: Record<string, unknown>;
  shot_ids: string[];
  adjacent_shot_qa: Record<string, unknown>;
  created_at: string;
  updated_at: string;
}

export interface EpisodeGateStatus {
  sequence_units_valid: boolean;
  missing_units: SequenceUnitType[];
  line_tracking_complete: boolean;
  untracked_lines: number;
  shot_diversity_status: ShotDiversityStatus;
  shot_diversity_summary?: {
    total: number;
    duplicates: number;
    near_duplicates: number;
    unique: number;
    motifs: number;
  };
  continuity_verified: boolean;
  track_consistency: { consistent: boolean; inconsistencies: string[] };
  all_gates_passed: boolean;
}