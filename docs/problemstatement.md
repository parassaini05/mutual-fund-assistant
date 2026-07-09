# Problem Statement: Mutual Fund FAQ Assistant (Facts-Only Q&A)

## Overview

The objective of this project is to build a **facts-only FAQ assistant** for mutual fund schemes, using **Groww** as the reference product context. The assistant will answer objective, verifiable queries related to mutual funds by retrieving information exclusively from official public sources, such as AMC (Asset Management Company) websites, AMFI, and SEBI.

The system must strictly avoid providing investment advice, opinions, or recommendations. Every response must include a single, clear source link and adhere to defined constraints around clarity, accuracy, and compliance.

---

## Objective

Design and implement a lightweight **Retrieval-Augmented Generation (RAG)**-based assistant that:

- Answers factual queries about mutual fund schemes
- Uses a curated corpus of official documents
- Provides concise, source-backed responses

---

## Target Users

- Retail investors comparing mutual fund schemes
- Customer support and content teams handling repetitive mutual fund queries

---

## Scope of Work

### 1. Corpus Definition

**Selected Mutual Fund Schemes (5 schemes across multiple AMCs):**

| # | Scheme Name | AMC | Category | Groww Link |
|---|-------------|-----|----------|-----------|
| 1 | ICICI Prudential Large Cap Fund — Direct Growth | ICICI Prudential | Large Cap | [View on Groww](https://groww.in/mutual-funds/icici-prudential-large-cap-fund-direct-growth) |
| 2 | Kotak Emerging Equity Scheme — Direct Growth | Kotak Mahindra | Mid Cap | [View on Groww](https://groww.in/mutual-funds/kotak-emerging-equity-scheme-direct-growth) |
| 3 | HDFC Small Cap Fund — Direct Growth | HDFC | Small Cap | [View on Groww](https://groww.in/mutual-funds/hdfc-small-cap-fund-direct-growth) |
| 4 | HSBC Midcap Fund — Direct Growth | HSBC | Mid Cap | [View on Groww](https://groww.in/mutual-funds/hsbc-midcap-fund-direct-growth) |
| 5 | Bajaj Finserv Flexi Cap Fund — Direct Growth | Bajaj Finserv | Flexi Cap | [View on Groww](https://groww.in/mutual-funds/bajaj-finserv-flexi-cap-fund-direct-growth) |

**Primary Source URLs (Groww — confirmed):**

| # | URL |
|---|-----|
| 1 | https://groww.in/mutual-funds/icici-prudential-large-cap-fund-direct-growth |
| 2 | https://groww.in/mutual-funds/kotak-emerging-equity-scheme-direct-growth |
| 3 | https://groww.in/mutual-funds/hdfc-small-cap-fund-direct-growth |
| 4 | https://groww.in/mutual-funds/hsbc-midcap-fund-direct-growth |
| 5 | https://groww.in/mutual-funds/bajaj-finserv-flexi-cap-fund-direct-growth |

**Additional official sources to supplement the corpus:**

  - Scheme factsheets (from respective AMC websites)
  - KIM (Key Information Memorandum)
  - SID (Scheme Information Document)
  - AMC FAQ/help pages
  - AMFI/SEBI guidance pages
  - Statement and tax document download guides

### 2. FAQ Assistant Requirements

The assistant must:

- **Answer facts-only queries**, such as:
  - Expense ratio of a scheme
  - Exit load details
  - Minimum SIP amount
  - ELSS lock-in period
  - Riskometer classification
  - Benchmark index
  - Process to download statements or capital gains reports

- **Ensure:**
  - Each response is limited to a maximum of **3 sentences**
  - Each response includes **exactly one citation link**
  - Each response includes a footer:
    > *"Last updated from sources: \<date\>"*

### 3. Refusal Handling

The assistant must **refuse** non-factual or advisory queries, such as:

- *"Should I invest in this fund?"*
- *"Which fund is better?"*

Refusal responses should:

- Be polite and clearly worded
- Reinforce the facts-only limitation
- Provide a relevant educational link (e.g., AMFI or SEBI resource)

### 4. User Interface (Minimal)

The solution should include a simple interface with:

- A welcome message
- Three example questions
- A visible disclaimer:
  > *"Facts-only. No investment advice."*

---

## Constraints

### Data and Sources

- Use **only official public sources** (AMC, AMFI, SEBI)
- Do not use third-party blogs or aggregator websites

### Privacy and Security

- **Do not collect, store, or process:**
  - PAN or Aadhaar numbers
  - Account numbers
  - OTPs
  - Email addresses or phone numbers

### Content Restrictions

- No investment advice or recommendations
- No performance comparisons or return calculations
- For performance-related queries, provide a link to the **official factsheet only**

### Transparency

- Responses must be **short, factual, and verifiable**
- Every answer must include a **source link** and **last updated date**

---

## Expected Deliverables

### 1. README Document

- Setup instructions
  - Selected AMCs and schemes (5 funds across ICICI Prudential, Kotak, HDFC, HSBC, Bajaj Finserv)
- Architecture overview (RAG approach)
- Known limitations

### 2. Disclaimer Snippet

> *"Facts-only. No investment advice."*

---

## Success Criteria

| # | Criterion |
|---|-----------|
| 1 | Accurate retrieval of factual mutual fund information |
| 2 | Strict adherence to facts-only responses |
| 3 | Consistent inclusion of valid source citations |
| 4 | Proper refusal of advisory queries |
| 5 | Clean, minimal, and user-friendly interface |

---

## Summary

The goal is to build a **trustworthy, transparent, and compliant** mutual fund FAQ assistant that prioritizes **accuracy over intelligence**. The system should ensure that users receive only verified, source-backed financial information, without any advisory bias or speculative content.
