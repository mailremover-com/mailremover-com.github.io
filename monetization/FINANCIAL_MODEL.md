# SignSimple.io Financial Model

## Executive Summary

**Goal:** Generate $11,800 in Week 1 to fund 5+ years of operations

| Metric | Value |
|--------|-------|
| LTD Price | $59 |
| LTD Spots | 200 |
| Total LTD Revenue | $11,800 |
| Cost per LTD User/Year | ~$10-15 |
| Runway from LTD Revenue | 5-7 years |

---

## PART 1: COST ANALYSIS

### Infrastructure Costs (Per Month)

| Service | Provider | Monthly Cost | Annual Cost |
|---------|----------|--------------|-------------|
| Hosting | Vercel/Railway/Fly.io | $20 | $240 |
| Database | PlanetScale/Supabase | $25 | $300 |
| File Storage | S3/R2/Backblaze | $10 | $120 |
| Email Service | SendGrid/Resend | $20 | $240 |
| Monitoring | Sentry (free tier) | $0 | $0 |
| Domain/SSL | Cloudflare | $15 | $180 |
| **Subtotal** | | **$90** | **$1,080** |

### Per-User Variable Costs

| Cost Item | Per Document | Per Signature | Notes |
|-----------|--------------|---------------|-------|
| Email (transactional) | $0.001 | $0.001 | ~$0.002/doc sent |
| PDF Processing | $0.002 | - | Rendering/processing |
| Storage | $0.001 | - | ~500KB avg doc |
| Bandwidth | $0.0005 | $0.0005 | Downloads/views |
| **Total per doc** | **~$0.005** | | |

### Cost Per LTD User Per Year

**Assumptions:**
- Average LTD user sends 30 docs/month = 360 docs/year
- Average 2 signatures per doc = 720 signatures/year
- Average storage: 200MB/year

| Cost Component | Calculation | Annual Cost |
|----------------|-------------|-------------|
| Document processing | 360 x $0.005 | $1.80 |
| Email notifications | 1,000 emails x $0.001 | $1.00 |
| Storage (200MB) | 0.2GB x $0.023/GB/mo x 12 | $0.06 |
| Bandwidth | Est. 2GB/year | $0.10 |
| **Variable cost/user** | | **$2.96** |

**Add share of fixed costs:**
| Fixed costs | $1,080/year |
| If 200 LTD users | $5.40/user |

**Total cost per LTD user per year: ~$8.36**

Round up for margin: **$10-15/user/year**

---

## PART 2: BREAK-EVEN ANALYSIS

### LTD Break-Even Timeline

| Year | LTD Revenue | Cumulative Revenue | Cumulative Costs | Net Position |
|------|-------------|--------------------|--------------------|--------------|
| 0 | $11,800 | $11,800 | $0 | +$11,800 |
| 1 | $0 | $11,800 | $3,080 | +$8,720 |
| 2 | $0 | $11,800 | $6,160 | +$5,640 |
| 3 | $0 | $11,800 | $9,240 | +$2,560 |
| 4 | $0 | $11,800 | $12,320 | -$520 |
| 5 | $0 | $11,800 | $15,400 | -$3,600 |

**Break-even on LTD alone: ~3.8 years**

### With Additional Revenue Streams

| Year | LTD | Subscriptions | Upsells | Total Revenue | Costs | Net |
|------|-----|---------------|---------|---------------|-------|-----|
| 1 | $11,800 | $3,600 | $3,000 | $18,400 | $3,080 | +$15,320 |
| 2 | $0 | $7,200 | $6,000 | $13,200 | $4,000 | +$9,200 |
| 3 | $0 | $12,000 | $8,000 | $20,000 | $5,000 | +$15,000 |
| 4 | $0 | $18,000 | $10,000 | $28,000 | $6,000 | +$22,000 |
| 5 | $0 | $24,000 | $12,000 | $36,000 | $7,000 | +$29,000 |

