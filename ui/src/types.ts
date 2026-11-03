export type AppTarget = { file: string; line: number; app_var: string };

export type ProjectScan = {
  root: string;
  framework: string | null;
  python_files: string[];
  apps: AppTarget[];
  existing_segments: Record<string, string[]>;
  has_tests: boolean;
  warnings: string[];
};

export type ParamSpec = {
  type: string;
  default?: unknown;
  min?: number;
  description?: string;
};

export type SegmentManifest = {
  name: string;
  version: string;
  display_name: string;
  summary: string;
  kind: string;
  stage: string;
  params: Record<string, ParamSpec>;
  adapt: Record<string, unknown>;
  tests: string[];
};

export type Preview = {
  file: string;
  changed: boolean;
  reason: string;
  diff: string;
};

export type TestResult = {
  ran: boolean;
  passed: boolean | null;
  exit_code: number | null;
  output_tail: string;
};

export type Verify = {
  syntax_ok: boolean;
  syntax_error: string | null;
  tests: TestResult;
};

export type ApplyResult = Preview & { verify: Verify };
