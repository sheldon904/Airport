# Florida Real Estate Compliance Guide

Airport tracks and automates compliance with Florida real estate regulations and federal requirements. This document details the statutory deadlines, disclosure requirements, and compliance logic built into the platform.

## Overview

Florida real estate transactions are governed by numerous state statutes and federal regulations. Missing a deadline or failing to provide required disclosures can result in:

- Contract rescission rights for buyers
- Fines and license discipline
- Transaction delays or cancellations
- Civil liability

Airport automates tracking of 15+ statutory requirements to ensure nothing slips through the cracks.

---

## Florida Statutory Deadlines

### Seller Disclosures

#### Seller's Property Disclosure (F.S. 689.25)
**Deadline:** Within 3 days of effective date

Florida law requires sellers of residential property to disclose known material facts about the property. While Florida does not mandate a specific disclosure form, the FAR (Florida Association of Realtors) form is widely used.

**What's Disclosed:**
- Structural issues
- Roof condition and age
- Plumbing and electrical systems
- Environmental hazards
- Neighborhood nuisances
- HOA/Condo information

**Airport Action:** Creates deadline 3 days from effective date, extracts disclosure items from uploaded forms.

---

#### Radon Gas Disclosure (F.S. 404.056)
**Deadline:** At contract signing (Day 0)

All Florida residential sales contracts must include the following statutory radon disclosure:

> "RADON GAS: Radon is a naturally occurring radioactive gas that, when it has accumulated in a building in sufficient quantities, may present health risks to persons who are exposed to it over time. Levels of radon that exceed federal and state guidelines have been found in buildings in Florida. Additional information regarding radon and radon testing may be obtained from your county health department."

**Airport Action:** Verifies radon disclosure is present in executed contract, flags if missing.

---

#### Property Tax Disclosure (F.S. 689.261)
**Deadline:** Prior to closing

Sellers must provide a statement regarding property tax implications:

> "PROPERTY TAX DISCLOSURE SUMMARY: The County property appraiser may reassess the property's value following a change of ownership, potentially resulting in higher property taxes."

**Airport Action:** Tracks disclosure status, alerts if not provided before closing.

---

#### Energy Efficiency Disclosure (F.S. 553.996)
**Deadline:** Prior to closing

Sellers must inform buyers about Florida's Building Energy-Efficiency Rating System and that energy ratings may be obtained.

**Airport Action:** Tracks disclosure completion status.

---

### Lead-Based Paint (Pre-1978 Properties)

#### Lead-Based Paint Disclosure (42 U.S.C. 4852d)
**Deadline:** Within 10 days for inspection period

For properties built before 1978, federal law requires:

1. **Disclosure Form:** Seller disclosure of known lead-based paint hazards
2. **Pamphlet:** EPA pamphlet "Protect Your Family From Lead in Your Home"
3. **Inspection Period:** Minimum 10-day period for buyer to conduct lead inspection (can be waived)
4. **Acknowledgment:** Signed acknowledgment of receipt

**Airport Action:**
- Only creates deadline when `year_built < 1978`
- Tracks 10-day inspection period
- Verifies all required documents are present
- Flags missing acknowledgments

---

### HOA Properties

#### HOA Disclosure (F.S. 720.401)
**Deadline:** Within 3 days of effective date

For properties in homeowner associations, sellers must provide:

1. Copy of most recent year-end financial information
2. Governing documents (Declaration, Bylaws, Rules)
3. Disclosure summary including:
   - Assessment amounts
   - Fee frequency
   - Special assessments
   - Any pending lawsuits
   - Reserve amounts

**Buyer Rights:**
- 3-day rescission period after receipt of all required documents

**Airport Action:**
- Only creates deadline when `is_hoa = true`
- Tracks document receipt and rescission period
- Alerts agents to missing required documents

---

### Condominium Properties

#### Condo Association Documents (F.S. 718.503)
**Deadline:** Within 3 days of effective date (seller to buyer)

For condominium purchases, extensive documentation is required:

**Required Documents:**
1. Declaration of Condominium
2. Articles of Incorporation
3. Bylaws
4. Current Rules and Regulations
5. Most recent year-end financial statement
6. Frequently Asked Questions and Answers sheet
7. Current year's budget
8. Governance form
9. Statement regarding developer rights (if applicable)