**Cumulative profit after 5 years: $90,520**

---

## PART 3: WHY $59 x 200 = 5+ YEARS OF RUNWAY

### The Math

**Total LTD Revenue: $11,800**

**Annual Operating Costs:**
```
Fixed costs: $1,080
Variable costs (200 users x $3): $600
Buffer for unexpected: $320
---
Total: $2,000/year
```

**Runway Calculation:**
```
$11,800 / $2,000 = 5.9 years
```

### Margin of Safety

**Conservative scenario:**
- Costs 50% higher than estimated: $3,000/year
- Runway: $11,800 / $3,000 = 3.9 years

**Aggressive scenario:**
- Costs as estimated: $2,000/year
- Runway: 5.9 years

**With subscription revenue added:**
- Even $200/month MRR extends runway indefinitely
- $200/month = just 10-20 monthly subscribers

---

## PART 4: REVENUE PROJECTIONS

### Year 1 Revenue Model

| Source | Q1 | Q2 | Q3 | Q4 | Total |
|--------|-----|-----|-----|-----|-------|
| LTD Sales | $11,800 | $0 | $0 | $0 | $11,800 |
| Starter ($9/mo) | $180 | $360 | $540 | $720 | $1,800 |
| Pro ($19/mo) | $380 | $760 | $1,140 | $1,520 | $3,800 |
| LTD Upsells | $0 | $500 | $1,000 | $1,500 | $3,000 |
| **Total** | **$12,360** | **$1,620** | **$2,680** | **$3,740** | **$20,400** |

**Year 1 projections:**
- Revenue: $20,400
- Costs: $3,080
- Profit: $17,320

### 5-Year Revenue Projection

| Year | LTD | Subscriptions | Upsells | Total |
|------|-----|---------------|---------|-------|
| 1 | $11,800 | $5,600 | $3,000 | $20,400 |
| 2 | $0 | $14,400 | $6,000 | $20,400 |
| 3 | $0 | $28,800 | $10,000 | $38,800 |
| 4 | $0 | $48,000 | $15,000 | $63,000 |
| 5 | $0 | $72,000 | $20,000 | $92,000 |

**5-Year cumulative revenue: $214,600**

---

## PART 5: SUBSCRIBER GROWTH MODEL

### Conversion Funnel Assumptions

| Stage | Conversion Rate |
|-------|-----------------|
| Visitor to Free signup | 5% |
| Free to Paid (Starter) | 3% |
| Free to Paid (Pro) | 2% |
| Starter to Pro upgrade | 20% (over lifetime) |

### Monthly Subscriber Growth

| Month | Free Users | Starter | Pro | MRR |
|-------|------------|---------|-----|-----|
| 1 | 100 | 5 | 2 | $83 |
| 3 | 400 | 15 | 8 | $287 |
| 6 | 1,000 | 40 | 20 | $740 |
| 12 | 2,500 | 100 | 50 | $1,850 |
| 24 | 6,000 | 250 | 125 | $4,625 |

**Month 24 ARR: $55,500**

---

## PART 6: SENSITIVITY ANALYSIS

### What if LTD users cost more?

| Cost/User/Year | Years of Runway |
|----------------|-----------------|
| $10 | 5.9 years |
| $20 | 2.95 years |
| $30 | 1.97 years |
| $50 | 1.18 years |

**Mitigation:** Soft caps on LTD usage (100 docs/mo) prevent runaway costs.

### What if fewer LTDs sell?

| LTDs Sold | Revenue | Runway (alone) |
|-----------|---------|----------------|
| 200 | $11,800 | 5.9 years |
| 150 | $8,850 | 4.4 years |
| 100 | $5,900 | 2.95 years |
| 50 | $2,950 | 1.5 years |

**Mitigation:** Even 100 LTDs + small subscription base = sustainable.

### What if churn is high?

