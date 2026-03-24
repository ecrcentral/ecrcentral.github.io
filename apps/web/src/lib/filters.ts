import type { Funding, TravelGrant, Resource, Funder } from './schema'

export type FilterState = Record<string, string[]>

export function parseFiltersFromURL(search: string): FilterState {
  const params = new URLSearchParams(search)
  const filters: FilterState = {}
  for (const [key, value] of params.entries()) {
    if (!filters[key]) filters[key] = []
    filters[key].push(value)
  }
  return filters
}

export function filtersToURL(filters: FilterState): string {
  const params = new URLSearchParams()
  for (const [key, values] of Object.entries(filters)) {
    for (const value of values) {
      params.append(key, value)
    }
  }
  return params.toString()
}

export function filterFundings(fundings: Funding[], filters: FilterState, query: string): Funding[] {
  return fundings.filter(item => {
    if (filters.status?.length && !filters.status.includes(item.status)) return false
    if (filters.funder?.length && !item.funders.some(f => filters.funder!.includes(f))) return false
    if (filters.career_level?.length && !item.career_levels.some(c => filters.career_level!.includes(c))) return false
    if (filters.subject?.length && !item.subjects.some(s => filters.subject!.includes(s))) return false
    if (filters.funding_purpose?.length && !item.funding_purposes.some(p => filters.funding_purpose!.includes(p))) return false
    if (filters.applicant_country?.length && item.applicant_country && !filters.applicant_country.some(c => item.applicant_country!.toLowerCase().includes(c.toLowerCase()))) return false
    if (filters.host_country?.length && item.host_country && !filters.host_country.some(c => item.host_country!.toLowerCase().includes(c.toLowerCase()))) return false
    if (filters.deadline_month?.length && item.deadline_month && !filters.deadline_month.includes(item.deadline_month)) return false
    if (filters.frequency?.length && item.frequency && !filters.frequency.includes(item.frequency)) return false
    if (filters.featured?.length && filters.featured.includes('true') && !item.featured) return false
    if (query) {
      const q = query.toLowerCase()
      const searchable = (item.search_text || item.name + ' ' + (item.description || '')).toLowerCase()
      if (!searchable.includes(q)) return false
    }
    return true
  })
}

export function filterTravelGrants(grants: TravelGrant[], filters: FilterState, query: string): TravelGrant[] {
  return grants.filter(item => {
    if (filters.status?.length && !filters.status.includes(item.status)) return false
    if (filters.funder?.length && !item.funders.some(f => filters.funder!.includes(f))) return false
    if (filters.career_level?.length && !item.career_levels.some(c => filters.career_level!.includes(c))) return false
    if (filters.subject?.length && !item.subjects.some(s => filters.subject!.includes(s))) return false
    if (filters.travel_purpose?.length && !item.travel_purposes.some(p => filters.travel_purpose!.includes(p))) return false
    if (filters.membership?.length && filters.membership.includes('required') && !(item.membership?.toLowerCase() === 'yes')) return false
    if (filters.applicant_country?.length && item.applicant_country && !filters.applicant_country.some(c => item.applicant_country!.toLowerCase().includes(c.toLowerCase()))) return false
    if (query) {
      const q = query.toLowerCase()
      const searchable = (item.search_text || item.name + ' ' + (item.description || '')).toLowerCase()
      if (!searchable.includes(q)) return false
    }
    return true
  })
}

export function filterResources(resources: Resource[], filters: FilterState, query: string): Resource[] {
  return resources.filter(item => {
    if (filters.status?.length && !filters.status.includes(item.status)) return false
    if (filters.category?.length && !item.resource_categories.some(c => filters.category!.includes(c))) return false
    if (filters.subject?.length && !item.subjects.some(s => filters.subject!.includes(s))) return false
    if (filters.featured?.length && filters.featured.includes('true') && !item.featured) return false
    if (query) {
      const q = query.toLowerCase()
      const searchable = (item.name + ' ' + (item.description || '') + ' ' + (item.source_name || '')).toLowerCase()
      if (!searchable.includes(q)) return false
    }
    return true
  })
}

export function filterFunders(funders: Funder[], filters: FilterState, query: string): Funder[] {
  return funders.filter(item => {
    if (filters.status?.length && !filters.status.includes(item.status)) return false
    if (filters.country?.length && !filters.country.some(c => item.country.toLowerCase().includes(c.toLowerCase()))) return false
    if (filters.featured?.length && filters.featured.includes('true') && !item.featured) return false
    if (query) {
      const q = query.toLowerCase()
      if (!item.name.toLowerCase().includes(q) && !item.country.toLowerCase().includes(q)) return false
    }
    return true
  })
}
