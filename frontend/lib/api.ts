import axios, { type AxiosRequestConfig } from "axios";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";
const API_ROOT_URL = API_BASE_URL.replace(/\/api\/v1\/?$/, "");

/** Shared axios instance. All requests go through this so baseURL/headers
 *  are configured in exactly one place. */
const client = axios.create({
  baseURL: API_BASE_URL,
  headers: { "Content-Type": "application/json" },
});

export interface SimulationConfig {
  state: string;
  shots: number;
  seed?: number;
  measurement_basis: "Z" | "X";
}

export interface AttackConfig {
  attack_type: "forgery" | "impersonation" | "replay" | "channel";
  intensity: number;
  parameters?: Record<string, any>;
}

export interface SimulationRunRequest {
  protocol: string;
  config: SimulationConfig;
  attack?: AttackConfig;
  detection_threshold?: number;
}

export interface SimulationRunResponse {
  run_id: string;
  status: string;
  protocol: string;
  shots: number;
  measurements: Record<string, number>;
  measurement_counts: Record<string, number>;
  theoretical_probs: Record<string, number>;
  fidelity?: number;
  execution_time_ms: number;
  timestamp: string;
}

export interface DetectionRequest {
  observed_distribution: Record<string, number>;
  expected_distribution: Record<string, number>;
  sample_size: number;
  threshold?: number;
  method?: string;
}

export interface DetectionResponse {
  run_id: string;
  decision: "LEGITIMATE" | "SUSPICIOUS" | "ATTACK";
  attack_type?: string;
  statistic_value: number;
  threshold: number;
  p_value?: number;
  confidence_interval?: [number, number];
  forgery_probability: number;
  verification_accuracy: number;
  false_accept_rate: number;
  false_reject_rate: number;
  detection_rate: number;
  evidence: string[];
  explanation: string;
  confidence: string;
  timestamp: string;
}

export interface Run {
  run_id: string;
  protocol: string;
  status: "completed" | "running" | "failed";
  shots: number;
  timestamp: string;
  execution_time_ms: number;
  threat_detected: boolean;
  threat_level?: "LOW" | "MEDIUM" | "HIGH";
  fidelity?: number;
  detection_decision?: "LEGITIMATE" | "SUSPICIOUS" | "ATTACK";
  verification_accuracy?: number;
  false_accept_rate?: number;
  false_reject_rate?: number;
  detection_rate?: number;
}

export interface HistoryResponse {
  runs: Run[];
  total: number;
  limit: number;
  offset: number;
}

/* ------------------------------------------------------------------ *
 * Investigation-scoped domain types (MILESTONE 2 backend).
 * Shapes mirror the Pydantic response models in backend/routes/*.py.
 * ------------------------------------------------------------------ */

export interface QuantumResult {
  id?: string;
  fidelity?: number;
  measurement_counts?: Record<string, number>;
  measurement_probabilities?: Record<string, number>;
  theoretical_probabilities?: Record<string, number>;
  circuit_qasm?: string;
}

export interface Experiment {
  id: string;
  type: "baseline" | "attack" | string;
  status: "completed" | "running" | "failed" | string;
  execution_time_ms?: number;
  error?: string | null;
  created_at?: string;
  config?: any;
  quantum_result?: QuantumResult;
}

export interface BaselineExperimentRequest {
  state: string;
  shots: number;
  seed?: number;
  measurement_basis?: "Z" | "X";
}

export interface AttackExperimentRequest {
  baseline_experiment_id: string;
  state: string;
  shots: number;
  attack_type: "forgery" | "impersonation" | "replay" | "channel";
  attack_intensity: number;
  seed?: number;
  measurement_basis?: "Z" | "X";
}

export interface DetectionRunRequest {
  baseline_experiment_id: string;
  attack_experiment_id: string;
  threshold?: number;
  method?: string;
}

/**
 * Single API surface. Exposes raw HTTP verbs (get/post/put/delete) for
 * endpoints that don't warrant a typed helper, plus typed helpers for the
 * endpoints the UI uses most. One export, no duplicates.
 *
 * NOTE ON PARAMETER TRANSPORT: the investigation/experiment/detection/evidence
 * endpoints declare their inputs as FastAPI `Query(...)` parameters, NOT JSON
 * bodies. Every helper below therefore passes values via `params:`. Sending a
 * JSON body to these would produce HTTP 422.
 */
