# Editorial Policy

This document describes what ECRcentral includes, how entries are reviewed, and how the database is kept accurate over time. It is intended for both contributors and maintainers.

---

## Purpose of ECRcentral

ECRcentral is a curated, community-maintained database of funding opportunities, travel grants, and resources specifically relevant to early career researchers (ECRs). The goal is to be a practical, trustworthy reference — not an exhaustive aggregator of everything that exists.

Entries are included because they are:
- Genuinely relevant to ECRs
- From reputable sources
- Currently active or likely to recur
- Not already well-covered by existing specialist databases

---

## Who is an "early career researcher"?

ECRcentral uses a broad definition that includes:

- Bachelor students (final year, research-focused programmes)
- Master students
- PhD candidates and students
- Postdoctoral researchers
- Junior faculty and early-stage independent researchers (typically within 10 years of PhD)
- Medical doctors (MD) pursuing research careers

An entry does not need to be exclusively for ECRs to be included, but the opportunity must be accessible to at least one of these groups and relevant to their career stage.

---

## Funding opportunities — inclusion criteria

A funding opportunity should be listed if it meets all of the following:

1. **Active or recurring.** The opportunity is currently open, will reopen, or recurs regularly (annually, bi-annually, rolling). One-time opportunities that have closed permanently should be archived, not listed as active.

2. **Accessible to ECRs.** At least one eligible career stage is PhD, postdoc, junior faculty, MD, master, or bachelor.

3. **From a named, identifiable organization.** The funder must be a real institution, society, foundation, or government body with a verifiable web presence.

4. **Has an official URL.** The entry must link to an official application page or funding programme page, not a news article or third-party aggregator.

5. **Sufficient detail available.** At minimum, the name, URL, funder, and some description of the purpose must be known. Entries with no description are not accepted.

### What is excluded from fundings

- Prizes and awards that carry no cash component and provide no direct career support (unless they carry significant prestige and career benefit)
- Internal institutional grants available only to employees of one specific institution
- Crowd-funding campaigns or individual fundraising appeals
- Opportunities requiring paid membership where membership fees are prohibitive
- Consulting contracts, employment positions, and paid internships (these are jobs, not grants)
- Opportunities that are exclusively for citizens of a single country AND that country has its own well-known national database (to avoid duplicating national grant portals)

---

## Travel grants — inclusion criteria

A travel grant should be listed if it meets all of the following:

1. **Active or recurring.**
2. **Accessible to ECRs.**
3. **From a named, identifiable organization.**
4. **Has an official URL.**
5. **Covers genuine travel costs.** The grant must contribute to travel, accommodation, or conference registration. Nominal awards below EUR/USD 100 are not listed unless they are part of a broader programme.

### What is excluded from travel grants

- Conference waivers that cover registration only when the applicant is an invited speaker (this is not a competitive grant)
- Internal departmental travel funding
- Reimbursements that require the applicant to be already affiliated with the offering institution

---

## Resources — inclusion criteria

A resource should be listed if it meets all of the following:

1. **Freely accessible.** The resource is available at no cost, or has a meaningful free tier. Paid-only resources are listed only if they are widely used and the price is noted.

2. **Primarily aimed at researchers or ECRs.** General productivity tools (e.g., a generic note-taking app) are excluded unless specifically designed for or widely adopted by the research community.

3. **From a credible source.** University communication labs, professional societies, open science organizations, and established research-support platforms are credible sources. Anonymous blogs or personal sites are not.

4. **Stable and maintained.** The resource should be at a stable URL and show signs of active maintenance (updated within the last two years, or clearly a finished, durable reference).

5. **Relevant to ECR career development.** The resource must address at least one of: scientific writing, career planning, grant applications, research methods, open science, data management, peer review, science communication, networking, mental health and wellbeing in academia, or equivalent ECR-relevant topics.

### What is excluded from resources

- Individual research papers or preprints (these are primary literature, not resources)
- Software tools for conducting experiments (bioinformatics pipelines, statistical packages, lab instruments) — these belong in specialist databases
- Social media accounts, newsletters, or podcasts (unless they have a stable, searchable archive of structured content)
- Resources that require institutional login with no open access

---

## The review_status field

Every entry has a `review_status` field that controls visibility:

