# Meeting Q&A Cheat Sheet: Mnabaa Agentic Platform

**Target Audience**: CTO / Architecture Board / C-Level
**Goal**: Defend the architecture, justify the investment, and prove operational maturity.

---

## 🏗️ Strategy & ROI

**Q: Why build this custom platform? Why not just buy Microsoft Copilot or use ServiceNow GenAI?**
**A:** Two reasons: **Sovereignty** and **Actionability**.

1.  **Sovereignty**: Copilot sends data to US-managed models. We require 100% EU residency (Paris).
2.  **Actionability**: SaaS copilots are "Chatbots" (read-only). Mnabaa is a "Virtual Team" (read/write). We need custom logic to execute complex workflows across _multiple_ systems (ServiceNow + BigQuery + Drive) which siloed SaaS tools cannot do.

**Q: You quote €3,800/month. That sounds unrealistically low. What's the catch?**
**A:** You are correct, that is the **Infrastructure Run Cost** (Cloud bill). The _Total Cost of Ownership (TCO)_ includes the engineering team.
We estimate needing **1.5 FTEs** (Platform Engineer + Data Steward) to maintain the connectors and governance. However, we save ~€50k/year in ServiceNow GenAI license fees, which subsidizes this engineering effort. We trade "License Rent" for "Asset Ownership".

**Q: What is the ROI? When do we break even?**
**A:**

- **Cost**: ~€150k/year (Infra + 1.5 FTE).
- **Savings**:
  - **License Avoidance**: €50k/year (ServiceNow Pro Plus).
  - **Productivity**: 20% deflection of L1 tickets (4,000 hrs/yr @ €50/hr) = €200k/year.
- **Break-even**: Month 9.

**Q: Break down the €3,800/month infrastructure cost. What are we actually paying for?**
**A:** Based on 1,000 active users, 300,000 queries/month:

| Component                | Driver                              | Monthly Cost | Justification                                                |
| :----------------------- | :---------------------------------- | :----------- | :----------------------------------------------------------- |
| **Gemini (LLM)**         | Hybrid: 80% Flash + 20% Pro         | €200-500     | Flash is 10x cheaper for routing. Pro for complex reasoning. |
| **Vertex AI Search**     | Query volume (€2/1k queries)        | €600-1,000   | Tiered pricing. First 100k cheaper, scales up.               |
| **Cloud Run (API)**      | 2vCPU, 4GB RAM                      | €400-800     | Serverless auto-scales. Min instances = €400, peak = €800.   |
| **Cloud SQL (HA)**       | PostgreSQL + pgvector               | €250-400     | High Availability required for production.                   |
| **Cloud Storage**        | 3 buckets (Transient/Raw/Processed) | €50-100      | Minimal storage, high operation count.                       |
| **Secret Manager + KMS** | API keys + encryption               | €50-80       | Per-secret access charges.                                   |
| **Cloud Armor + LB**     | WAF + DDoS protection               | €100-150     | Essential for public endpoints.                              |
| **Logging/Monitoring**   | 500GB/month logs                    | €100-200     | Critical for debugging hallucinations.                       |

**The Big Variable**: Vertex AI Search dominates (€600-1k). If we double our query volume, this doubles too.

**Q: The Gemini costs seem low. How do you keep LLM costs under control at €200-500/month for 1,000 users?**
**A:** Three strategies:

1.  **"Flash-First" Routing**: The Supervisor uses **Gemini Flash** (10x cheaper than Pro). Only specialist agents escalate to Pro when needed.
2.  **Prompt Compression**: We strip unnecessary context. Instead of sending 50 KB of PDFs, we send 5 KB of extracted text.
3.  **Caching**: We use **Vertex AI Context Caching** for repetitive prompts (e.g., system instructions). This reduces token costs by 90% for cached content.

**Q: What about hidden costs? (Network egress, API calls to ServiceNow, etc.)**
**A:**

