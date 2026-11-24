import { useState, type FormEvent } from 'react'
import { fileUrl, isActive, type Format, type Job } from './api'
import { useJobs } from './useJobs'

function JobRow({ job }: { job: Job }) {
  return (
    <li className="job">
      <div className="job-head">
        <span className="job-title">{job.title ?? job.url}</span>
        <span className={`badge badge-${job.status}`}>
          {job.format} · {job.status}
        </span>
      </div>
      {isActive(job) && (
        <progress value={job.progress} max={100} aria-label="Download progress" />
      )}
      {job.status === 'done' && (
        <a className="save" href={fileUrl(job)} download>
          Save {job.filename}
        </a>
      )}
      {job.status === 'error' && <p className="error">{job.error}</p>}
    </li>
  )
}

export default function YoutubePage() {
  const { jobs, start } = useJobs()
  const [url, setUrl] = useState('')
  const [format, setFormat] = useState<Format>('mp3')
  const [error, setError] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)

  async function onSubmit(event: FormEvent) {
    event.preventDefault()
    setError(null)
    setBusy(true)
    try {
      await start(url.trim(), format)
      setUrl('')
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Something went wrong')
    } finally {
      setBusy(false)
    }
  }

  return (
    <section>
      <h2>YouTube downloader</h2>
      <form onSubmit={onSubmit} className="row">
        <input
          type="url"
          required
          placeholder="https://www.youtube.com/watch?v=…"
          value={url}
          onChange={(e) => setUrl(e.target.value)}
          aria-label="YouTube URL"
        />
        <select value={format} onChange={(e) => setFormat(e.target.value as Format)} aria-label="Format">
          <option value="mp3">mp3 (audio)</option>
          <option value="mp4">mp4 (video)</option>
        </select>
        <button type="submit" disabled={busy}>
          {busy ? 'Starting…' : 'Download'}
        </button>
      </form>
      {error && <p className="error" role="alert">{error}</p>}
      <ul className="jobs">
        {jobs.map((job) => (
          <JobRow key={job.id} job={job} />
        ))}
      </ul>
      {jobs.length === 0 && <p className="muted">No downloads yet. Paste a link above.</p>}
    </section>
  )
}
