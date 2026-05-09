export interface ProductLaunchRaw {
  title: string;
  source_url: string;
  source_domain: string;
  snippet: string;
  query_source: string;
}

export interface ProductLaunch {
  company_name: string;
  company_domain: string | null;
  product_name: string;
  tagline: string | null;
  launch_type: "new_product" | "new_feature";
  is_ai: boolean;
  score: number | null;
  source: "product_hunt" | "news";
  source_url: string;
  source_name: string | null;
  description: string | null;
  categories: string[];
  classification_reasoning: string | null;
  linkedin_url: string | null;
  on_product_hunt: boolean;
}

export interface ProductLaunchPipelineResult {
  date: string;
  source: "product_hunt" | "news";
  launchCount: number;
  stats: {
    rawResults: number;
    afterClassify: number;
    durationMs: number;
  };
}
