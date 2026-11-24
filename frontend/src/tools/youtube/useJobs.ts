import { useCallback, useEffect, useState } from 'react'
import { createJob, isActive, listJobs, type Format, type Job } from './api'

/** Job list that polls once a second while anything is still running. */
export function useJobs() {
  const [jobs, setJobs] = useState<Job[]>([])

  const refresh = useCallback(async () => {
    try {
      setJobs(await listJobs())
    } catch {
      // transient poll failure; the next tick retries
    }
  }, [])

  useEffect(() => {
    void refresh()
  }, [refresh])

  const hasActive = jobs.some(isActive)
  useEffect(() => {
    if (!hasActive) return
    const timer = setInterval(() => void refresh(), 1000)
    return () => clearInterval(timer)
  }, [hasActive, refresh])

  const start = useCallback(async (url: string, format: Format) => {
    const job = await createJob(url, format)
    setJobs((prev) => [job, ...prev.filter((j) => j.id !== job.id)])
  }, [])

  return { jobs, start }
}