- **Network Egress**: Minimal. We stay within GCP (Cloud Run → Cloud SQL → Vertex AI = free). Only egress is to external SaaS (ServiceNow), ~10GB/month = €1.
- **ServiceNow API**: Their REST API has generous rate limits. We're using <100k API calls/month, well below standard tier.
- **BigQuery**: We use Dry-Run validation (free) and read-only queries on Authorized Views (minimal compute).

**Q: How does the cost scale if we go from 1,000 users to 10,000 users?**
**A:**

| Component            | Scaling Factor            | Cost at 10k Users        |
| :------------------- | :------------------------ | :----------------------- |
| **Gemini**           | Linear with queries       | €2,000-5,000             |
| **Vertex AI Search** | Linear with queries       | €6,000-10,000            |
| **Cloud Run**        | Logarithmic (auto-scales) | €1,500-2,500             |
| **Cloud SQL**        | Fixed (same DB size)      | €250-400                 |
| **Everything else**  | Minimal increase          | €500-700                 |
| **Total**            |                           | **€10,250-18,600/month** |

**Key Insight**: The infrastructure cost scales **sub-linearly** (10x users = 3-5x cost) because the database and fixed overhead don't scale. However, you'd need **3-4 FTEs** to manage that scale, so TCO becomes ~€50k/month.

**Q: Can we reduce costs further? What are the optimization opportunities?**
**A:**

1.  **Model Distillation**: Train a smaller, custom model on our FAQ data. Could reduce LLM costs by 50%, but requires ML expertise.
2.  **Self-Hosted Vector DB**: Replace Vertex AI Search with open-source (Qdrant/Weaviate). Saves €600/month but adds operational burden.
3.  **Reserved Capacity**: GCP offers Cloud SQL committed use discounts (30% off). Worth it after 6 months of stable usage.

**Trade-off**: Every optimization adds technical debt or operational complexity. For Phase 1, we optimize for **speed to market**, not **cost minimization**.

---

## 🔒 Security & Sovereignty

**Q: Why Paris (`europe-west9`)? Why not Belgium or global?**
**A:** Paris offers the lowest latency for our French HQ (10ms vs 30ms). More importantly, it meets the strictest interpretation of "Data Sovereignty" — our data never leaves French soil, which simplifies legal compliance with GDPR and potential future regulations.

**Q: How do you prevent the AI from seeing PII (Credit Cards/Personal Info)?**
**A:** We use a **"Defense in Depth"** strategy:

1.  **Ingress**: Cloud DLP scans the user's prompt _before_ it touches the LLM. If it sees a credit card, it redacts it to `[CREDIT_CARD]`.
2.  **Egress**: The connectors (ServiceNow/Salesforce) have strict field masking. We explicitly define which fields are read.

**Q: What prevents an agent from "going rogue" and deleting our database?**
**A:**

1.  **Read-Only Defaults**: 90% of tools are read-only.
2.  **Human-in-the-Loop**: Any "Destructive Action" (Delete, Refund > €50) triggers an **Approval Card** in the UI. The agent _proposes_ the action; the human _signs_ it.
3.  **VPC Service Controls**: Even if an agent is hacked, it cannot send data to an external IP. It is network-isolated.

---

## ⚙️ Operations & "Day 2"

**Q: ServiceNow updates their API every 6 months. Won't your custom connector break?**
**A:** This is a managed risk. We strictly type our connectors using **Pydantic Schemas**.
We have a **"Golden Contract" CI/CD pipeline**. Every night, we run integration tests against a ServiceNow dev instance. If an API changes, the build fails _before_ production is affected, giving us time to patch the 10 lines of Python code.

**Q: How do we debug a "Hallucination"?**
**A:** We don't guess; we trace.
We use **LangGraph Native Monitoring**. We can see the exact state history:

1.  User Input.
2.  Supervisor Decision ("I choose the IT Agent").
3.  IT Agent Retrieval ("I found KB Article #123").
4.  Final Answer.
    We can pinpoint exactly which step failed (bad routing vs bad data) and fix it.

**Q: What happens if the LLM is slow or down?**
**A:**

