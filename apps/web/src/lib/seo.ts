export interface SEOProps {
  title: string
  description: string
  canonical?: string
  ogImage?: string
  type?: 'website' | 'article'
}

export function makeSEO(props: SEOProps & { siteUrl?: string }): SEOProps & { fullTitle: string } {
  const siteName = 'ECRcentral'
  const fullTitle = props.title.includes(siteName) ? props.title : `${props.title} | ${siteName}`
  return { ...props, fullTitle }
}

export const defaultSEO: SEOProps = {
  title: 'ECRcentral',
  description: 'Funding opportunities, travel grants, and resources for early career researchers.',
}