| Monthly Churn | Year 1 Impact |
|---------------|---------------|
| 5% | -$336 revenue |
| 10% | -$672 revenue |
| 15% | -$1,008 revenue |

**Mitigation:** Focus on onboarding and activation to reduce early churn.

---

## PART 7: COMPETITIVE PRICING COMPARISON

| Product | Solo Plan | Team Plan | Per-Signature |
|---------|-----------|-----------|---------------|
| DocuSign | $15/mo | $45/mo | $0.50-$2.00 |
| HelloSign | $20/mo | $40/mo | Unlimited |
| SignNow | $8/mo | $15/mo | Unlimited |
| PandaDoc | $35/mo | $65/mo | Unlimited |
| **SignSimple.io** | **$9/mo** | **$19/mo** | **Unlimited** |
| **SignSimple LTD** | **$59 once** | - | **Unlimited** |

### Value Proposition Math

**For LTD buyer paying $59 once vs $15/mo competitor:**
```
Competitor cost Year 1: $180
Competitor cost Year 2: $360
Competitor cost Year 3: $540
Competitor cost Year 5: $900

SignSimple LTD cost forever: $59

Savings Year 1: $121
Savings Year 5: $841
Savings Year 10: $1,741
```

---

## PART 8: WORST CASE SCENARIOS

### Scenario 1: No subscriptions ever
- Only LTD revenue: $11,800
- Annual costs: $2,000
- Runway: 5.9 years
- **Outcome:** Still viable for years, time to pivot

### Scenario 2: High LTD abuse
- 20% of LTD users exceed limits
- Extra costs: $1,500/year
- New runway: 3.4 years
- **Mitigation:** Enforce fair use policy, charge for overages

### Scenario 3: Major cost increases
- Cloud costs double
- New annual costs: $4,000
- New runway: 2.95 years
- **Mitigation:** Optimize infrastructure, move to cheaper providers

### Scenario 4: Legal/compliance issues
- Potential cost: $5,000-$20,000
- **Mitigation:** Get proper e-signature compliance from day 1

---

## PART 9: FINANCIAL DASHBOARD METRICS

### KPIs to Track Weekly

| Metric | Target | Formula |
|--------|--------|---------|
| MRR | Growing 15%/mo | Sum of all subscription revenue |
| LTV | >$100 | Avg revenue per customer lifetime |
| CAC | <$20 | Marketing spend / new customers |
| LTV:CAC | >5:1 | LTV / CAC |
| Churn | <5% | Lost customers / total customers |
| NPS | >50 | Promoters - Detractors |

### Monthly Financial Review

```
Revenue Breakdown:
- LTD: $[X] (one-time)
- Starter: $[X] (recurring)
- Pro: $[X] (recurring)
- Upsells: $[X]
- Total: $[X]

Costs:
- Infrastructure: $[X]
- Variable: $[X]
- Marketing: $[X]
- Total: $[X]

Net: $[X]
Runway: [X] months
```

---

## SUMMARY

### Key Takeaways

1. **$59 x 200 = $11,800** covers infrastructure for 5+ years
2. **Cost per LTD user: ~$10-15/year** is sustainable
3. **Break-even on LTD alone: 3.8 years** (conservative)
4. **With subscriptions: Profitable from Month 6**
5. **5-year projected revenue: $214,600**

### Why This Model Works

1. **Low infrastructure costs** - Modern cloud services are cheap
2. **High margin** - 90%+ gross margin on subscriptions
3. **LTD provides runway** - Time to build without pressure
4. **Multiple revenue streams** - LTD + subscriptions + upsells
5. **Scalable** - Costs grow slower than revenue

### Action Items

- [ ] Set up financial tracking dashboard
- [ ] Monitor per-user costs monthly
- [ ] Review pricing after 6 months
- [ ] Optimize infrastructure for cost
- [ ] Build upsell features by Month 3

---

*This model assumes bootstrapped operation with no external funding. Revenue projections are conservative estimates based on industry benchmarks.*
