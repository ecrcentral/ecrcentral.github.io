import type { APIRoute } from 'astro'
import fundings from '@data/built/fundings.json'
import travelGrants from '@data/built/travel-grants.json'
import resources from '@data/built/resources.json'
import funders from '@data/built/funders.json'

const SITE = 'https://ecrcentral.org'

const staticPages = [
  { url: '/', priority: '1.0', changefreq: 'weekly' },
  { url: '/fundings/', priority: '0.9', changefreq: 'daily' },
  { url: '/travel-grants/', priority: '0.9', changefreq: 'daily' },
  { url: '/resources/', priority: '0.9', changefreq: 'weekly' },
  { url: '/funders/', priority: '0.8', changefreq: 'weekly' },
  { url: '/about/', priority: '0.6', changefreq: 'monthly' },
  { url: '/contribute/', priority: '0.6', changefreq: 'monthly' },
]

function url(path: string, priority: string, changefreq: string) {
  return `  <url>
    <loc>${SITE}${path}</loc>
    <changefreq>${changefreq}</changefreq>
    <priority>${priority}</priority>
  </url>`
}

export const GET: APIRoute = () => {
  const fundingUrls = (fundings as { slug: string }[])
    .map(f => url(`/fundings/${f.slug}/`, '0.7', 'weekly'))

  const grantUrls = (travelGrants as { slug: string }[])
    .map(f => url(`/travel-grants/${f.slug}/`, '0.7', 'weekly'))

  const resourceUrls = (resources as { slug: string }[])
    .map(f => url(`/resources/${f.slug}/`, '0.6', 'monthly'))

  const funderUrls = (funders as { slug: string }[])
    .map(f => url(`/funders/${f.slug}/`, '0.6', 'monthly'))

  const xml = `<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
${staticPages.map(p => url(p.url, p.priority, p.changefreq)).join('\n')}
${fundingUrls.join('\n')}
${grantUrls.join('\n')}
${resourceUrls.join('\n')}
${funderUrls.join('\n')}
</urlset>`

  return new Response(xml, {
    headers: { 'Content-Type': 'application/xml; charset=utf-8' },
  })
}
