'use client'

import Link from 'next/link'
import { Play, Stop, RotateCw, Globe, Settings, Trash2 } from 'lucide-react'
import { useState } from 'react'
import api from '@/lib/api'
import { refreshProjects } from '@/lib/hooks'

interface ProjectCardProps {
  project: {
    id: number
    name: string
    slug: string
    status: string
    created_at: string
    git_repo_url: string
    git_branch: string
  }
}

export default function ProjectCard({ project }: ProjectCardProps) {
  const [deploying, setDeploying] = useState(false)
  const [stopping, setStopping] = useState(false)

  const statusColors: Record<string, string> = {
    running: 'bg-green-100 text-green-800',
    stopped: 'bg-red-100 text-red-800',
    building: 'bg-yellow-100 text-yellow-800',
    deploying: 'bg-yellow-100 text-yellow-800',
    failed: 'bg-red-100 text-red-800',
    never_deployed: 'bg-gray-100 text-gray-800',
  }

  const handleDeploy = async () => {
    setDeploying(true)
    try {
      await api.post(`/projects/${project.id}/deploy/`)
      setTimeout(refreshProjects, 2000)
    } catch (e) {
      console.error(e)
    } finally {
      setDeploying(false)
    }
  }

  const handleStop = async () => {
    setStopping(true)
    try {
      await api.post(`/projects/${project.id}/stop/`)
      setTimeout(refreshProjects, 2000)
    } catch (e) {
      console.error(e)
    } finally {
      setStopping(false)
    }
  }

  return (
    <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
      <div className="flex justify-between items-start mb-4">
        <div>
          <h3 className="text-lg font-semibold text-gray-900">{project.name}</h3>
          <p className="text-sm text-gray-500">{project.git_repo_url}</p>
          <p className="text-xs text-gray-400 mt-1">Branch: {project.git_branch}</p>
        </div>
        <span className={`px-2 py-1 rounded-full text-xs font-medium ${statusColors[project.status] || 'bg-gray-100 text-gray-800'}`}>
          {project.status.replace('_', ' ')}
        </span>
      </div>
      <div className="flex gap-2 mt-4">
        <button
          onClick={handleDeploy}
          disabled={deploying}
          className="flex-1 bg-primary-600 hover:bg-primary-700 disabled:opacity-50 text-white px-3 py-2 rounded-lg text-sm font-medium flex items-center justify-center gap-2"
        >
          <Play className="w-4 h-4" />
          {deploying ? 'Deploying...' : 'Deploy'}
        </button>
        <button
          onClick={handleStop}
          disabled={stopping}
          className="bg-gray-100 hover:bg-gray-200 text-gray-700 px-3 py-2 rounded-lg text-sm font-medium"
        >
          {project.status === 'running' ? <Stop className="w-4 h-4" /> : <RotateCw className="w-4 h-4" />}
        </button>
        <Link href={`/projects/${project.id}`} className="bg-gray-100 hover:bg-gray-200 text-gray-700 px-3 py-2 rounded-lg text-sm font-medium">
          <Settings className="w-4 h-4" />
        </Link>
      </div>
    </div>
  )
}