- **Slow**: We use **Streaming**. The user sees the first token in <1s, even if the full task takes 10s.
- **Down**: We have **Circuit Breakers**. If Vertex AI fails, the system degrades to "Search Only" mode (returning raw links) rather than hanging or crashing.

---

## 💻 Technology Stack

**Q: Why Python? Why not Java/Node?**
**A:** Python is the native language of AI.

- **Libraries**: LangGraph, Pydantic, Pandas are Python-first.
- **Talent**: AI Engineers work in Python.
- **Performance**: The heavy lifting is done by the C++ kernels in the libraries (TensorFlow/Torch) or the API (Gemini). The Python layer is just thin orchestration glue.

**Q: Why "Transient Uploads"? Why not just upload everything to Drive?**
**A:** Hygiene and Privacy.

- **Hygiene**: We don't want the Corporate Brain polluted with one-off "Lunch Menu.pdf" or "Competitor Report.pdf".
- **Privacy**: Users may upload sensitive HR docs for analysis. By deleting them after 24h, we guarantee we aren't accidentally storing "toxic" data forever.

---

## 🏗️ Deep Dive: Physical Architecture

**Q: You rely heavily on Cloud Run (Serverless). What about Cold Starts? Won't that kill the user experience?**
**A:** Valid concern. We mitigate this in three ways:

1.  **Min Instances**: We configure `min-instances=1` for the API, keeping a warm container ready for the Supervisor (latency sensitive).
2.  **Async Workers**: Heavy tasks (ServiceNow processing) are offloaded to **Cloud Run Jobs** or async workers. The user gets an immediate "I'm working on it..." acknowledgment, so the cold start is masked.
3.  **Startup Boost**: We use Cloud Run's "CPU boost" to speed up the Python runtime initialization during boot.

**Q: VPC Service Controls (VPC-SC) are notoriously hard to manage. Are you sure we need this complexity?**
**A:** For a "Luxury" client with high IP value, **Yes**.
VPC-SC is the only control that stops a _valid_ credential from extracting data to a personal Gmail account.
**Mitigation**: We don't implement it blindly. We use **Dry-Run Mode** first to identify all legitimate traffic patterns (GitHub Actions, Monitoring) and whitelist them before enforcing the perimeter. This prevents the "break the world" scenario.

**Q: Scaling pgvector on Cloud SQL: When do we hit the wall? Why not Pinecone/Weaviate?**
**A:** We chose Cloud SQL (PostgreSQL) for **operational simplicity** (one DB to backup/monitor).

- **Limit**: `pgvector` with HNSW indexes scales well to ~10M-50M vectors. Our internal knowledge base (Confluence + Drive) is <500k documents. We are orders of magnitude away from the limit.
- **Future**: If we reach 100M+, we can seamlessly migrate to **Vertex AI Vector Search** (managed Scalann) without changing the application logic, just the retrieval connector.

**Q: What happens if `europe-west9` (Paris) goes down? (Regional Failure)**
**A:**

- **Phase 1 (MVP - "Region-Zonal")**:
  - **Architecture**: Cloud Run is multi-zonal by default (resilient to data center fire), but Cloud SQL is Zonal.
  - **SLO**: 99.9% Availability.
  - **Risk**: If the entire Paris region goes dark (e.g., major fiber cut), the service halts.
  - **Justification**: For an internal L1 Support tool, we accept a 4-hour **RTO (Recovery Time Objective)** in a catastrophic event rather than paying x2 for multi-region redundancy immediately.
- **Phase 3 (Global Scale - "Active-Passive")**:
  - **Architecture**: Standby stack in `europe-west1` (Belgium).
  - **Data**: **Cloud SQL Cross-Region Read Replicas** (async replication).
  - **Failover Process**:
    1.  **Traffic**: Global External Load Balancer detects 502s from Paris.
    2.  **Data**: Promote Belgium Read Replica to Master (**RPO < 5s** lag).
    3.  **Compute**: Infrastructure Manager (Terraform) automatically scales up Belgium Cloud Run instance count (from 0 to N).
  - **Result**: ~15 minutes to full operational capacity.

