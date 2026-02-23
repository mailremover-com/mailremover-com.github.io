# Post-LTD Transition & Upsell Strategy

## Overview

This document covers:
1. When and how to close the LTD
2. Transitioning to regular pricing
3. Upsell opportunities for LTD users
4. Long-term LTD user management

---

## PART 1: CLOSING THE LTD

### When to Close

**Option A: Spots-Based (Recommended)**
- Close when 200 spots are sold
- Creates genuine scarcity
- Easy to track and communicate
- No ambiguity

**Option B: Time-Based**
- Close after 7 days regardless of spots sold
- Creates deadline urgency
- Risk: May close with spots remaining (looks bad)

**Option C: Hybrid (Best Practice)**
- Close when 200 spots sold OR 14 days pass
- Whichever comes first
- Allows extension if momentum exists
- Maximum flexibility

### Recommended Approach
```
Primary trigger: 200 spots sold
Backup trigger: 14 days from launch
Extend if: Selling 10+ spots/day on day 7
```

### Closing Checklist

**Technical:**
- [ ] Disable LTD purchase option in Stripe
- [ ] Update LTD page to "Sold Out" version
- [ ] Redirect /ltd to /pricing (or keep as sold-out page)
- [ ] Update spots counter to show 0
- [ ] Verify no pending LTD purchases can complete

**Communication:**
- [ ] Send "Sold Out" email to waitlist
- [ ] Post on Twitter/social channels
- [ ] Update any running ads
- [ ] Respond to DMs asking about LTD

### "Sold Out" Page Content

```html
<!-- Replace LTD page content with: -->
<div class="sold-out-container">
    <h1>Founder's Lifetime Deal - SOLD OUT</h1>
    <p>All 200 spots have been claimed by our founding members.</p>

    <div class="regular-pricing">
        <h2>Regular Pricing Available:</h2>
        <ul>
            <li>Free: $0/month (3 docs/month)</li>
            <li>Starter: $9/month (25 docs/month)</li>
            <li>Pro: $19/month (unlimited)</li>
        </ul>
        <a href="/pricing" class="cta">View Pricing</a>
    </div>

    <div class="waitlist-future">
        <h3>Want to know about future deals?</h3>
        <p>Join our list for occasional special offers:</p>
        <form action="/future-deals-waitlist" method="POST">
            <input type="email" name="email" placeholder="your@email.com">
            <button type="submit">Notify Me</button>
        </form>
    </div>
</div>
```

---

## PART 2: REGULAR PRICING STRUCTURE

### Post-LTD Pricing

| Plan | Monthly | Yearly (17% off) | Features |
|------|---------|------------------|----------|
| Free | $0 | $0 | 3 docs/mo, basic templates |
| Starter | $9 | $90 | 25 docs/mo, all templates, audit trail |
| Pro | $19 | $190 | Unlimited, API, custom branding, priority support |

### Why This Structure Works

**Free Tier:**
- Low barrier to entry
- Users experience value before paying
- Converts to paid when they hit limit

**Starter ($9):**
- Affordable for freelancers
- Enough volume for most individual users
- Clear upgrade path when they grow

**Pro ($19):**
- Still cheaper than DocuSign ($25+)
- Unlimited removes mental barrier
- API access for integrations

### Pricing Page After LTD

The pricing page should:
1. Remove LTD banner/callout
2. Feature Pro as "Most Popular"
3. Show annual savings prominently
4. Include comparison to competitors

---

## PART 3: UPSELL OPPORTUNITIES FOR LTD USERS

### Philosophy
LTD users paid for lifetime access to core features. Additional revenue comes from:
- Add-ons that enhance their experience
- Team/collaboration features
- Enterprise-grade features

### Upsell #1: Team Seats
**What:** Add team members to LTD account
**Price:** $5/user/month (50% off regular $10/user)
**Target:** LTD users who grow into teams

Email trigger (3 months post-purchase):
```
Subject: Add your team to SignSimple.io

Hey [Name],

I noticed you've sent 127 documents through SignSimple.io - nice!

If you're working with a team, you can add team members to your account.

As a Founder member, you get 50% off team seats:
- $5/user/month instead of $10
- Each user gets their own login
- Shared templates and history

Add your first team member: [link]

Best,
SignSimple.io
```

### Upsell #2: Additional Storage
**What:** Extra storage beyond 10GB limit
**Price:** $5/10GB/month
**Target:** High-volume users

Trigger: When user hits 80% of storage limit

### Upsell #3: API Access
**What:** Programmatic access for integrations
**Price:** $29/month or $19/month for LTD users
**Target:** Technical users, developers, agencies

