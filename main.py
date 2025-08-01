import os
import io
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Any
from fastapi.middleware.cors import CORSMiddleware
import vertexai
from vertexai.generative_models import GenerativeModel
from google.cloud import bigquery, storage
import docx

# --- CONFIGURATION ---
PROJECT_ID = os.environ.get("GCP_PROJECT")
LOCATION = "us-central1"
GCS_BUCKET_NAME = "miva-query-backend-code" 

# --- Final list of your documentation files ---
DOCUMENTATION_FILES = [
    "Exam Portal Documentation-210725-075414.docx",
    "Moodle LMS Data Dictionary (A-U).docx",
    "Moodle LMS Data Dictionary (U-Z).docx",
    "SIS Documentation-210725-075529.docx"
] 

# --- CLIENT INITIALIZATION ---
vertexai.init(project=PROJECT_ID, location=LOCATION)
bq_client = bigquery.Client()
storage_client = storage.Client()
model = GenerativeModel("gemini-1.5-flash-001")

# --- FastAPI APP SETUP ---
app = FastAPI(title="MIVA RAG Query Assistant API", version="2.2.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- HELPER FUNCTION TO GET SCHEMA FROM DOCX ---
def get_schema_from_gcs(bucket_name: str, file_list: list) -> str:
    """Downloads, reads, and combines text from a list of .docx files in GCS."""
    full_schema_context = []
    try:
        bucket = storage_client.bucket(bucket_name)
        
        for file_name in file_list:
            blob = bucket.blob(file_name)
            
            # Download the file content into a memory buffer
            in_memory_file = io.BytesIO()
            blob.download_to_file(in_memory_file)
            in_memory_file.seek(0)
            
            # Read the .docx file from memory and add its text to our context
            document = docx.Document(in_memory_file)
            file_text = [para.text for para in document.paragraphs]
            full_schema_context.append('\n'.join(file_text))
            
        return '\n\n---\n\n'.join(full_schema_context) # Join docs with a separator
    except Exception as e:
        print(f"CRITICAL: Could not read documentation files. Error: {e}")
        return None

# --- Pydantic Models ---
class QueryRequest(BaseModel):
    natural_language_query: str

class QueryResponse(BaseModel):
    sql_query: str
    results: List[Dict[str, Any]]

# --- THE CORE LOGIC ---
@app.post("/query", response_model=QueryResponse)
async def get_sql_from_natural_language(request: QueryRequest):
    """
    Takes a natural language query, generates SQL using Gemini with RAG,
    executes it on BigQuery, and returns the results.
    """
    
    # 1. Retrieve schema from all documentation files in GCS
    schema_context = get_schema_from_gcs(GCS_BUCKET_NAME, DOCUMENTATION_FILES)
    if not schema_context:
        raise HTTPException(status_code=500, detail="Could not retrieve database documentation to build the query.")
        
    # 2. Construct the prompt for the AI Model
    prompt = f"""
    You are a Google BigQuery expert. Based on the following database documentation,
    write a single, valid, and executable SQL query to answer the user's question.
    Only return the SQL query and nothing else.

    Documentation:
    ---
    {schema_context}
    ---

    User Question: "{request.natural_language_query}"
    """
    
    # 3. Generate the SQL Query using Gemini
    try:
        response = model.generate_content(prompt)
        # Basic cleanup of the AI's response to get only the SQL
        generated_sql = response.text.strip().replace("```sql", "").replace("```", "").replace("`", "")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating SQL with AI: {e}")

    if not generated_sql:
        raise HTTPException(status_code=400, detail="AI could not generate a valid SQL query.")

    # 4. Execute the Query on BigQuery
    try:
        query_job = bq_client.query(generated_sql)
        results = query_job.result()
        rows = [dict(row) for row in results]
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error executing BigQuery job. SQL may be invalid. Details: {e}")

    return {"sql_query": generated_sql, "results": rows}

@app.get("/", include_in_schema=False)
async def root():
    return {"message": "MIVA RAG Query Assistant API is running."}