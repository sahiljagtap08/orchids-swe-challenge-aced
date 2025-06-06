const API_BASE_URL = process.env.NODE_ENV === 'production' 
  ? '' 
  : (process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000');

export interface CloneJobRequest {
  url: string
  model: string
  full_site?: boolean      // New: Enable full website cloning
  max_pages?: number       // New: Limit for full site cloning
  include_assets?: boolean // New: Download all assets
}

export interface ScrapeMetadata {
  title: string
  description: string
  viewport_width: number
  viewport_height: number
  load_time: number
  screenshot_url?: string
  assets_count: number
}

export interface PageCloneResult {
  url: string
  path: string
  html: string
  css?: string
  screenshot: string
  metadata?: ScrapeMetadata
}

export interface FullSiteCloneResult {
  base_url: string
  pages: PageCloneResult[]
  sitemap: string[]
  total_pages: number
  total_assets: number
  clone_time: number
  model_used: string
}

export interface CloneJobResponse {
  job_id: string
  status: 'pending' | 'discovering' | 'scraping' | 'processing' | 'completed' | 'failed'
  url: string
  model: string
  created_at: string
  updated_at: string
  progress?: string
  result?: {
    html: string
    css?: string
    reasoning: string
    model_used: string
    processing_time: number
  }
  full_site_result?: FullSiteCloneResult // New: Full site clone results
  error?: string
}

class APIClient {
  private baseURL: string

  constructor(baseURL: string = API_BASE_URL) {
    this.baseURL = baseURL
  }

  async createCloneJob(request: CloneJobRequest): Promise<CloneJobResponse> {
    const response = await fetch(`${this.baseURL}/api/v1/clone`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(request),
    })

    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: 'Network error' }))
      throw new Error(error.detail || 'Failed to create clone job')
    }

    return response.json()
  }

  async getCloneJob(jobId: string): Promise<CloneJobResponse> {
    const response = await fetch(`${this.baseURL}/api/v1/clone/${jobId}`)

    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: 'Network error' }))
      throw new Error(error.detail || 'Failed to get clone job')
    }

    return response.json()
  }

  async pollCloneJob(
    jobId: string,
    onUpdate: (job: CloneJobResponse) => void,
    intervalMs: number = 1000
  ): Promise<CloneJobResponse> {
    return new Promise((resolve, reject) => {
      const poll = async () => {
        try {
          const job = await this.getCloneJob(jobId)
          onUpdate(job)

          if (job.status === 'completed') {
            resolve(job)
          } else if (job.status === 'failed') {
            reject(new Error(job.error || 'Clone job failed'))
          } else {
            setTimeout(poll, intervalMs)
          }
        } catch (error) {
          reject(error)
        }
      }

      poll()
    })
  }

  getDownloadUrl(jobId: string): string {
    return `${this.baseURL}/api/v1/clone/${jobId}/download`
  }

  async checkHealth(): Promise<{ status: string; service: string; version: string }> {
    const response = await fetch(`${this.baseURL}/health`)
    
    if (!response.ok) {
      throw new Error('Backend health check failed')
    }

    return response.json()
  }

  getLogsStream(jobId: string, onLog: (log: string) => void, onComplete: () => void): EventSource {
    const eventSource = new EventSource(`${this.baseURL}/api/v1/clone/${jobId}/logs`)
    
    eventSource.onmessage = (event) => {
      if (event.data === "[END]") {
        eventSource.close()
        onComplete()
        return
      }
      onLog(event.data)
    }

    eventSource.onerror = (err) => {
      console.error("EventSource failed:", err)
      eventSource.close()
      onComplete()
    }
    
    return eventSource
  }
}

export const apiClient = new APIClient()
export default apiClient 