'use client'

import { useState, useEffect } from 'react'
import { useRouter } from 'next/navigation'
import api from '@/lib/api'
import { useAuth } from '@/lib/auth'

export default function NewProjectPage() {
  const [name, setName] = useState('')
  const [gitRepoUrl, setGitRepoUrl] = useState('')
  const [gitBranch, setGitBranch] = useState('main')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [githubConnected, setGithubConnected] = useState(false)
  const [repos, setRepos] = useState([])
  const [selectedRepo, setSelectedRepo] = useState('')
  const [showManualInput, setShowManualInput] = useState(false)
  const { user, login } = useAuth()
  const router = useRouter()

  useEffect(() => {
    api.get('/api/github/status/').then(res => {
      setGithubConnected(res.data.connected)
      if (res.data.connected) {
        loadRepos()
      }
    }).catch(() => setGithubConnected(false))
  }, [])

  const loadRepos = async () => {
    try {
      const res = await api.get('/api/github/repos/')
      setRepos(res.data.repos || [])
    } catch (e) {
      console.error('Failed to load repos')
    }
  }

  const handleConnectGithub = () => {
    window.location.href = '/api/github/connect/'
  }

  const handleRepoSelect = (repoFullName) => {
    setSelectedRepo(repoFullName)
    setName(repoFullName.split('/')[1] || repoFullName)
    const repo = repos.find(r => r.name === repoFullName)
    if (repo) {
      setGitRepoUrl(repo.url)
      setGitBranch(repo.default_branch || 'main')
    }
    setShowManualInput(false)
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setLoading(true)
    setError('')
    try {
      const res = await api.post('/api/projects/', {
        name,
        git_repo_url: gitRepoUrl,
        git_branch: gitBranch,
        build_method: 'auto',
      })
      router.push(`/projects/${res.data.slug}`)
    } catch (e: any) {
      setError(e.response?.data?.name?.[0] || e.response?.data?.git_repo_url?.[0] || 'Failed to create project')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="max-w-2xl">
      <h1 className="text-2xl font-bold text-gray-900 mb-6">New Project</h1>
      
      {!githubConnected ? (
        <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6 mb-6">
          <h2 className="text-lg font-semibold mb-2">Connect GitHub</h2>
          <p className="text-gray-600 text-sm mb-4">Connect your GitHub account to browse repos and enable auto-deploys.</p>
          <button
            onClick={handleConnectGithub}
            className="bg-gray-900 hover:bg-gray-800 text-white px-4 py-2 rounded-lg text-sm font-medium flex items-center gap-2"
          >
            <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 20 20"><path fillRule="evenodd" d="M10 0C4.477 0 0 4.484 0 10.017c0 4.425 2.865 8.18 6.839 9.504.5.092.682-.217.682-.483 0-.237-.008-.868-.013-1.703-2.782.605-3.369-1.343-3.369-1.343-.454-1.158-1.11-1.466-1.11-1.466-.908-.62.069-.608.069-.608 1.003.07 1.531 1.032 1.531 1.032.892 1.53 2.341 1.088 2.91.832.092-.647.35-1.088.636-1.338-2.22-.253-4.555-1.113-4.555-4.951 0-1.093.39-1.988 1.029-2.688-.103-.253-.446-1.272.098-2.65 0 0 .84-.27 2.75 1.026A9.564 9.564 0 0110 4.844c.85.004 1.705.115 2.504.337 1.909-1.296 2.747-1.027 2.747-1.027.546 1.379.203 2.398.1 2.651.64.7 1.028 1.595 1.028 2.688 0 3.848-2.339 4.695-4.566 4.943.359.309.678.92.678 1.855 0 1.338-.012 2.419-.012 2.747 0 .268.18.58.688.482A10.019 10.019 0 0020 10.017C20 4.484 15.522 0 10 0z" clipRule="evenodd" /></svg>
            Connect GitHub
          </button>
        </div>
      ) : (
        <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6 mb-6">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-lg font-semibold">Select Repository</h2>
            <button
              onClick={() => setShowManualInput(!showManualInput)}
              className="text-sm text-primary-600 hover:text-primary-700"
            >
              Enter manually
            </button>
          </div>
          
          {!showManualInput && repos.length > 0 && (
            <div className="space-y-2 max-h-64 overflow-y-auto border rounded-lg">
              {repos.map((repo) => (
                <div
                  key={repo.name}
                  onClick={() => handleRepoSelect(repo.name)}
                  className={`p-3 cursor-pointer hover:bg-gray-50 border-b last:border-0 ${selectedRepo === repo.name ? 'bg-primary-50' : ''}`}
                >
                  <p className="font-medium text-gray-900">{repo.name}</p>
                  <p className="text-xs text-gray-500">Default: {repo.default_branch}</p>
                </div>
              ))}
            </div>
          )}
          
          {showManualInput && (
            <div className="space-y-3 mt-3">
              <div>
                <label className="block text-sm font-medium text-gray-700">Git Repository URL</label>
                <input
                  type="url"
                  value={gitRepoUrl}
                  onChange={(e) => { setGitRepoUrl(e.target.value); setSelectedRepo(''); }}
                  placeholder="https://github.com/username/repo.git"
                  className="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-lg shadow-sm focus:outline-none focus:ring-primary-500 focus:border-primary-500"
                />
              </div>
            </div>
          )}
        </div>
      )}

      <form onSubmit={handleSubmit} className="bg-white rounded-xl shadow-sm border border-gray-200 p-6 space-y-4">
        {error && <p className="text-red-600 text-sm">{error}</p>}
        <div>
          <label className="block text-sm font-medium text-gray-700">Project Name</label>
          <input
            type="text"
            value={name}
            onChange={(e) => setName(e.target.value)}
            className="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-lg shadow-sm focus:outline-none focus:ring-primary-500 focus:border-primary-500"
            required
          />
        </div>
        <div>
          <label className="block text-sm font-medium text-gray-700">Branch</label>
          <input
            type="text"
            value={gitBranch}
            onChange={(e) => setGitBranch(e.target.value)}
            className="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-lg shadow-sm focus:outline-none focus:ring-primary-500 focus:border-primary-500"
          />
        </div>
        <button
          type="submit"
          disabled={loading || !gitRepoUrl}
          className="bg-primary-600 hover:bg-primary-700 disabled:opacity-50 text-white px-4 py-2 rounded-lg font-medium"
        >
          {loading ? 'Creating...' : 'Create Project'}
        </button>
      </form>
    </div>
  )
}
