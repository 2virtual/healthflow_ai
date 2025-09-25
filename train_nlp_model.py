# healthflow_ai/train_nlp_model.py
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report
import joblib
import re
import scipy.sparse as sp
import os

print("📂 Loading data...")
df = pd.read_csv("data/traineddf_with_level1.csv")

# Combine text fields
df["symptoms_text"] = (
    df["Chief_complain"].fillna("") + " " + 
    df["Diagnosis.in.ED"].fillna("")
).str.strip()

# Clean dataset
train_df = df[[
    "symptoms_text", "Age", "Sex", "KTAS_expert"
]].copy()

train_df = train_df[
    (train_df["symptoms_text"] != "") & 
    (train_df["KTAS_expert"].notna())
].dropna()

print(f"✅ Training samples: {len(train_df)}")

# Clean text
def clean_text(text):
    if not isinstance(text, str):
        return ""
    text = text.lower()
    text = re.sub(r'[^a-zA-Z0-9\s]', ' ', text)
    text = re.sub(r'\s+', ' ', text)
    return text.strip()

train_df["symptoms_clean"] = train_df["symptoms_text"].apply(clean_text)

# Features & labels
X_text = train_df["symptoms_clean"]
X_meta = train_df[["Age", "Sex"]]
y = train_df["KTAS_expert"].astype(int)

# Split
X_train_text, X_test_text, X_train_meta, X_test_meta, y_train, y_test = train_test_split(
    X_text, X_meta, y, test_size=0.2, random_state=42, stratify=y
)

# TF-IDF
print("📈 Vectorizing text...")
tfidf = TfidfVectorizer(
    max_features=5000,
    ngram_range=(1, 2),
    stop_words='english',
    min_df=2,
    max_df=0.95
)

X_train_tfidf = tfidf.fit_transform(X_train_text)
X_test_tfidf = tfidf.transform(X_test_text)

# Combine with metadata
X_train_full = sp.hstack([X_train_tfidf, X_train_meta])
X_test_full = sp.hstack([X_test_tfidf, X_test_meta])

# Train model
print("🧠 Training Logistic Regression model...")
model = LogisticRegression(
    multi_class='multinomial',
    solver='lbfgs',
    max_iter=1000,
    random_state=42
)
model.fit(X_train_full, y_train)

# Evaluate
y_pred = model.predict(X_test_full)
print("\n📊 Classification Report:")
print(classification_report(y_test, y_pred))

# Save model — INSIDE CONTAINER, BUT MAPPED TO backend/app/models/
MODEL_PATH = "backend/app/models/triage_nlp_model.joblib"
joblib.dump({
    'tfidf': tfidf,
    'model': model,
    'meta_cols': ["Age", "Sex"]
}, MODEL_PATH)

print(f"\n✅ Model saved to: {MODEL_PATH}")
print("🎉 Training complete!")