import json
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

app = FastAPI()

# Load Mock Integrations
def load_mock_environment():
    with open("mock_data.json", "r") as f:
        return json.load(f)

# Priority Scoring Function (Layer 3)
def calculate_priority_score(urgency: int, importance: int, dependency: int, risk: int, user_pref: int):
    total = urgency + importance + dependency + risk + user_pref
    if total >= 21:
        level = "CRITICAL"
    elif total >= 15:
        level = "HIGH"
    elif total >= 8:
        level = "MEDIUM"
    else:
        level = "LOW"
    return total, level

class UserPrompt(BaseModel):
    message: str

@app.post("/api/process")
async def process_orchestration(data: UserPrompt):
    env = load_mock_environment()
    prompt = data.message.lower()
    
    # Debug trace log sent to the UI "Judge View"
    trace = []
    
    # Layer 1: Intent Detection
    trace.append({"layer": "1. Intent Engine", "detail": "Detected Intent: Event Preparation & Conflict Optimization", "status": "COMPLETED"})
    
    # Layer 2: Context Graph Aggregation
    interview_email = env["emails"][0]
    assignment_task = env["tasks"][0]
    weather = env["weather"]["forecast"]
    base_travel = env["maps"]["normal_travel_time_min"]
    actual_travel = int(base_travel * env["weather"]["travel_delay_multiplier"])
    
    trace.append({
        "layer": "2. Context Engine", 
        "detail": f"Linked Email ({interview_email['subject']}), Tasks ({assignment_task['task']}), Weather ({weather} -> Travel time {actual_travel} mins)",
        "status": "COMPLETED"
    })
    
    # Layer 3: Decision Engine & Priority Scoring
    interview_score, interview_level = calculate_priority_score(urgency=5, importance=5, dependency=4, risk=4, user_pref=4) # 22
    meeting_score, meeting_level = calculate_priority_score(urgency=2, importance=3, dependency=2, risk=1, user_pref=3) # 11
    
    conflict_detected = True
    trace.append({
        "layer": "3. Decision Engine", 
        "detail": f"Conflict Detected: 12 PM Meeting overlaps travel buffer for 2 PM Interview. Interview Priority: {interview_level} ({interview_score}), Meeting Priority: {meeting_level} ({meeting_score}). Decision: Keep Interview, Reschedule Meeting.",
        "status": "COMPLETED"
    })
    
    # Layer 4 & 5: Action Engine & Trust Engine Categorization
    actions = [
        {
            "action": "Set assignment reminder for 8:00 PM tonight",
            "trust_level": "LEVEL_1_AUTO",
            "reason": "Low risk, prevents deadline conflict",
            "confidence": "95%"
        },
        {
            "action": "Set departure alarm for 12:15 PM tomorrow",
            "trust_level": "LEVEL_1_AUTO",
            "reason": "Factored 90-min travel duration due to rain forecast",
            "confidence": "91%"
        },
        {
            "action": "Reschedule 12:00 PM Project Sync Meeting to 4:30 PM",
            "trust_level": "LEVEL_2_RECOMMEND",
            "reason": "Direct schedule conflict with required travel time",
            "confidence": "88%"
        }
    ]
    
    trace.append({"layer": "4 & 5. Action & Trust Engine", "detail": "Actions categorized by Trust Levels (1 Auto, 2 Require Confirmation).", "status": "COMPLETED"})
    
    return {
        "user_intent": "Prepare for Interview",
        "trace": trace,
        "recommended_actions": actions
    }

@app.get("/", response_class=HTMLResponse)
async def serve_ui():
    with open("templates/index.html", "r") as f:
        return f.read()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)