export const api = {
  // ---- Raw verbs (relative to API_BASE_URL) ----
  get: <T = any>(url: string, config?: AxiosRequestConfig) => client.get<T>(url, config),
  post: <T = any>(url: string, data?: any, config?: AxiosRequestConfig) =>
    client.post<T>(url, data, config),
  put: <T = any>(url: string, data?: any, config?: AxiosRequestConfig) =>
    client.put<T>(url, data, config),
  delete: <T = any>(url: string, config?: AxiosRequestConfig) => client.delete<T>(url, config),

  // ---- Health ----
  getHealth: async () => {
    const response = await axios.get(`${API_ROOT_URL}/health`);
    return response.data;
  },

  // ---- Simulation (legacy /runs surface) ----
  runSimulation: async (data: SimulationRunRequest): Promise<SimulationRunResponse> => {
    const response = await client.post<SimulationRunResponse>("/simulations/run", data);
    return response.data;
  },

  detectThreat: async (runId: string, data: DetectionRequest): Promise<DetectionResponse> => {
    const response = await client.post<DetectionResponse>(`/simulations/${runId}/detect`, data);
    return response.data;
  },

  simulateAttack: async (data: any): Promise<SimulationRunResponse> => {
    const response = await client.post<SimulationRunResponse>(
      `/attacks/${data.attack_config.attack_type}/simulate`,
      data
    );
    return response.data;
  },

  // ---- Runs ----
  getRun: async (runId: string): Promise<Run> => {
    const response = await client.get<Run>(`/runs/${runId}`);
    return response.data;
  },

  getHistory: async (limit = 50, offset = 0): Promise<HistoryResponse> => {
    const response = await client.get<HistoryResponse>("/runs", { params: { limit, offset } });
    return response.data;
  },

  compareRuns: async (runId1: string, runId2: string) => {
    const response = await client.post("/compare", { run_id_1: runId1, run_id_2: runId2 });
    return response.data;
  },

  replayRun: async (runId: string) => {
    const response = await client.post(`/runs/${runId}/replay`);
    return response.data;
  },

  exportRun: async (runId: string, format: "json" | "csv" | "markdown") => {
    const response = await client.post(`/runs/${runId}/export`, { run_id: runId, format });
    return response.data;
  },

  // ---- Analytics ----
  getAnalytics: async (timeRange = "24h") => {
    const response = await client.get("/analytics", { params: { time_range: timeRange } });
    return response.data;
  },

  getDetectionTrends: async (days = 7) => {
    const response = await client.get("/analytics/trends", { params: { days } });
    return response.data;
  },

  getProtocolStats: async () => {
    const response = await client.get("/analytics/protocols");
    return response.data;
  },

  // ---- Investigations ----
  getInvestigations: async (limit = 20, offset = 0) => {
    const response = await client.get("/investigations", { params: { limit, offset } });
    return response.data;
  },

  getInvestigation: async (id: string) => {
    const response = await client.get(`/investigations/${id}`);
    return response.data;
  },

  // POST /investigations — name/description/protocol are Query(...) params.
  createInvestigation: async (data: {
    name: string;
    description?: string;
    protocol?: string;
  }) => {
    const response = await client.post("/investigations", null, {
      params: {
        name: data.name,
        description: data.description ?? "",
        protocol: data.protocol ?? "teleportation_qds",
      },
    });
    return response.data;
  },

  // PUT /investigations/{id}/status — status is a Query(...) param.
  updateInvestigationStatus: async (id: string, status: string) => {
    const response = await client.put(`/investigations/${id}/status`, null, {
      params: { status },
    });
    return response.data;
  },

  deleteInvestigation: async (id: string) => {
    const response = await client.delete(`/investigations/${id}`);
    return response.data;
  },

  // ---- Experiments (all Query(...) params) ----
  listExperiments: async (investigationId: string) => {
    const response = await client.get(`/investigations/${investigationId}/experiments`);
    return response.data as { experiments: Experiment[] };
  },

  getExperiment: async (investigationId: string, experimentId: string) => {
    const response = await client.get<Experiment>(
      `/investigations/${investigationId}/experiments/${experimentId}`
    );
    return response.data;
  },

  runBaselineExperiment: async (
    investigationId: string,
    body: BaselineExperimentRequest
  ) => {
    const response = await client.post(
      `/investigations/${investigationId}/experiments/baseline`,
      null,
      {
        params: {
          state: body.state,
          shots: body.shots,
          seed: body.seed,
          measurement_basis: body.measurement_basis ?? "Z",
        },
      }
    );
    return response.data;
  },

  runAttackExperiment: async (investigationId: string, body: AttackExperimentRequest) => {
    const response = await client.post(
      `/investigations/${investigationId}/experiments/attack`,
      null,
      {
        params: {
          baseline_experiment_id: body.baseline_experiment_id,
          state: body.state,
          shots: body.shots,
          attack_type: body.attack_type,
          attack_intensity: body.attack_intensity,
          seed: body.seed,
          measurement_basis: body.measurement_basis ?? "Z",
        },
      }
    );
    return response.data;
  },

  // ---- Detection ----
  // POST /investigations/{id}/detect — Query(...) params.
  runDetection: async (investigationId: string, body: DetectionRunRequest) => {
    const response = await client.post(`/investigations/${investigationId}/detect`, null, {
      params: {
        baseline_experiment_id: body.baseline_experiment_id,
        attack_experiment_id: body.attack_experiment_id,
        threshold: body.threshold ?? 0.15,
        method: body.method ?? "tv_distance",
      },
    });
    return response.data;
  },

  getDetection: async (investigationId: string) => {
    const response = await client.get(`/investigations/${investigationId}/detection`);
    return response.data;
  },

  // ---- Evidence ----
  getEvidence: async (investigationId: string, limit = 50, offset = 0) => {
    const response = await client.get(`/investigations/${investigationId}/evidence`, {
      params: { limit, offset },
    });
    return response.data;
  },

  getEvidenceExplanation: async (investigationId: string) => {
    const response = await client.get(`/investigations/${investigationId}/evidence/explanation`);
    return response.data;
  },

  // ---- System ----
  // NOTE: no /system/status route exists in the current backend; callers must
  // tolerate a failure (the Dashboard already .catch(()=>null)s this).
  getSystemStatus: async () => {
    const response = await client.get("/system/status");
    return response.data;
  },
};

export default api;
