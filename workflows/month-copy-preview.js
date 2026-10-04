export const meta = {
  name: 'month-copy-preview',
  description: 'For an already-parsed month, adapt every post\'s copy per platform and run the compliance check in parallel, then return one review sheet — no image or video generation, no credits spent',
  phases: ['List posts', 'Adapt and check each post', 'Review sheet'],
}

// args: { brand: "brand-slug", month: "YYYY-MM" }
// Copy and compliance only. Creative generation spends provider credits and needs the user's
// price-check approval, which a workflow cannot ask for mid-run, so it is deliberately out of scope.
const input = args || {}
if (!input.brand || !input.month) {
  return 'month-copy-preview needs args.brand and args.month, e.g. {"brand": "acme-coffee", "month": "2026-11"}. Parse the calendar first with /socialforge:parse-calendar.'
}

phase('List posts')
const listing = await agent(
  `List the posts of SocialForge brand "${input.brand}" for month ${input.month} from the parsed calendar the /socialforge:parse-calendar skill produced ` +
  '(read the month\'s calendar file in the SocialForge workspace; do not re-parse or modify anything). Return each post id with its platforms.',
  {
    label: 'list posts',
    schema: {
      type: 'object',
      required: ['posts'],
      properties: {
        posts: {
          type: 'array',
          items: {
            type: 'object',
            required: ['id', 'platforms'],
            properties: { id: { type: 'string' }, platforms: { type: 'array', items: { type: 'string' } } },
          },
        },
        note: { type: 'string' },
      },
    },
  },
)
if (!listing || listing.posts.length === 0) {
  return `No parsed posts found for ${input.brand} ${input.month}${listing && listing.note ? ': ' + listing.note : ''}. Run /socialforge:parse-calendar first.`
}
log(`${listing.posts.length} posts to adapt`)

phase('Adapt and check each post')
const perPost = await pipeline(listing.posts, post =>
  agent(
    `For SocialForge brand "${input.brand}", month ${input.month}, post ${post.id}: adapt the post's copy for ${post.platforms.join(', ')} ` +
    'with the /socialforge:adapt-copy skill, then check each adaptation against the brand\'s compliance rules (banned phrases, required disclaimers, ' +
    'platform restrictions) the way the compliance-checker agent does. Save the adapted copy where adapt-copy normally saves it. ' +
    'Do NOT generate, edit or composite any image or video. Report pass/fail per platform with the exact rule for any failure.',
    {
      label: post.id,
      schema: {
        type: 'object',
        required: ['post', 'platforms'],
        properties: {
          post: { type: 'string' },
          platforms: {
            type: 'array',
            items: {
              type: 'object',
              required: ['platform', 'compliance', 'issues'],
              properties: {
                platform: { type: 'string' },
                compliance: { type: 'string', enum: ['pass', 'fail'] },
                issues: { type: 'array', items: { type: 'string' } },
              },
            },
          },
        },
      },
    },
  ),
)

phase('Review sheet')
const done = perPost.filter(Boolean)
const failing = done.filter(p => p.platforms.some(x => x.compliance === 'fail'))
log(`${done.length} posts adapted; ${failing.length} with compliance failures`)
return {
  brand: input.brand,
  month: input.month,
  posts_adapted: done.length,
  posts_missing: listing.posts.length - done.length,
  compliance_failures: failing,
  next_step: 'Review the failures, then quote creative with /socialforge:price-check before generating any images or video.',
}
