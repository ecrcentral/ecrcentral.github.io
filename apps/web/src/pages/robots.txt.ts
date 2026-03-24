import type { APIRoute } from 'astro'

export const GET: APIRoute = () => {
  return new Response(
    [
      'User-agent: *',
      'Allow: /',
      '',
      'Sitemap: https://ecrcentral.org/sitemap-index.xml',
    ].join('\n')
  )
}
