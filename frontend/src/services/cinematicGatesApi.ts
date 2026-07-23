import { apiClient } from '../lib/api';
import type {
  SequenceUnit,
  LineTracking,
  ShotDiversityReport,
  ContinuityReference,
  EpisodeGateStatus,
  SequenceUnitType,
  SequenceUnitStatus,
  LineTrackingStage,
  ContinuityReferenceType,
  ShotDiversityEntry,
} from '../types/cinematicGates';

// ---- Request/response shapes ----

export interface CreateSequenceUnitInput {
  unit_type: SequenceUnitType;
  unit_order: number;
  title: string;
  script_content?: string;
  duration_seconds?: number;
  status?: SequenceUnitStatus;
  metadata?: Record<string, unknown>;
}

export interface UpdateSequenceUnitInput {
  title?: string;
  script_content?: string;
  duration_seconds?: number;
  status?: SequenceUnitStatus;
  unit_order?: number;
  metadata?: Record<string, unknown>;
}

export interface UpdateLineStageInput {
  character_name?: string;
  voice_id?: string;
  scene_id?: string;
  shot_id?: string;
  source_audio_url?: string;
  lipsync_task_id?: string;
  resolved_provider?: string;
  resolved_model?: string;
  timeline_position_ms?: number;
  metadata?: Record<string, unknown>;
}

export interface CreateContinuityReferenceInput {
  reference_type: ContinuityReferenceType;
  reference_id: string;
  reference_data: Record<string, unknown>;
  shot_ids?: string[];
}

export interface TrackConsistencyResult {
  consistent: boolean;
  inconsistencies: string[];
}

export interface AdjacentShotQAResult {
  video_generation_id: string;
  results: Record<string, unknown>;
  verified: boolean;
}

// ---- API functions ----

export const cinematicGatesApi = {
  // ── Sequence Units ──

  createSequenceUnits: async (
    vgId: string,
    units: CreateSequenceUnitInput[]
  ): Promise<SequenceUnit[]> => {
    return apiClient.post<SequenceUnit[]>(
      `/ai/cinematic-gates/${vgId}/sequence-units`,
      { units }
    );
  },

  getSequenceUnits: async (vgId: string): Promise<SequenceUnit[]> => {
    return apiClient.get<SequenceUnit[]>(
      `/ai/cinematic-gates/${vgId}/sequence-units`
    );
  },

  updateSequenceUnit: async (
    unitId: string,
    data: UpdateSequenceUnitInput
  ): Promise<SequenceUnit> => {
    return apiClient.patch<SequenceUnit>(
      `/ai/cinematic-gates/sequence-units/${unitId}`,
      data
    );
  },

  // ── Line Tracking ──

  getLineTracking: async (vgId: string): Promise<LineTracking[]> => {
    return apiClient.get<LineTracking[]>(
      `/ai/cinematic-gates/${vgId}/line-tracking`
    );
  },

  updateLineStage: async (
    lineId: string,
    stage: LineTrackingStage,
    data: UpdateLineStageInput
  ): Promise<LineTracking> => {
    return apiClient.patch<LineTracking>(
      `/ai/cinematic-gates/line-tracking/${lineId}`,
      { status: stage, ...data }
    );
  },

  // ── Shot Diversity ──

  analyzeShotDiversity: async (vgId: string): Promise<ShotDiversityReport> => {
    return apiClient.post<ShotDiversityReport>(
      `/ai/cinematic-gates/${vgId}/shot-diversity/analyze`,
      {}
    );
  },

  getShotDiversityReport: async (vgId: string): Promise<ShotDiversityReport | null> => {
    return apiClient.get<ShotDiversityReport | null>(
      `/ai/cinematic-gates/${vgId}/shot-diversity`
    );
  },

  markIntentionalMotif: async (
    reportId: string,
    shotId: string,
    reason: string
  ): Promise<ShotDiversityEntry> => {
    return apiClient.patch<ShotDiversityEntry>(
      `/ai/cinematic-gates/shot-diversity/${reportId}/motif`,
      { shot_id: shotId, motif_reason: reason }
    );
  },

  // ── Continuity References ──

  createContinuityReference: async (
    vgId: string,
    refType: ContinuityReferenceType,
    refId: string,
    refData: Record<string, unknown>,
    shotIds?: string[]
  ): Promise<ContinuityReference> => {
    return apiClient.post<ContinuityReference>(
      `/ai/cinematic-gates/${vgId}/continuity-references`,
      {
        reference_type: refType,
        reference_id: refId,
        reference_data: refData,
        shot_ids: shotIds ?? [],
      }
    );
  },

  getContinuityReferences: async (
    vgId: string,
    refType?: ContinuityReferenceType
  ): Promise<ContinuityReference[]> => {
    const query = refType
      ? `?reference_type=${encodeURIComponent(refType)}`
      : '';
    return apiClient.get<ContinuityReference[]>(
      `/ai/cinematic-gates/${vgId}/continuity-references${query}`
    );
  },

  // ── QA & Validation ──

  runAdjacentShotQA: async (vgId: string): Promise<AdjacentShotQAResult> => {
    return apiClient.post<AdjacentShotQAResult>(
      `/ai/cinematic-gates/${vgId}/adjacent-shot-qa`,
      {}
    );
  },

  validateTrackConsistency: async (vgId: string): Promise<TrackConsistencyResult> => {
    return apiClient.get<TrackConsistencyResult>(
      `/ai/cinematic-gates/${vgId}/track-consistency`
    );
  },

  // ── Episode Gate Status ──

  getEpisodeGateStatus: async (vgId: string): Promise<EpisodeGateStatus> => {
    return apiClient.get<EpisodeGateStatus>(
      `/ai/cinematic-gates/${vgId}/gate-status`
    );
  },
};

export default cinematicGatesApi;