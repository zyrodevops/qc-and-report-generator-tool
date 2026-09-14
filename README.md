# Marine Cargo Survey & QC Report Generator Tool

A specialized, IRDAI-compliant web platform for marine cargo surveyors to inspect cargo, transcribe tally sheets via OCR, manage survey photographs, and generate bit-exact, audit-traceable QC and survey inspection reports in Microsoft Word (`.docx`) and PDF formats.

Built on a **Block State** engine where all arithmetic calculations (totals, percentages, photo ranges, and annexure numbering) are computed fresh at render time using exact Decimal precision.

---

## 🛠 Prerequisites

Ensure you have the following installed on your host machine:

- **Python**: 3.12+
- **Node.js**: 18+ (with npm)
- **Docker & Docker Compose**: For PostgreSQL (v16) & Redis (v7)
- **System Dependencies** (for PDF export & OCR):
  - Ubuntu/Debian:
    ```bash
    sudo apt-get update && sudo apt-get install -y \
      libreoffice-core libreoffice-writer antiword \
      tesseract-ocr tesseract-ocr-eng libgl1 libglib2.0-0
    ```

---

## 🚀 Running for Development

### 1. Clone the Repository & Setup Environment

```bash
git clone https://github.com/zyrodevops/qc-and-report-generator-tool.git
cd qc-and-report-generator-tool

# Copy environment variables template
cp .env.example .env
```

*(Optional)* Configure your `.env` file if custom database credentials or port numbers are needed.

---

### 2. Start Infrastructure Services (Database & Redis)

Start PostgreSQL and Redis in the background using Docker Compose:

```bash
docker compose up -d db redis
```

---

### 3. Setup & Start Backend (FastAPI)

In a new terminal:

```bash
# 1. Create and activate a Python 3.12 virtual environment
python3 -m venv .venv
source .venv/bin/activate

# 2. Install Python dependencies
pip install -r backend/requirements.txt

# 3. Apply database migrations
cd backend
alembic upgrade head
cd ..

# 4. Start the FastAPI development server with hot-reload
uvicorn backend.app.main:app --host 0.0.0.0 --port 8000 --reload
```

The backend API will be running at:
- **API**: [http://localhost:8000](http://localhost:8000)
- **Swagger Docs**: [http://localhost:8000/docs](http://localhost:8000/docs)

---

### 4. Setup & Start Frontend (React + Vite + Tailwind CSS)

In a separate terminal:

```bash
cd frontend

# 1. Install Node.js dependencies
npm install

# 2. Start Vite development server
npm run dev
```

The frontend application will be live at:
- **Web App**: [http://localhost:5173](http://localhost:5173)

---

## 🔑 Default Login Credentials

The web application features password-protected client and surveyor access:

| Field | Value |
| :--- | :--- |
| **Access Key (Web UI Login)** | `surveyor123` |
| **Alternative Direct User** | `surveyor@example.com` / `Password123!` |
| **Demo Surveyor User** | `surveyor@oceanic-claims.test` / `SafePassword123!` |

---

## 🧪 Running Tests & Quality Gates

### Run Backend & Integrity Tests

```bash
source .venv/bin/activate
pytest backend/tests/ -q
```

### Build Frontend

```bash
cd frontend
npm run build
```

### Pre-commit Security Scan

The project includes an automatic pre-commit hook enforcing CRITICAL-RULES §8 (preventing accidental commits of IRDAI licence numbers, sensitive client names, or raw `.doc`/`sample-data` files):

```bash
.git/hooks/pre-commit
```

---

## 🔬 Corpus Mining Tool (Standalone)

To re-mine client reports and extract section headings, defect frequencies, and arithmetic checks:

```bash
python tools/mine_corpus.py --corpus sample-data/perishable_fruits --output tools/perishable_fruits_output
```

This generates:
- `inventory.csv`: Inventory of parsed report files
- `block_sequences.csv`: Discovered section and heading sequence archetypes
- `defect_categories.csv`: Cleaned defect category column mappings
- `sentence_frequency.csv`: Standardized clause library by frequency
- `arithmetic_errors.csv`: Reconciled table arithmetic audits
- `template_archetypes.json`: Mined archetypes used by the report builder

---

## 🌟 Core Features

- **12 Commodity Archetypes**: Pre-fills authentic section sequences, defect tables, and domain-accurate narrative paragraphs for Apple, Grape, Blueberry, Mandarin, Orange, Pear, Kiwi, Cherry, Avocado, Plum, Apricot, and Dragon Fruit.
- **EasyOCR Tally Sheet Scanner**: Transcribes physical handwritten or printed tally sheets directly into defect count tables and temperature probe records with confidence scoring and cell normalization.
- **Photo Annexure Studio**:
  - **Upload & Manage**: In-block photo grid with caption auto-numbering (`Survey Photo No. X`) and reordering.
  - **Bulk Mode**: Drag-and-drop batch upload queue with reorder handles.
  - **Pro Studio**: Full DOCX customization with compression presets (High / Balanced / Small), border toggles, and typography settings.
  - **Standalone Annexure Page**: Full-screen photo studio accessible directly from the main header navigation.
- **Strict Arithmetic Engine**: Zero floating-point rounding errors (`Decimal` with `ROUND_HALF_UP` only); no computed values stored in database.