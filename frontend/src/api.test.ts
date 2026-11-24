import { describe, expect, it } from 'vitest'
import { errorMessage } from './api'

describe('errorMessage', () => {
  it('shows a FastAPI 422 validation message without the pydantic prefix', () => {
    const body = {
      detail: [{ loc: ['body', 'url'], msg: 'Value error, Only YouTube URLs are supported' }],
    }
    expect(errorMessage(body, 'fallback')).toBe('Only YouTube URLs are supported')
  })

  it('passes through string details (502/404/409)', () => {
    expect(errorMessage({ detail: 'Video unavailable' }, 'fallback')).toBe('Video unavailable')
  })

  it('falls back when the body is not a FastAPI error', () => {
    expect(errorMessage(null, 'Request failed (500)')).toBe('Request failed (500)')
  })
})