#### Condo Rescission Period (F.S. 718.503)
**Deadline:** 15 calendar days from receipt of condo documents

Buyers have an unconditional right to rescind within 15 days of receiving required condo documents. This cannot be waived.

**Airport Action:**
- Only creates deadlines when `is_condo = true`
- Tracks document receipt dates
- Calculates 15-day rescission period from last document received
- Prominently displays rescission deadline

---

### Title and Survey

#### Title Commitment (Standard Contract)
**Deadline:** Within 15 days of effective date

While not statutory, standard Florida contracts require title commitment delivery within a specified period (typically 15 days).

**What's Examined:**
- Current ownership
- Liens and encumbrances
- Easements and restrictions
- Title exceptions
- Insurance requirements

**Airport Action:** Tracks title commitment deadline and flags title exceptions for review.

---

### Closing Preparation

#### Walk-Through Inspection
**Deadline:** 1 day before closing (standard)

Standard practice allows buyer to inspect property prior to closing to verify:
- Condition unchanged since contract
- Repairs completed as agreed
- Property is vacant (if applicable)
- Included items present

**Airport Action:** Creates reminder 1 day before closing date.

---

## TRID Deadlines (Financed Purchases)

The TILA-RESPA Integrated Disclosure (TRID) rule applies to most residential mortgage loans.

### Loan Estimate (12 CFR 1026.19(e))
**Deadline:** 3 business days after loan application

Lenders must provide the Loan Estimate form within 3 business days of receiving a loan application. The estimate must include:

- Loan terms
- Projected payments
- Closing costs
- APR
- Total Interest Percentage (TIP)

**Business Day Definition (TRID):**
All days except Sundays and federal public holidays.

### Closing Disclosure (12 CFR 1026.19(f))
**Deadline:** 3 business days BEFORE closing

The Closing Disclosure must be received by the borrower at least 3 business days before consummation. Changes to certain terms may require a new 3-day waiting period.

**Triggers for New Waiting Period:**
- APR increases by more than 0.125%
- Loan product changes
- Prepayment penalty added

**Airport TRID Calculations:**

Airport implements precise TRID business day calculations:

```
TRID Business Days = All days except:
  - Sundays
  - New Year's Day (Jan 1)
  - MLK Day (3rd Monday in January)
  - Presidents Day (3rd Monday in February)
  - Memorial Day (Last Monday in May)
  - Juneteenth (June 19, since 2021)
  - Independence Day (July 4)
  - Labor Day (1st Monday in September)
  - Columbus Day (2nd Monday in October)
  - Veterans Day (November 11)
  - Thanksgiving (4th Thursday in November)
  - Christmas Day (December 25)
```

**Holiday Observance:**
- If holiday falls on Saturday, Friday is observed
- If holiday falls on Sunday, Monday is observed

**Airport Action:**
- Only creates TRID deadlines when `is_financed = true`
- Uses TRID-compliant business day calculator
- Accounts for all federal holidays including Juneteenth
- Handles holiday observance rules

---

## Standard Contingencies

While not statutory, Airport tracks standard contract contingencies:

### Inspection Period
**Default:** 15 days from effective date

Buyer's right to inspect property and negotiate repairs or terminate.

**Typical Options:**
- Accept property as-is
- Request repairs
- Request credit at closing
- Terminate contract

### Financing Contingency
**Default:** 30 days from effective date
**Condition:** Only for financed purchases

Buyer's protection if mortgage financing cannot be obtained.

**Requirements:**
- Good faith loan application
- Credit approval or denial
- Loan commitment by deadline

### Appraisal Contingency
**Default:** 30 days from effective date

Protection if property does not appraise at purchase price.

**Options:**
- Renegotiate price
- Buyer pays difference
- Terminate contract

---

## Document Checklist Categories

Airport organizes required documents into categories:

### Contract Documents
| Document | Deadline | Required |
|----------|----------|----------|
| Executed Purchase Contract | Day 0 | Yes |
| Earnest Money Receipt | 3 days | Yes |
| Addenda and Amendments | Varies | As needed |

