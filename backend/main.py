from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from databricks import sql
from databricks.sdk import WorkspaceClient
from databricks.sdk.core import Config

import pandas as pd
import yaml
from pathlib import Path
import os
from datetime import datetime
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

async def export_segment(segment_name: str, format: str = 'csv', destination: str = 'none'):
    # Get the current timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # Load and process the segment data
    df = load_segment_data(segment_name)
    
    # Generate the export filename
    filename = f"{segment_name}_{timestamp}.{format}"
    filepath = os.path.join('exports', filename)
    
    # Export the data in the requested format
    if format == 'csv':
        df.to_csv(filepath, index=False)
    elif format == 'json':
        df.to_json(filepath, orient='records')
    elif format == 'parquet':
        df.to_parquet(filepath, index=False)
    
    # Handle different export destinations
    if destination == 'salesforce':
        await export_to_salesforce(df, segment_name)
    elif destination == 'facebook':
        await export_to_facebook(df, segment_name)
    elif destination == 'google_ads':
        await export_to_google_ads(df, segment_name)
    
    return {"status": "success", "file": filename}

async def export_to_salesforce(df: pd.DataFrame, segment_name: str):
    # TODO: Implement Salesforce export logic
    pass

async def export_to_facebook(df: pd.DataFrame, segment_name: str):
    # TODO: Implement Facebook export logic
    pass

async def export_to_google_ads(df: pd.DataFrame, segment_name: str):
    # TODO: Implement Google Ads export logic
    pass

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

def create_default_segments():
    # Young adults segment
    young_adults = {
        "name": "Young adults",
        "conditions": {
            "Age": {
                "min": 18,
                "max": 35
            }
        },
        "type": "condition",
        "creator": {
            "name": "System",
            "email": "lukas.langr@datasentics.com"
        },
        "created_at": datetime.now().isoformat()
    }
    
    # Affluent customers segment
    affluent = {
        "name": "Affluent",
        "conditions": {
            "Balance": {
                "min": 100000
            },
            "AvgTxnAmt_3M": {
                "min": 1000
            }
        },
        "type": "condition",
        "creator": {
            "name": "System",
            "email": "lukas.langr@datasentics.com"
        },
        "created_at": datetime.now().isoformat()
    }
    
    # New customers SQL segment
    new_customers = {
        "name": "New customers",
        "query": "AccountOpenDate >= '2025-01-01'",
        "type": "sql",
        "creator": {
            "name": "System",
            "email": "lukas.langr@datasentics.com"
        },
        "created_at": datetime.now().isoformat()
    }
    
    # Save the segments if they don't already exist
    segments = [
        (young_adults, "yaml"),
        (affluent, "yaml"),
        (new_customers, "sql")
    ]
    
    for segment, format in segments:
        file_path = SEGMENTS_DIR / f"{segment['name']}.{format}"
        if not file_path.exists():
            with open(file_path, "w") as f:
                if format == "yaml":
                    yaml.dump(segment, f)
                else:
                    json.dump(segment, f)

@app.on_event("startup")
async def startup_event():
    # Create default segments
    create_default_segments()
    # Start the schedule runner
    asyncio.create_task(schedule_runner())

@app.get("/api/user")
async def get_user_info(request: Request):
    user = request.headers.get("X-Forwarded-User", "Unknown")
    email = request.headers.get("X-Forwarded-Email", "Unknown")
    return {
        "name": user,
        "email": email
    }

@app.get("/api/columns")
def get_columns(request: Request):
    return {
        "user": request.headers.get("X-Forwarded-User", "Unknown"),
        "email": request.headers.get("X-Forwarded-Email", "Unknown"),
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
async def save_segment(data: dict, request: Request):
    segment_file = SEGMENTS_DIR / f"{data['name']}.yaml"
    segment_data = {
        "name": data["name"],
        "conditions": data["conditions"],
        "type": "condition",
        "creator": {
            "name": request.headers.get("X-Forwarded-User", "Unknown"),
            "email": request.headers.get("X-Forwarded-Email", "Unknown")
        },
        "created_at": datetime.now().isoformat()
    }
    with open(segment_file, "w") as f:
        yaml.dump(segment_data, f)
    return {"message": "Segment saved successfully"}

@app.post("/api/save-sql-segment")
async def save_sql_segment(data: dict, request: Request):
    segment_file = SEGMENTS_DIR / f"{data['name']}.sql"
    segment_data = {
        "name": data["name"],
        "query": data["query"],
        "type": "sql",
        "creator": {
            "name": request.headers.get("X-Forwarded-User", "Unknown"),
            "email": request.headers.get("X-Forwarded-Email", "Unknown")
        },
        "created_at": datetime.now().isoformat()
    }
    with open(segment_file, "w") as f:
        json.dump(segment_data, f)
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
    segment_found = False
    
    if segment_file.exists():
        segment_file.unlink()  # Delete the file
        segment_found = True
    else:
        # Try deleting SQL segment if YAML wasn't found
        sql_file = SEGMENTS_DIR / f"{segment_name}.sql"
        if sql_file.exists():
            sql_file.unlink()  # Delete the file
            segment_found = True
    
    if not segment_found:
        raise HTTPException(status_code=404, detail="Segment not found")
    
    # Delete associated schedules
    schedules = load_schedules()
    # Keep only schedules that don't belong to the deleted segment
    updated_schedules = [s for s in schedules if s["segment_name"] != segment_name]
    
    # If any schedules were removed, update the schedules file
    if len(updated_schedules) != len(schedules):
        save_schedules(updated_schedules)
    
    return {"message": "Segment and its associated schedules deleted successfully"}

@app.post("/api/schedule-export")
async def schedule_export(request: dict):
    segment_name = request.get("segment_name")
    format = request.get("format", "csv")
    destination = request.get("destination", "none")
    interval_hours = request.get("interval_hours")
    run_time = request.get("run_time")
    
    if not segment_name:
        raise HTTPException(status_code=400, detail="Segment name is required")
        
    schedule = {
        "segment_name": segment_name,
        "format": format,
        "destination": destination,
        "last_run": None
    }
    
    if interval_hours:
        schedule["interval_hours"] = interval_hours
    elif run_time:
        schedule["run_time"] = run_time
    else:
        raise HTTPException(status_code=400, detail="Either interval_hours or run_time must be provided")
    
    # Load existing schedules and append the new one
    current_schedules = load_schedules()
    current_schedules.append(schedule)
    save_schedules(current_schedules)
    
    return {"status": "success"}

@app.get("/api/schedules")
async def get_schedules():
    return load_schedules()

@app.delete("/api/schedules/{schedule_index}")
async def delete_schedule(schedule_index: int):
    try:
        schedules = load_schedules()
        if schedule_index < 0 or schedule_index >= len(schedules):
            raise HTTPException(status_code=404, detail="Schedule not found")
            
        # Remove the schedule at the specified index
        removed_schedule = schedules.pop(schedule_index)
        save_schedules(schedules)
        
        return {"message": "Schedule deleted successfully", "deleted_schedule": removed_schedule}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/export-now")
async def export_now(request: dict):
    segment_name = request.get("segment_name")
    format = request.get("format", "csv")
    destination = request.get("destination", "none")
    
    if not segment_name:
        raise HTTPException(status_code=400, detail="Segment name is required")
        
    return await export_segment(segment_name, format, destination)

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
