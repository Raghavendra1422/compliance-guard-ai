# 🛡️ Compliance-Guard AI

An AI-powered RBI loan compliance checker that analyzes loan applications against RBI circulars and guidelines using Deep RAG and agentic hallucination detection.

---

## 🧠 Problem Statement

Banks and NBFCs process thousands of loan applications daily. Compliance officers must manually check each application against hundreds of RBI circulars — a slow, error-prone, and expensive process.

**Key problems:**
- RBI guidelines change frequently — manual tracking is unreliable
- Human reviewers miss edge cases under volume pressure
- No audit trail for compliance decisions
- Hallucinated compliance answers from plain LLMs are dangerous in banking

---

## ✅ Solution — RAG-Powered Compliance Engine

```
RBI Circular PDFs
      ↓
[Ingestion Pipeline]   → Chunks, embeds, stores in ChromaDB
      ↓
Loan Application Query
      ↓
[RAG Retrieval]        → Finds relevant RBI guidelines semantically
      ↓
[Hallucination Guard]  → Verifies answer is grounded in source docs
      ↓
Compliance Report with citations
```

---

## 🏗️ Architecture

```
compliance-guard-ai/
│
├── backend/
│   ├── main.py              # FastAPI entry point
│   ├── rag/
│   │   ├── ingestor.py      # PDF chunking + embedding pipeline
│   │   ├── retriever.py     # Semantic search on ChromaDB
│   │   └── chain.py         # RAG chain with hallucination guard
│   ├── routers/
│   │   ├── documents.py     # Upload + manage RBI circulars
│   │   └── compliance.py    # Check compliance queries
│   └── requirements.txt
│
├── frontend/
│   ├── src/
│   │   ├── components/      # React components
│   │   └── pages/           # App pages
│   └── package.json
│
└── README.md
```

---

## 🛠️ Tech Stack

| Component | Technology | Purpose |
|---|---|---|
| Backend | **FastAPI + Python** | REST API server |
| AI Framework | **LangChain** | RAG pipeline orchestration |
| Vector Store | **ChromaDB** | Store and retrieve RBI circular embeddings |
| LLM | **Groq (LLaMA 3.3 70B)** | Compliance answer generation |
| Embeddings | **HuggingFace** | Document and query embeddings |
| Frontend | **React + Tailwind CSS** | User interface |
| PDF Processing | **PyMuPDF** | Extract text from RBI circulars |

---

## ⚙️ Setup & Installation

### Backend
```bash
cd backend
python -m venv venv

# Windows
venv\Scripts\activate

# Mac/Linux
source venv/bin/activate

pip install -r requirements.txt
uvicorn main:app --reload
```

### Frontend
```bash
cd frontend
npm install
npm run dev
```

### Environment Variables

Create `backend/.env`:
```env
GROQ_API_KEY=your_groq_key
GROQ_MODEL=llama-3.3-70b-versatile
CHROMA_DB_PATH=./chroma_db
```

---

## 💡 Key AI Concepts Demonstrated

- **Deep RAG** — multi-stage retrieval with re-ranking for higher accuracy
- **Hallucination Guard** — verifies every answer is grounded in source RBI documents
- **Semantic Search** — finds relevant guidelines even when query wording differs from circular
- **Agentic Workflow** — agent decides when to retrieve more context vs answer directly
- **Citation Tracking** — every compliance decision links back to the exact RBI circular

---

## 🔑 Why RAG Over Plain LLM for Compliance

| Problem with plain LLM | How RAG solves it |
|---|---|
| Hallucinated compliance rules | Answers grounded in actual RBI documents |
| Outdated training data | New circulars ingested in real time |
| No citations | Every answer cites the exact circular |
| Generic answers | Retrieves the specific relevant guideline |
| Dangerous in banking | Hallucination guard rejects ungrounded answers |

---

## 📈 Future Improvements

- [ ] Add support for SEBI and IRDAI guidelines
- [ ] Automated circular ingestion from RBI website
- [ ] Compliance dashboard with analytics
- [ ] Multi-language support for regional languages
- [ ] Audit trail export for regulatory reporting

---

## 👤 Author

**Chelimela Raghavendra Goud**
- GitHub: [@Raghavendra1422](https://github.com/Raghavendra1422)
- LinkedIn: [raghavendra1422](https://linkedin.com/in/raghavendra1422)
