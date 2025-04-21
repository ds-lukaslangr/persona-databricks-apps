from fastapi import FastAPI, BackgroundTasks, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from databricks import sql
from databricks.sdk import WorkspaceClient
from databricks.sdk.core import Config

import pandas as pd
import yaml
from pathlib import Path
import os
from datetime import datetime, time
import asyncio
import json
from pydantic import BaseModel

app = FastAPI()

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins in Databricks Apps
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def sqlQuery(query: str) -> pd.DataFrame:
    cfg = Config() # Pull environment variables for auth
    with sql.connect(
        server_hostname=cfg.host,
        http_path=f"/sql/1.0/warehouses/{os.getenv('DATABRICKS_WAREHOUSE_ID')}",
        credentials_provider=lambda: cfg.authenticate
    ) as connection:
        with connection.cursor() as cursor:
            cursor.execute(query)
            return cursor.fetchall_arrow().to_pandas()

# Load data
df = sqlQuery(f"SELECT * FROM {os.getenv('INPUT_TABLE')}")  # Replace with your SQL query

# Create necessary directories
SEGMENTS_DIR = Path("segments")
SEGMENTS_DIR.mkdir(exist_ok=True)
EXPORTS_DIR = Path("exports")
EXPORTS_DIR.mkdir(exist_ok=True)
SCHEDULES_FILE = Path("schedules.json")

# Initialize schedules
if not SCHEDULES_FILE.exists():
    with open(SCHEDULES_FILE, "w") as f:
        json.dump([], f)

def load_schedules():
    with open(SCHEDULES_FILE, "r") as f:
        return json.load(f)

def save_schedules(schedules):
    with open(SCHEDULES_FILE, "w") as f:
        json.dump(schedules, f)

def export_segment(segment_name, format):
    # Try loading as YAML first
    segment_file = SEGMENTS_DIR / f"{segment_name}.yaml"
    if segment_file.exists():
        with open(segment_file) as f:
            segment = yaml.safe_load(f)
            # Apply conditions
            mask = pd.Series(True, index=df.index)
            for column, condition in segment["conditions"].items():
                if isinstance(condition, dict):
                    if "min" in condition or "max" in condition:
                        if "min" in condition:
                            mask &= df[column] >= condition["min"]
                        if "max" in condition:
                            mask &= df[column] <= condition["max"]
                    elif "values" in condition:
                        mask &= df[column].isin(condition["values"])
            filtered_df = df[mask]
    else:
        # Try loading as SQL
        sql_file = SEGMENTS_DIR / f"{segment_name}.sql"
        if sql_file.exists():
            with open(sql_file) as f:
                segment = json.load(f)
                filtered_df = df.query(segment["query"])
        else:
            raise HTTPException(status_code=404, detail="Segment not found")
    
    # Export filtered data
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    export_path = EXPORTS_DIR / f"{segment_name}_{timestamp}.{format}"
    
    if format == "csv":
        filtered_df.to_csv(export_path, index=False)
    elif format == "json":
        filtered_df.to_json(export_path, orient="records")
    elif format == "parquet":
        filtered_df.to_parquet(export_path, index=False)

async def schedule_runner():
    while True:
        schedules = load_schedules()
        current_time = datetime.now()
        current_hour = current_time.hour
        current_minute = current_time.minute
        
        for schedule in schedules:
            should_run = False
            last_run = datetime.fromisoformat(schedule["last_run"]) if schedule["last_run"] else None
            
            if "run_time" in schedule:
                # Time-based schedule
                schedule_time = datetime.strptime(schedule["run_time"], "%H:%M").time()
                if (current_hour == schedule_time.hour and 
                    current_minute == schedule_time.minute and
                    (not last_run or last_run.date() < current_time.date())):
                    should_run = True
            else:
                # Interval-based schedule
                interval_hours = schedule["interval_hours"]
                if not last_run or (current_time - last_run).total_seconds() / 3600 >= interval_hours:
                    should_run = True
            
            if should_run:
                export_segment(schedule["segment_name"], schedule["format"])
                schedule["last_run"] = current_time.isoformat()
                save_schedules(schedules)
        
        await asyncio.sleep(60)  # Check every minute

@app.on_event("startup")
async def startup_event():
    asyncio.create_task(schedule_runner())

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

