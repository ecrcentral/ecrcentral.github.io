export interface Funder {
  id: string
  legacy_id: number | null
  slug: string
  name: string
  short_name: string | null
  funder_registry_id: string | null
  country: string
  website: string | null
  logo: string | null
  legacy_logo_path: string | null
  dora: boolean
  aliases: string[]
  description: string | null
  status: 'active' | 'inactive' | 'archived' | 'draft'
  featured: boolean
  review_status: 'approved' | 'pending' | 'rejected'
  last_verified: string | null
  verified_by: string | null
  created_at: string | null
  updated_at: string | null
  source: string
  // denormalized (added by build script)
  active_funding_count?: number
  active_travel_grant_count?: number
}

export interface Funding {
  id: string
  legacy_id: number | null
  slug: string
  name: string
  description: string | null
  url: string
  funders: string[]
  funder_names?: string[]         // denormalized
  funder_logos?: (string | null)[] // denormalized
  legacy_funder_name: string | null
  host_country: string | null
  applicant_country: string | null
  academic_level: string | null
  career_levels: string[]
  career_level_names?: string[]
  years_since_phd: string | null
  duration: string | null
  award: string | null
  mobility_rule: string | null
  research_costs: string | null
  deadline: string | null
  deadline_raw: string | null
  deadline_month: string | null
  diversity: string | null
  comments: string | null
  benefits: string | null
  frequency: string | null
  fileds: string | null
  featured: boolean
  review_status: 'approved' | 'pending' | 'rejected'
  status: 'active' | 'expired' | 'archived' | 'draft'
  last_verified: string | null
  verified_by: string | null
  legacy_user_id: number | null
  created_at: string | null
  updated_at: string | null
  subjects: string[]
  subject_names?: string[]
  funding_purposes: string[]
  funding_purpose_names?: string[]
  search_text: string | null
  source: string
}

export interface TravelGrant {
  id: string
  legacy_id: number | null
  slug: string
  name: string
  url: string
  description: string | null
  funders: string[]
  funder_names?: string[]
  funder_logos?: (string | null)[]
  legacy_funder_name: string | null
  applicant_country: string | null
  host_country: string | null
  award: string | null
  deadline: string | null
  deadline_raw: string | null
  deadline_month: string | null
  membership: string | null
  membership_time: string | null
  purpose_text: string | null
  career_levels: string[]
  career_level_names?: string[]
  subjects: string[]
  subject_names?: string[]
  travel_purposes: string[]
  travel_purpose_names?: string[]
  featured: boolean
  review_status: 'approved' | 'pending' | 'rejected'
  status: 'active' | 'expired' | 'archived' | 'draft'
  last_verified: string | null
  verified_by: string | null
  created_at: string | null
  updated_at: string | null
  search_text: string | null
  source: string
}

export interface Resource {
  id: string
  legacy_id: number | null
  slug: string
  name: string
  url: string
  description: string | null
  source_name: string | null
  funders: string[]
  funder_names?: string[]
  resource_categories: string[]
  resource_category_names?: string[]
  subjects: string[]
  subject_names?: string[]
  featured: boolean
  review_status: 'approved' | 'pending' | 'rejected'
  status: 'active' | 'expired' | 'archived' | 'draft'
  last_verified: string | null
  verified_by: string | null
  created_at: string | null
  updated_at: string | null
  source: string
}

export interface VocabTerm {
  id: string
  legacy_id: number | null
  slug: string
  name: string
  parent_id?: number | null
  parent_slug?: string | null
}

export interface FacetValue {
  value: string
  label: string
  count: number
}

export interface FacetGroup {
  [key: string]: FacetValue[]
}

export interface Facets {
  fundings: FacetGroup
  travel_grants: FacetGroup
  resources: FacetGroup
  funders: FacetGroup
}

export interface HomepageFeatured {
  featured_fundings: Funding[]
  featured_travel_grants: TravelGrant[]
  featured_resources: Resource[]
  featured_funders: Funder[]
  recently_updated: Array<(Funding | TravelGrant | Resource) & { _type: string }>
}

export interface SearchDocument {
  id: string
  type: 'funding' | 'travel-grant' | 'resource' | 'funder'
  slug: string
  name: string
  description: string
  funder_names: string
  country: string
  career_levels: string
  subjects: string
}