### Disclosures
| Document | Deadline | Condition |
|----------|----------|-----------|
| Seller's Property Disclosure | 3 days | All |
| Radon Gas Disclosure | Day 0 | All |
| Lead-Based Paint | 10 days | Pre-1978 |
| HOA Disclosure | 3 days | HOA property |
| Condo Documents | 3 days | Condo |
| Property Tax Disclosure | Pre-closing | All |
| Energy Efficiency | Pre-closing | All |

### Financial Documents
| Document | Required | Condition |
|----------|----------|-----------|
| Pre-Approval Letter | Yes | Financed |
| Loan Estimate | Yes | Financed |
| Loan Commitment | Yes | Financed |
| Closing Disclosure | Yes | Financed |
| Proof of Funds | Yes | Cash |

### Inspection Documents
| Document | Required |
|----------|----------|
| Home Inspection Report | Optional |
| WDO (Termite) Inspection | Optional |
| Appraisal Report | Required (financed) |
| Survey | Optional |

### Title Documents
| Document | Deadline |
|----------|----------|
| Title Commitment | 15 days |
| Title Search | Pre-closing |
| Title Insurance Policy | At closing |

### Closing Documents
| Document | Deadline |
|----------|----------|
| Closing Disclosure | 3 business days before |
| Warranty Deed | At closing |
| Settlement Statement | At closing |

---

## Compliance Engine Logic

Airport's compliance engine applies rules based on transaction characteristics:

```
FOR each transaction:
  CREATE standard statutory deadlines

  IF year_built < 1978:
    CREATE lead paint disclosure deadline
    CREATE lead inspection period (10 days)

  IF is_hoa:
    CREATE HOA disclosure deadline
    CREATE HOA rescission period (3 days)

  IF is_condo:
    CREATE condo documents deadline
    CREATE condo rescission period (15 days)

  IF is_financed:
    CREATE TRID loan estimate deadline
    CREATE TRID closing disclosure deadline
    CREATE financing contingency
    CREATE appraisal contingency
```

---

## Audit Trail Requirements

For compliance purposes, Airport maintains a complete audit trail:

### Logged Actions
- Document uploads and modifications
- Deadline creation and updates
- Verification and corrections
- Status changes
- User actions and timestamps

### Retention
- All audit records retained for 5+ years
- Immutable log entries (SET NULL on deletion)
- Export capability for regulatory review

### Compliance Reports
- Transaction summary with all deadlines
- Document checklist with verification status
- Timeline of key events
- Risk assessment scoring

---

## Risk Assessment

Airport calculates a compliance risk score for each transaction:

### Risk Factors
| Factor | Weight |
|--------|--------|
| Overdue deadlines | High |
| Missing required documents | High |
| Unverified extractions | Medium |
| Approaching deadlines (≤3 days) | Medium |
| Low confidence extractions | Low |

### Risk Levels
- **Low (0-25):** On track, minor attention needed
- **Medium (26-50):** Action required, some deadlines approaching
- **High (51-75):** Urgent attention, overdue items
- **Critical (76-100):** Immediate action required

---

## Reference: Florida Statutes

| Statute | Topic |
|---------|-------|
| F.S. 475.25 | Real Estate License Law |
| F.S. 475.278 | Broker Relationships |
| F.S. 404.056 | Radon Gas Disclosure |
| F.S. 501.025 | Consumer Transactions |
| F.S. 553.996 | Energy Efficiency |
| F.S. 689.01 | Conveyances |
| F.S. 689.25 | Seller Disclosures |
| F.S. 689.261 | Property Tax Disclosure |
| F.S. 718.503 | Condominium Disclosures |
| F.S. 720.401 | HOA Disclosures |

## Reference: Federal Regulations

| Regulation | Topic |
|------------|-------|
| 42 U.S.C. 4852d | Lead-Based Paint |
| 12 CFR 1026.19 | TRID (Reg Z) |
| 12 CFR 1024 | RESPA |

---

## Disclaimer

This document is for informational purposes only and does not constitute legal advice. Regulations change, and specific situations may have unique requirements. Always consult with a licensed real estate attorney or your broker for compliance questions.

Airport is designed to assist with compliance tracking but does not guarantee regulatory compliance. Users are responsible for verifying all deadlines and requirements for their specific transactions.
