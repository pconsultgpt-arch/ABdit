# ABdit

This repository contains the `AbDit.pptx` presentation, which shows a schematic
view of a system designed to convince people to use and install devices that
help reduce water consumption and cost — and a working **prototype web
application** that implements the Abdit platform end-to-end.

## Prototype

A FastAPI + SQLite + Jinja2 server-rendered application that walks the full
seven-step Abdit workflow with rich seeded data.

### What's implemented

- **Five role-specific portals**: subscriber, specialist, water company,
  equipment provider, Abdit operator (admin).
- **Consumption analytics engine**: per-subscriber z-score against historical
  baseline + peer comparison against similar households (household size,
  garden), classifying anomalies as low / medium / high severity.
- **Notifications**: anomalies generate alerts in the subscriber's inbox with
  a one-click "Request inspection" action.
- **Inspection workflow** (the seven steps from the proposal): request →
  specialist claim → on-site report → pre-invoice (proposal) with marketplace
  items → subscriber accept/decline → installation → verified savings feedback
  into the knowledge base.
- **Equipment marketplace**: providers manage product catalogs (CRUD); products
  appear in specialist proposals and the subscriber-facing marketplace.
- **Knowledge base & training programs**: curated water-saving practices,
  case-study counts, and partner certification programs.
- **Water-company tooling**: aggregate consumption charts, subscriber roster,
  upload-reading form (simulating utility-system import), one-click
  re-run-analytics.
- **Operator dashboard**: cross-platform KPIs, inspection-pipeline counts,
  verified savings rolling up from completed installations.
- **Auth**: session-based login with role-based access control.

### Run it

**macOS / Linux**

```bash
./run.sh
```

**Windows** (cmd or PowerShell)

```bat
run.bat
```

Either script creates a virtualenv, installs deps, seeds a fresh SQLite
database with demo data, and starts the server on `http://localhost:8000`.
All demo accounts share the password `password`.

Requires Python 3.11+ on `PATH` (the Windows script tries `py -3` first, then
`python`).

| Email | Role | What you'll see |
| --- | --- | --- |
| `amal@example.com` | Subscriber | Open proposal awaiting acceptance |
| `nadia@example.com` | Subscriber | Verified installation with 23.5% savings |
| `samir@example.com` | Subscriber | New high-consumption notification |
| `specialist1@abdit.io` | Specialist | Active inspection in progress |
| `ops@bluecity-water.com` | Water company | 8 subscribers, 18 months history |
| `aquasmart@abdit.io` | Provider | 2 active products, marketplace stats |
| `admin@abdit.io` | Abdit operator | Cross-platform dashboard |

### Demo walkthrough

1. **Subscriber `samir@example.com`** → dashboard shows a high-severity alert.
   Click "Request inspection".
2. **Specialist `specialist1@abdit.io`** → claim the unassigned request, fill
   in the report form (plumbing/irrigation/leakage findings, estimated
   savings), then build a proposal by ticking products from the marketplace
   and clicking "Send proposal".
3. **Back to `samir@example.com`** → open the inspection, review the report
   with projected yearly savings, accept the proposal.
4. **Specialist** → mark the installation complete with verified savings %.
5. **`admin@abdit.io`** → operator dashboard now shows the new completed
   installation rolled into the average-verified-savings KPI.

### Project layout

```
app/
├── main.py            # FastAPI app + auth + login flow
├── database.py        # SQLAlchemy engine/session
├── models.py          # ORM models for every entity in the proposal
├── auth.py            # Password hashing + role-based dependencies
├── analytics.py       # Anomaly detection + savings estimator
├── seed.py            # Idempotent demo-data seeder
├── routers/
│   ├── subscriber.py
│   ├── specialist.py
│   ├── water_company.py
│   ├── provider.py
│   └── admin.py
├── templates/         # Jinja2 templates per role
└── static/style.css
```

### Limitations (this is a prototype)

- Single-process SQLite, single demo water company, no real metering integration.
- Anomaly detection is statistical (z-score + peer ratio); no ML model is
  trained.
- No email/SMS — notifications are in-app only.
- No payment processing for proposals/installations.
- Session secret and demo passwords are hard-coded for ease of local demo.

---

## Proposal: Abdit System for Intelligent Water Conservation

### 1. Introduction

Water scarcity and increasing water costs are major challenges in many regions.
Traditional water management systems mainly rely on periodic meter readings and
billing, without providing actionable insights to help subscribers reduce
consumption.

This proposal introduces **Abdit**, an intelligent platform that analyzes water
consumption patterns and connects water subscribers with specialists, equipment
providers, and training institutions to help reduce water usage through
water-saving technologies and practices.

Abdit acts as a digital intermediary platform, similar to how ride-sharing
platforms connect drivers and passengers. In this ecosystem, Abdit connects
water companies, subscribers, water-saving specialists, equipment providers,
and educational institutions.

### 2. Current System (Traditional Model)

In the traditional water service model:

- The water company reads the meter periodically.
- A bill is issued based on total water consumption.
- The subscriber pays the bill.

**Limitations**

- No analysis of consumption patterns.
- Subscribers receive no guidance on reducing water use.
- Potential water waste remains undetected.
- Water companies have limited tools for demand management.

