import { api } from '../../api'

export type Format = 'mp3' | 'mp4'
export type JobStatus = 'queued' | 'downloading' | 'converting' | 'done' | 'error'

export interface Job {
  id: string
  url: string
  format: Format
  status: JobStatus
  progress: number
  title: string | null
  filename: string | null
  error: string | null
}

export const isActive = (job: Job) =>
  job.status === 'queued' || job.status === 'downloading' || job.status === 'converting'

export const listJobs = () => api<Job[]>('/youtube/jobs')

export const createJob = (url: string, format: Format) =>
  api<Job>('/youtube/jobs', { method: 'POST', body: JSON.stringify({ url, format }) })

export const fileUrl = (job: Job) => `/api/youtube/jobs/${job.id}/file`