| Value | Meaning | Visible on site? |
|-------|---------|-----------------|
| `pending` | Submitted, awaiting maintainer review | No |
| `approved` | Reviewed and confirmed accurate | Yes |
| `rejected` | Does not meet inclusion criteria | No |

### How review works

1. Contributors submit new entries with `review_status: pending`.
2. A maintainer reviews the entry against this policy.
3. If approved: `review_status` is changed to `approved` and the PR is merged.
4. If rejected: the maintainer leaves a comment explaining why and closes the PR (or the issue).
5. If more information is needed: the maintainer leaves a comment and labels the PR `needs-info`.

Maintainers aim to review new entries within 7 days of submission.

---

## How featured entries are chosen

The `featured: true` flag marks entries for display on the homepage showcase section. Featured entries are chosen by maintainers to represent a diverse, high-quality sample of what ECRcentral contains.

Criteria for featuring an entry:
- The entry is `approved` and `active`
- It represents a well-funded, credible, established programme
- It covers a broad range of career levels or disciplines (not hyper-specific)
- It has a complete record (all major fields filled in, good description)
- There is reasonable geographic or disciplinary diversity across the featured set

To request that an entry be featured, leave a comment on the relevant PR or issue. Maintainers make the final decision.

Featured entries are not permanent — they are rotated periodically to keep the homepage fresh.

---

## How outdated entries are handled

The ECRcentral database is only as useful as it is accurate. Managing outdated content is an ongoing community effort.

### Marking entries as expired

When a funding opportunity closes permanently:
- Set `status: expired`
- The entry is hidden from default search results but remains in the database for reference
- If it is likely to reopen (e.g., annual programme temporarily on hold), use `status: archived` instead of `expired`

### Automated expiry

The build system checks `deadline_date` fields. When a deadline date is in the past by more than 90 days and the frequency is not `Rolling`, the build script flags the entry for review. It does not automatically change the status (to avoid false positives), but creates a warning in the build log.

### Community reporting

Anyone can report an outdated entry using the [outdated entry issue form](https://github.com/ecrcentral/ecrcentral.github.io/issues/new?template=outdated-entry.yml). Maintainers aim to act on these reports within 14 days.

### Bulk review

Maintainers conduct a periodic bulk review (at minimum annually) of all `active` entries to check for:
- Broken URLs
- Passed deadlines without a future cycle announced
- Changed eligibility criteria

---

## Moderation process

### Pull request moderation

All content changes go through pull requests. Maintainers:
- Check the content against this policy
- Run automated validation (CI will catch schema and reference errors)
- Review the description for accuracy and neutral language
- Merge, request changes, or reject with explanation

Maintainers are not required to independently verify every claim in a submission (that is the contributor's responsibility), but will check obvious issues and cross-reference the official URL.

### Issue moderation

Issue submissions (from the issue forms) are processed by maintainers who create YAML files from the information provided. If the information is insufficient to create a valid entry, the maintainer will ask follow-up questions on the issue.

### Spam and low-quality submissions

Submissions that appear to be self-promotion from organizations that do not meet inclusion criteria will be rejected. Repeated low-quality submissions from the same contributor may result in a contribution ban.

---

## Conflict of interest policy

Maintainers and contributors should disclose any affiliation with the organization offering a grant or resource they are submitting. Disclosure does not disqualify a submission — submitting your own organization's legitimate funding programme is fine — but it must be noted in the PR or issue.

Maintainers should not be the sole reviewer of submissions from their own organization. When possible, a second maintainer should review such submissions.

---

## How to appeal a rejection

If your submission was rejected and you believe it meets the inclusion criteria:

1. Leave a comment on the closed PR or issue explaining your case and citing the specific criteria you believe the entry meets.
2. A maintainer will review the appeal and either reinstate the submission or explain the rejection further.

Appeals are not guaranteed to succeed. The final decision rests with the maintainers.

If you believe a maintainer has applied this policy incorrectly or inconsistently, you can open a [GitHub Discussion](https://github.com/ecrcentral/ecrcentral.github.io/discussions) to raise the issue with the broader community.

---

## Versioning this policy

This editorial policy may change over time as the community's needs evolve. Significant changes will be announced in the repository's GitHub Discussions. The git history of this file (`docs/editorial-policy.md`) serves as a changelog.