**Q: How do secure the connection between Cloud Run and the external SaaS tools (ServiceNow)?**
**A:** We rely on **Identity + Network + Secrets** (The "Triple Lock").

1.  **Network Identity (The "Static IP")**:
    - **Path**: Cloud Run $\rightarrow$ Serverless VPC Connector $\rightarrow$ Cloud Router $\rightarrow$ **Cloud NAT**.
    - **Benefit**: This guarantees all egress traffic exits via a single, dedicated Static IP (e.g., `34.x.x.x`).
    - **Enforcement**: ServiceNow IP Access Control List (ACL) is configured to whitelist _only_ this IP. All other traffic is dropped.
2.  **Application Identity (Least Privilege)**:
    - We do not use generic "System Users". The Agent uses a specific Service Account with scoped roles (e.g., `sn_incident_write`).
3.  **Credential Hygiene**:
    - API Keys are stored in **Secret Manager** and mounted as volumes. They are never exposed in environment variables.
    - Even if an attacker stole the API Key, they couldn't use it from their laptop because the **IP Check would fail**.

---

## 🤖 AI Governance & Ethics

**Q: "Hallucinations" are a dealbreaker. How can you guarantee the agent won't lie to an employee?**
**A:** We cannot "guarantee" 0% hallucination (no LLM can), but we **minimize and contain** it:

1.  **Grounding**: The agent is instructed to _only_ answer from the retrieved context. If the answer isn't in Confluence, it says "I don't know."
2.  **Citations**: Every answer must include a clickable link to source document. Users are trained to "Trust but Verify."
3.  **Shadow Validation**: We log every "thumbs down" feedback. A "Red Team" reviews these weekly to update the "Negative Constraints" in the system prompt (e.g., "Do not confuse 'Process A' with 'Process B'").

**Q: What if the model outputs biased or toxic content?**
**A:**

- **Vertex AI Safety Filters**: We set these to "Block High Probability" for Hate Speech and Harassment.
- **Output Guardrails**: We use a lightweight classifier on the _output_ text. If it detects toxicity, the response is replaced with a generic error message, protecting the user.

---

## 🔄 Data Strategy & Ingestion

**Q: How do you handle stale data? If a Price List is updated, does the agent know immediately?**
**A:**

- **Google Drive**: Live sync. The update is visible in search in ~10 minutes.
- **Confluence/ServiceNow**: We run an **Hourly Sync Job**.
- **Cleanup**: Our ingestion pipeline has a "Tombstone" check. If a document is deleted in source, we remove it from the Vector Store during the next hourly run to prevent "Ghost Knowledge."

**Q: What about "conflicting info"? (e.g. 2024 Policy vs 2025 Policy)**
**A:** We use **Metadata Filtering**.

- The Search Tool prioritizes documents with `year=2025` or `status=approved`.
- We explicitly downrank documents with `status=archived` or `folder=legacy` to preventing the agent from reading old policies.

---

## 🔮 Future Proofing

**Q: What if we want to switch to GPT-5 or Claude later? Are we locked into Google?**
**A:**

- **Model Agnostic Code**: We use **LangChain/LangGraph**. Switching models is literally changing one line of configuration: `model="gemini-1.5-pro"` to `model="gpt-5"`.
- **Vendor Lock-in Risk**: The "Sticky" part is the **Vector Database** (Cloud SQL) and **Data Pipeline**, not the LLM. Since we use standard Postgres (`pgvector`) and Python, we can migrate the data layer to Azure/AWS with standard database tools if forced.

**Q: How do we prevent "Token Bill Shock" if an agent gets stuck in a loop?**
**A:**

1.  **Hard Limit**: The Supervisor has a `max_steps=10` limit. If the problem isn't solved in 10 steps, it halts and asks for human help.
2.  **Budget Alerts**: We set a GCP Budget Alert at 50% and 90% of expected spend. If we hit 90% in Week 2, we receive an email immediately.