Email trigger (6 months post-purchase):
```
Subject: Integrate SignSimple.io with your tools

Hey [Name],

You've been using SignSimple.io for 6 months now. Thank you!

I wanted to let you know about our API:

- Connect to Zapier, Make, or custom apps
- Automate document sending from your CRM
- Programmatically track signature status
- Webhook notifications when documents are signed

As a Founder member: $19/month (regularly $29)

Learn more: [link]

Best,
SignSimple.io
```

### Upsell #4: Priority Support SLA
**What:** Guaranteed response times
**Price:** $49/month
**Target:** Business-critical users

Features:
- 4-hour response time (vs 24-48 hours)
- Phone support access
- Dedicated account manager
- Onboarding assistance

### Upsell #5: White-Label/Branding Remove
**What:** Remove "Powered by SignSimple.io" branding
**Price:** $29/month
**Target:** Agencies, professional services

### Upsell Revenue Projections

| Upsell | Est. Adoption | Monthly Revenue |
|--------|---------------|-----------------|
| Team Seats (avg 2 users) | 20% of 200 = 40 | $400/mo |
| Extra Storage | 10% of 200 = 20 | $100/mo |
| API Access | 5% of 200 = 10 | $190/mo |
| Priority Support | 2% of 200 = 4 | $196/mo |
| White-Label | 3% of 200 = 6 | $174/mo |
| **Total** | | **$1,060/mo** |

Year 1 upsell revenue potential: $12,720

---

## PART 4: LONG-TERM LTD USER MANAGEMENT

### LTD User Tiers

After 12 months, segment LTD users:

**Power Users (Top 20%)**
- Send 50+ docs/month
- Most likely to upsell
- Invite to beta features
- Ask for testimonials

**Regular Users (Middle 60%)**
- Send 5-49 docs/month
- Healthy usage
- Occasional feature updates
- Annual check-in email

**Dormant Users (Bottom 20%)**
- Less than 5 docs/month
- Re-engagement campaigns
- Ask why they're not using it
- Offer help/training

### Annual LTD User Communication

**Month 12 - Anniversary Email:**
```
Subject: Happy 1-year anniversary, Founder Member!

Hey [Name],

One year ago today, you joined SignSimple.io as a Founder member.

Since then:
- You've sent [X] documents
- [Y] signatures collected
- [Z] hours saved (estimated)

Thank you for believing in us early. Here's what's new since you joined:
[List of new features added this year]

What's coming:
[Preview of roadmap items]

We're building this for you. Any features you'd love to see? Just reply.

Cheers,
SignSimple.io
```

### Handling LTD Abuse

**Signs of Abuse:**
- API scraping without paying for API
- Sharing account credentials
- Reselling access
- Automated usage far exceeding human patterns

**Response Protocol:**
1. First notice: Friendly email explaining limits
2. Second notice: Warning with specific violation
3. Third notice: Account restriction pending review
4. Final: Account suspension (offer prorated refund if egregious)

**Prevention:**
- Rate limiting on all endpoints
- Session tracking
- Clear ToS with enforcement language
- Monthly usage reports for internal review

### Future LTD Considerations

**If You Pivot the Product:**
Options:
1. Maintain core e-signature for LTD users forever
2. Offer equivalent value in new product
3. Prorated refund option

**If You Get Acquired:**
- LTD obligations transfer to acquirer
- Include in acquisition terms
- Communicate clearly to LTD users

**If You Shut Down:**
- 12 months notice
- Full data export
- Help migrating to alternatives
- Consider partial refunds if shutdown is early

---

## PART 5: FUTURE DEAL OPPORTUNITIES

### Anniversary Sale (Year 2)
After proving sustainability, consider:
- "Extended Founder's" deal at $99
- For waitlist members who missed first LTD
- Limited to 100 spots
- Slightly reduced limits (50 docs/mo vs 100)

### Black Friday / Special Occasions
- 40% off annual plans
- NOT lifetime deals (preserve LTD value)
- Short window (3-5 days)

### Referral Program
For LTD users:
- Get $10 credit per referral
- Stack credits for upsells (team seats, API)
- Referral gets 20% off first month

---

## SUMMARY

### Transition Checklist
- [ ] Close LTD at 200 spots or 14 days
- [ ] Update all pages to reflect sold-out status
- [ ] Launch regular pricing as primary
- [ ] Queue upsell emails for LTD users (3mo, 6mo, 12mo)
- [ ] Set up usage monitoring for abuse prevention
- [ ] Create anniversary email sequence

### Revenue Expectations

| Source | Year 1 |
|--------|--------|
| LTD Sales (200 x $59) | $11,800 |
| Monthly Subscriptions (est. 50 users avg) | $5,700 |
| LTD Upsells | $6,000 |
| **Total Year 1** | **$23,500** |

This model provides:
- Immediate cash from LTD
- Growing MRR from subscriptions
- Ongoing revenue from LTD upsells
- 5+ years of runway from LTD alone

---

*Remember: LTD users are your biggest advocates. Treat them well.*
