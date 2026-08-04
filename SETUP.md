# Setup Instructions

## 1. Clone repo
```bash
git clone <repo_url>
cd generative_ads_ai
```

## 2. Create virtual environment
```bash
python -m venv venv
```

## 3. Activate environment

**Windows:**
```bash
venv\Scripts\activate
```

**Mac/Linux:**
```bash
source venv/bin/activate
```

## 4. Install dependencies
```bash
pip install -r requirements.txt
```

## 5. Add API keys
Create a `.env` file in the root directory:
```
GEMINI_API_KEY=your_key
GROQ_API_KEY=your_key
```

## 6. Run project
```bash
streamlit run ui/app.py
```
