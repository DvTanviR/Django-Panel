import useSWR, { mutate } from 'swr'
import api from '@/lib/api'

const fetcher = (url: string) => api.get(url).then(res => res.data)

export function useProjects() {
  return useSWR('/projects/', fetcher, { refreshInterval: 5000 })
}

export function useDeployments(projectSlug: string) {
  const { data, error } = useSWR(projectSlug ? `/projects/?slug=${projectSlug}` : null, fetcher)
  return { data, error }
}

export function useDomains(projectSlug: string) {
  return useSWR(projectSlug ? `/domains/?project__slug=${projectSlug}` : null, fetcher)
}

export function useEnvVars(projectSlug: string) {
  return useSWR(projectSlug ? `/env-vars/?project__slug=${projectSlug}` : null, fetcher)
}

export function refreshProjects() {
  mutate('/projects/')
}

export function refreshDeployments(projectSlug: string) {
  mutate(`/projects/?slug=${projectSlug}`)
}

export function refreshDomains(projectSlug: string) {
  mutate(`/domains/?project__slug=${projectSlug}`)
}

export function refreshEnvVars(projectSlug: string) {
  mutate(`/env-vars/?project__slug=${projectSlug}`)
}
