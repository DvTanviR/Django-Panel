'use client'

import { useEffect, useState } from 'react'
import { useParams } from 'next/navigation'
import api from '@/lib/api'
import { refreshDomains } from '@/lib/hooks'

export default function ProjectPage() {
  const params = useParams()
  const [project, setProject] = useState<any>(null)
  const [deployments, setDeployments] = useState<any[]>([])
  const [domains, setDomains] = useState<any[]>([])
  const [envVars, setEnvVars] = useState<any[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    const slug = params.slug as string
    api.get(`/projects/?slug=${slug}`).then(res => {
      const proj = res.data[0]
      if (proj) {
        setProject(proj)
        return Promise.all([
          api.get(`/deployments/?project__id__exact=${proj.id}`),
          api.get(`/domains/?project_id=${proj.id}`),
          api.get(`/env-vars/?project_id=${proj.id}`),
        ]).then(([dep, dom, env]) => {
          setDeployments(dep.data.slice(0, 20))
          setDomains(dom.data)
          setEnvVars(env.data)
        })
      }
    }).finally(() => setLoading(false))
  }, [params.slug])

  if (loading) return <p className="text-gray-500">Loading...</p>
  if (!project) return <p className="text-red-600">Project not found</p>

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-start">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">{project.name}</h1>
          <p className="text-gray-500">{project.git_repo_url} <span className="text-xs bg-gray-100 px-2 py-1 rounded">{project.git_branch}</span></p>
        </div>
        <span className={`px-3 py-1 rounded-full text-sm font-medium ${
          project.status === 'running' ? 'bg-green-100 text-green-800' :
          project.status === 'failed' ? 'bg-red-100 text-red-800' :
          'bg-yellow-100 text-yellow-800'
        }`}>
          {project.status.replace('_', ' ')}
        </span>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
          <h2 className="text-lg font-semibold mb-4">Deployments</h2>
          {deployments.length === 0 ? (
            <p className="text-gray-500 text-sm">No deployments yet</p>
          ) : (
            <div className="space-y-3">
              {deployments.map((d: any) => (
                <div key={d.id} className="flex items-center justify-between py-2 border-b border-gray-100 last:border-0">
                  <div>
                    <p className="text-sm font-medium text-gray-900">{d.git_commit_sha?.slice(0, 8)}</p>
                    <p className="text-xs text-gray-500">{d.git_commit_message || 'Manual deploy'}</p>
                  </div>
                  <span className={`text-xs px-2 py-1 rounded-full ${
                    d.status === 'healthy' ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800'
                  }`}>
                    {d.status}
                  </span>
                </div>
              ))}
            </div>
          )}
        </div>

        <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
          <h2 className="text-lg font-semibold mb-4">Domains</h2>
          {domains.length === 0 ? (
            <p className="text-gray-500 text-sm">No custom domains yet</p>
          ) : (
            <div className="space-y-3">
              {domains.map((d: any) => (
                <div key={d.id} className="flex items-center justify-between py-2 border-b border-gray-100 last:border-0">
                  <div>
                    <p className="text-sm font-medium text-gray-900">{d.hostname}</p>
                    <p className="text-xs text-gray-500">TLS: {d.tls_status} | DNS: {d.dns_verified ? 'Verified' : 'Pending'}</p>
                  </div>
                  <div className="flex items-center gap-2">
                    <span className={`text-xs px-2 py-1 rounded-full ${
                      d.dns_verified ? 'bg-green-100 text-green-800' : 'bg-yellow-100 text-yellow-800'
                    }`}>
                      {d.dns_verified ? 'Verified' : 'Verifying'}
                    </span>
                    {!d.dns_verified && (
                      <button
                        onClick={() => handleVerify(d.id)}
                        className="text-xs bg-primary-600 hover:bg-primary-700 text-white px-2 py-1 rounded"
                      >
                        Verify
                      </button>
                    )}
                  </div>
                </div>
              ))}
            </div>
          )}
          <DomainForm projectId={project.id} onDomainAdded={async () => {
            const res = await api.get(`/domains/?project_id=${project.id}`)
            setDomains(res.data)
          }} />
        </div>

        <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
          <h2 className="text-lg font-semibold mb-4">Environment Variables</h2>
          {envVars.length === 0 ? (
            <p className="text-gray-500 text-sm">No environment variables</p>
          ) : (
            <div className="space-y-2">
              {envVars.map((ev: any) => (
                <div key={ev.id} className="flex items-center justify-between py-2 border-b border-gray-100 last:border-0">
                  <div>
                    <p className="text-sm font-medium text-gray-900">{ev.key}</p>
                    <p className="text-xs text-gray-500">{ev.is_secret ? '••••••' : ev.value_encrypted}</p>
                  </div>
                </div>
              ))}
            </div>
          )}
          <button className="mt-4 text-sm text-primary-600 hover:text-primary-700 font-medium">
            + Add Variable
          </button>
        </div>

        <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
          <h2 className="text-lg font-semibold mb-4">Actions</h2>
          <div className="space-y-2">
            <button className="w-full bg-primary-600 hover:bg-primary-700 text-white px-4 py-2 rounded-lg text-sm font-medium">
              Deploy Now
            </button>
            <button className="w-full bg-gray-100 hover:bg-gray-200 text-gray-700 px-4 py-2 rounded-lg text-sm font-medium">
              Restart
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}

function DomainForm({ projectId, onDomainAdded }: { projectId: number, onDomainAdded: () => void }) {
  const [hostname, setHostname] = useState('')
  const [submitting, setSubmitting] = useState(false)
  
  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setSubmitting(true)
    try {
      await api.post('/api/domains/', {
        project: projectId,
        hostname,
        is_primary: true,
      })
      setHostname('')
      onDomainAdded()
    } catch (e) {
      console.error(e)
    } finally {
      setSubmitting(false)
    }
  }
  
  const handleVerify = async (domainId: number) => {
    try {
      await api.post(`/api/domains/${domainId}/verify/`, {})
      onDomainAdded()
    } catch (e) {
      console.error(e)
    }
  }
  
  return (
    <form onSubmit={handleSubmit} className="mt-4 pt-4 border-t">
      <div className="flex gap-2">
        <input
          type="text"
          value={hostname}
          onChange={(e) => setHostname(e.target.value)}
          placeholder="app.example.com"
          className="flex-1 px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-primary-500 focus:border-primary-500"
          required
        />
        <button
          type="submit"
          disabled={submitting}
          className="bg-primary-600 hover:bg-primary-700 disabled:opacity-50 text-white px-3 py-2 rounded-lg text-sm font-medium"
        >
          Add
        </button>
      </div>
      <p className="text-xs text-gray-500 mt-2">Add an A record pointing to your server IP.</p>
    </form>
  )
}
