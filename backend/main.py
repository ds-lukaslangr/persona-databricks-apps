from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import pandas as pd
import yaml
from pathlib import Path
import os

app = FastAPI()

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],  # Vite's default port
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Load data
df = pd.read_csv("../bank_customer_data.csv")

# Create segments directory if it doesn't exist
SEGMENTS_DIR = Path("segments")
SEGMENTS_DIR.mkdir(exist_ok=True)

@app.get("/api/columns")
def get_columns():
    return {
        "columns": [
            {
                "name": col,
                "type": str(df[col].dtype),
                "unique_values": df[col].unique().tolist() if df[col].dtype == "object" else None
            }
            for col in df.columns
        ]
    }

@app.post("/api/evaluate-segment")
async def evaluate_segment(conditions: dict):
    mask = pd.Series(True, index=df.index)
    
    for column, condition in conditions.items():
        if isinstance(condition, dict):
            if "min" in condition or "max" in condition:
                # Numeric range condition
                if "min" in condition:
                    mask &= df[column] >= condition["min"]
                if "max" in condition:
                    mask &= df[column] <= condition["max"]
            elif "values" in condition:
                # Categorical multiselect condition
                mask &= df[column].isin(condition["values"])
    
    return {
        "count": int(mask.sum()),
        "total": len(df),
        "percentage": round(float(mask.sum()) / len(df) * 100, 2)
    }

@app.post("/api/save-segment")
async def save_segment(data: dict):
    segment_file = SEGMENTS_DIR / f"{data['name']}.yaml"
    with open(segment_file, "w") as f:
        yaml.dump(data, f)
    return {"message": "Segment saved successfully"}

@app.get("/api/segments")
def get_segments():
    segments = []
    for file in SEGMENTS_DIR.glob("*.yaml"):
        with open(file) as f:
            segment = yaml.safe_load(f)
            segments.append(segment)
    return segments