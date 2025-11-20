import axios from 'axios'

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

export const api = axios.create({
  baseURL: API_URL,
  headers: {
    'Content-Type': 'application/json',
  },
})

// Resume APIs
export const resumeApi = {
  upload: (file: File) => {
    const formData = new FormData()
    formData.append('file', file)
    return api.post('/api/parse', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    })
  },
  
  getParsed: (resumeId: number) => {
    return api.get(`/api/resume/${resumeId}/parsed`)
  },
  
  getScore: (resumeId: number) => {
    return api.post(`/api/score/${resumeId}`)
  },
  
  getRoleMatches: (resumeId: number, topK: number = 5) => {
    return api.get(`/api/roles/${resumeId}`, { params: { top_k: topK } })
  },
  
  getSkillSuggestions: (resumeId: number, targetRole: string) => {
    return api.post('/api/suggest', { resume_id: resumeId, target_role: targetRole })
  },
  
  list: () => {
    return api.get('/api/resumes')
  },
}

export default api

