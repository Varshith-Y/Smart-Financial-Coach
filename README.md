# Smart Financial Coach (SFC)

An AI‑powered personal finance assistant that helps users understand their spending patterns, track category‑wise expenses, visualize trends, and receive budget insights — all powered by a FastAPI backend and a modern React (Vite) frontend.

---

## 🚀 Features

### **1. Monthly Spending Summary**
- Total amount spent for the selected month/year  
- Breakdown of spending by category  
- Automatic sorting by highest→lowest spend  
- Clean UI with category tables + bar charts  

### **2. Budget Insights Engine**
- Define budgets for each category  
- System automatically checks whether you are:
  - **On track**
  - **Near limit**
  - **Over budget**
- Generates human‑readable messages

### **3. Spending Trajectory (Trends)**
- Multi‑month spending history  
- Detects biggest spending jumps between months  
- Helps identify anomalies or lifestyle changes  

### **4. Fully Built API (FastAPI)**
Endpoints include:
- `/health`
- `/summary/monthly`
- `/insights/budget`
- `/summary/trajectory`

Data is backed by a local SQLite database (`sfc.db`).

---

## 🏗️ Tech Stack

### **Backend**
- Python  
- FastAPI  
- SQLite  
- Pandas  
- Uvicorn  
- Azure Container Apps (optional deploy)

### **Frontend**
- React (Vite)
- Chart.js for visualizations
- Modern dark‑mode UI

---

## 📂 Project Structure

```
smart-financial-coach/
│
├── app/                  # FastAPI backend source
├── data/                 # Raw + processed dataset
├── scripts/              # Helper scripts (ETL, preprocessing)
├── frontend/             # React application
├── sfc.db                # SQLite database
├── Dockerfile            # Backend Dockerfile
├── requirements.txt
└── README.md
```

---

## 🏃 Running the Project Locally

### **1. Backend**

```bash
cd app
pip install -r requirements.txt
uvicorn main:app --reload
```

Backend will be available at:

```
http://localhost:8000
```

Swagger docs:

```
http://localhost:8000/docs
```

---

### **2. Frontend**

```bash
cd frontend
npm install
npm run dev
```

Frontend available at:

```
http://localhost:5173
```

---

## 🚢 Optional: Deploying to Azure

The backend is fully compatible with Azure Container Apps.

Basic workflow:

```
az containerapp env create ...
az containerapp create ...
```

(Deployment steps intentionally omitted here to keep the README concise.)

---