### 3. Proposed System: Abdit

Abdit introduces an intelligent consumption analysis and service coordination
platform.

The system analyzes subscriber consumption using:

- Historical billing data
- Household characteristics
- Seasonal consumption patterns
- Local climate conditions
- Knowledge base of water-saving practices
- Data gathered from specialists and previous projects

Based on this analysis, Abdit identifies high-consumption subscribers and
offers them personalized water-saving recommendations.

### 4. How the Abdit System Works

#### Step 1 — Data Collection

The water company provides Abdit with:

- Subscriber meter readings
- Billing history
- Location data
- Consumption trends

This data feeds the Abdit analysis engine.

#### Step 2 — Consumption Analysis

Abdit analyzes consumption using:

- Statistical models
- Machine learning
- A growing knowledge base of water-saving cases

The system identifies subscribers with unusually high or inefficient water
consumption.

#### Step 3 — Subscriber Notification

When a high-consumption pattern is detected, the subscriber receives a
notification suggesting:

- A water efficiency assessment
- A visit from a certified water-saving specialist

Participation is voluntary.

#### Step 4 — Specialist Inspection

If the subscriber agrees:

- A trained specialist visits the location.
- The specialist evaluates:
  - Plumbing systems
  - Irrigation systems
  - Household water usage
  - Potential leakages
  - Water-saving opportunities

#### Step 5 — Recommendations and Pre-Invoice

The specialist prepares:

- A technical report
- Suggested water-saving devices
- Estimated water savings
- A pre-invoice with installation options

The subscriber can choose among several options.

#### Step 6 — Equipment Installation

If the subscriber accepts a proposal:

- Equipment providers supply devices such as:
  - Smart irrigation controllers
  - Efficient faucets and showerheads
  - Leak detection systems
  - Water recycling systems
  - Smart meters

Installation is performed by certified specialists.

#### Step 7 — Knowledge Base Improvement

All projects feed data back into the Abdit system:

- Actual water savings
- Equipment performance
- Environmental conditions
- Cost effectiveness

This improves the knowledge base and analysis accuracy over time.

### 5. Key Stakeholders

#### 1. Water Company

**Responsibilities:**

- Provide consumption data
- Issue bills
- Collaborate with Abdit

**Benefits:**

- Reduced water demand
- Improved resource management
- Better customer engagement

#### 2. Subscribers

**Benefits:**

- Reduced water bills
- Professional efficiency assessment
- Access to modern water-saving technologies

#### 3. Water-Saving Specialists

**Roles:**

- Perform site inspections
- Recommend solutions
- Install equipment

They may be certified through approved training programs.

#### 4. Equipment Providers

Companies supplying:

- Water-saving devices
- Smart monitoring tools
- Leak detection technologies

They gain access to a targeted market through Abdit.

#### 5. Educational Institutions

Training centers can:

- Develop certification programs
- Train water efficiency specialists
- Provide research and best practices

### 6. Role of Abdit Platform

Abdit acts as the central coordination platform that:

- Analyzes water consumption
- Connects subscribers with specialists
- Links equipment providers with demand
- Maintains a knowledge base
- Facilitates project management

In essence, it functions as a marketplace and decision-support system for
water efficiency.

### 7. Key Components of the System

#### 1. Data Analytics Engine

Analyzes consumption patterns and detects anomalies.

#### 2. Knowledge Base

Stores:

- Water-saving techniques
- Equipment performance
- Case studies
- Regional best practices

#### 3. Subscriber Platform

Interface for subscribers to:

- View their consumption analysis
- Request inspections
- Review recommendations
- Accept proposals

#### 4. Specialist Platform

Used by specialists to:

- Receive service requests
- Submit reports
- Upload recommendations
- Track installations

#### 5. Provider Marketplace

Allows equipment suppliers to:

- List products
- Offer pricing
- Integrate with installation services

### 8. Implementation Requirements

**Technical Requirements**

- Data integration with water company systems
- Secure subscriber data management
- Machine learning for consumption analysis
- Mobile applications for specialists
- Web portal for subscribers
- Marketplace infrastructure

**Organizational Requirements**

- Partnership with water companies
- Certification program for specialists
- Agreements with equipment providers
- Collaboration with educational institutions

**Legal and Regulatory Considerations**

- Data privacy protection
- Consumer protection
- Certification standards
- Equipment quality standards

### 9. Business Model

Possible revenue streams:

- Commission from equipment sales
- Service fees for inspections
- Platform subscription from providers
- Data analytics services for water utilities
- Training program partnerships

### 10. Expected Benefits

**Environmental Benefits**

- Reduced water consumption
- Lower pressure on water resources
- Improved sustainability

**Economic Benefits**

- Lower water bills for subscribers
- New business opportunities for specialists
- Increased market for water-saving technologies

**Operational Benefits for Water Companies**

- Better demand management
- Reduced infrastructure stress
- Improved customer relationships

### 11. Future Development

Future extensions of Abdit may include:

- Smart meter integration
- AI-driven predictive water demand models
- Automatic leak detection alerts
- Integration with smart home systems
- Regional water conservation planning tool