@app.post("/api/save-sql-segment")
async def save_sql_segment(data: dict):
    segment_file = SEGMENTS_DIR / f"{data['name']}.sql"
    with open(segment_file, "w") as f:
        json.dump({
            "name": data["name"],
            "query": data["query"],
            "type": "sql"
        }, f)
    return {"message": "SQL segment saved successfully"}

@app.post("/api/evaluate-sql-segment")
async def evaluate_sql_segment(data: dict):
    try:
        print(data["query"])
        # Execute the SQL query against the pandas DataFrame
        result = df.query(data["query"])
        return {
            "count": len(result),
            "total": len(df),
            "percentage": round(float(len(result)) / len(df) * 100, 2)
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/api/segments")
def get_segments():
    segments = []
    # Load YAML segments
    for file in SEGMENTS_DIR.glob("*.yaml"):
        with open(file) as f:
            segment = yaml.safe_load(f)
            segment["type"] = "condition"  # Add type to distinguish from SQL segments
            segments.append(segment)
    
    # Load SQL segments
    for file in SEGMENTS_DIR.glob("*.sql"):
        with open(file) as f:
            segment = json.load(f)
            segments.append(segment)
    
    return segments

@app.delete("/api/segments/{segment_name}")
def delete_segment(segment_name: str):
    # Try deleting YAML segment first
    segment_file = SEGMENTS_DIR / f"{segment_name}.yaml"
    if segment_file.exists():
        segment_file.unlink()  # Delete the file
        return {"message": "Segment deleted successfully"}
    
    # Try deleting SQL segment if YAML wasn't found
    sql_file = SEGMENTS_DIR / f"{segment_name}.sql"
    if sql_file.exists():
        sql_file.unlink()  # Delete the file
        return {"message": "Segment deleted successfully"}
    
    raise HTTPException(status_code=404, detail="Segment not found")

@app.post("/api/schedule-export")
async def schedule_export(data: dict):
    schedules = load_schedules()
    new_schedule = {
        "segment_name": data["segment_name"],
        "format": data["format"],
    }
    
    if "run_time" in data:
        new_schedule["run_time"] = data["run_time"]
    else:
        new_schedule["interval_hours"] = data["interval_hours"]
    
    new_schedule["last_run"] = None
    schedules.append(new_schedule)
    save_schedules(schedules)
    return {"message": "Export scheduled successfully"}

@app.get("/api/schedules")
async def get_schedules():
    return load_schedules()

@app.post("/api/export-now")
async def export_now(background_tasks: BackgroundTasks, data: dict):
    background_tasks.add_task(export_segment, data["segment_name"], data["format"])
    return {"message": "Export started"}

class ChatMessage(BaseModel):
    message: str

conversation_id: str = None

@app.post("/api/chat")
async def chat_with_genie(chat_message: ChatMessage):
    global conversation_id

    try:
        cfg = Config()
        genie_space_id = os.getenv('DATABRICKS_GENIE_SPACE_ID')
        if not genie_space_id:
            raise HTTPException(status_code=400, detail="DATABRICKS_GENIE_SPACE_ID environment variable not set")

        w = WorkspaceClient()
        
        print(f"Chat message: {chat_message.message}")
        print(f"Conversation ID: {conversation_id}")
        # Start a new conversation with the mess 
        if conversation_id is None:
            genie_message = w.genie.start_conversation_and_wait(
                space_id=genie_space_id,
                content=chat_message.message
            )
            conversation_id = genie_message.conversation_id
        else:
            genie_message = w.genie.create_message_and_wait(
                space_id=genie_space_id,
                conversation_id=conversation_id,
                content=chat_message.message
            )

        print(f"Response: {genie_message.as_dict()}")

        attachments = []

        for attachment in genie_message.attachments:
            if attachment.text is not None:
                attachments.append({
                    "type": "text",
                    "content": attachment.text.content,
                })
            elif attachment.query is not None:
                attachments.append({
                    "type": "query",
                    "sql": attachment.query.query,
                    "status": attachment.query.title,
                })

        result = {
            "attachments": attachments
        }

        print(f"Result: {result}")
            
        return result

    except Exception as e:
        print(f"Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

BASE_DIR = Path(__file__).parent
STATIC_ASSETS_PATH = BASE_DIR.parent / "frontend/static"

# Mount static files from frontend build AFTER all API routes
app.mount("/", StaticFiles(directory=STATIC_ASSETS_PATH, html=True), name="static")
