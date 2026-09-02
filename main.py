import json
import re
from typing import Dict, List, Any, Optional
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, Response
from pydantic import BaseModel

app = FastAPI()

# =====================================================================
# 1. FUNCTIONAL & STATEFUL ADAPTIVE MEMORY STORE
# =====================================================================
class MemoryStore:
    def __init__(self):
        # Stored preferences with dynamic confidence ratings
        self.preferences: Dict[str, Dict[str, Any]] = {}
        self.decision_history: List[Dict[str, Any]] = []

    def learn_preference(self, rule_key: str, description: str, was_approved: bool):
        if rule_key not in self.preferences:
            self.preferences[rule_key] = {
                "description": description,
                "approved_count": 0,
                "rejected_count": 0,
                "confidence": 60,
                "active": True
            }
        
        pref = self.preferences[rule_key]
        if was_approved:
            pref["approved_count"] += 1
            # Deterministic Confidence Boost: 60% -> 75% -> 90%
            if pref["approved_count"] == 1:
                pref["confidence"] = 60
            elif pref["approved_count"] == 2:
                pref["confidence"] = 75
            else:
                pref["confidence"] = min(95, pref["confidence"] + 5)
        else:
            pref["rejected_count"] += 1
            pref["confidence"] = max(40, pref["confidence"] - 15)
            if pref["rejected_count"] >= 2:
                pref["active"] = False

    def get_preference(self, rule_key: str) -> Optional[Dict[str, Any]]:
        pref = self.preferences.get(rule_key)
        if pref and pref["active"]:
            return pref
        return None

    def clear(self):
        self.preferences.clear()
        self.decision_history.clear()

memory = MemoryStore()

def load_mock_environment() -> Dict[str, Any]:
    with open("mock_data.json", "r") as f:
        return json.load(f)

# =====================================================================
# 2. INTENT ENGINE
# =====================================================================
class IntentEngine:
    @staticmethod
    def parse_intent(text: str) -> Dict[str, Any]:
        lower = text.lower()
        if any(w in lower for w in ["interview", "exam", "prepare", "test"]):
            intent_type = "Event Preparation"
        elif any(w in lower for w in ["meeting", "move", "reschedule", "conflict", "clash"]):
            intent_type = "Conflict Resolution"
        elif any(w in lower for w in ["assignment", "due", "priority", "task"]):
            intent_type = "Priority Optimization"
        else:
            intent_type = "General Coordination"

        entities = []
        if "interview" in lower: entities.append("Interview")
        if "exam" in lower: entities.append("Exam")
        if "meeting" in lower: entities.append("Project Sync")
        if "assignment" in lower: entities.append("Systems Assignment")

        return {
            "primary_intent": intent_type,
            "entities": entities,
            "raw_prompt": text
        }

# =====================================================================
# 3. CONTEXT & PRIORITY ENGINE
# =====================================================================
class ContextAndPriorityEngine:
    @staticmethod
    def evaluate(intent_data: Dict[str, Any], env: Dict[str, Any]) -> Dict[str, Any]:
        prompt_lower = intent_data["raw_prompt"].lower()
        scores = {}
        conflicts = []

        if "interview" in prompt_lower:
            scores["Interview"] = {"score": 22, "level": "CRITICAL"}
            scores["Project Sync"] = {"score": 11, "level": "MEDIUM"}
            scores["Assignment"] = {"score": 16, "level": "HIGH"}
            conflicts.append("12:00 PM Project Sync overlaps required 90-min travel window for 2:00 PM Interview.")
        elif "exam" in prompt_lower:
            scores["Exam Preparation"] = {"score": 22, "level": "CRITICAL"}
            scores["Project Sync"] = {"score": 11, "level": "MEDIUM"}
            conflicts.append("2:00 PM Project Sync overlaps required 3-hour focus window for Exam Preparation.")
        elif "meeting" in prompt_lower and "assignment" in prompt_lower:
            scores["Assignment"] = {"score": 20, "level": "CRITICAL"}
            scores["Project Sync"] = {"score": 13, "level": "HIGH"}
            conflicts.append("2:00 PM Meeting restricts focus time for 5:00 PM Assignment deadline.")
        else:
            scores["General Tasks"] = {"score": 8, "level": "LOW"}

        return {"scores": scores, "conflicts": conflicts}

# =====================================================================
# 4. DECISION ENGINE (WITH DYNAMIC MEMORY WEIGHTING)
# =====================================================================
class DecisionEngine:
    @staticmethod
    def resolve_and_plan(intent_data: Dict[str, Any], eval_data: Dict[str, Any], review_mode: bool) -> Dict[str, Any]:
        prompt_lower = intent_data["raw_prompt"].lower()
        actions = []
        applied_memory = []

        # Check Active Stored Preferences
        protect_pref = memory.get_preference("protect_critical_over_meetings")
        avoid_sync_reschedule = memory.get_preference("avoid_rescheduling_project_sync")

        # Scenario 1: Interview
        if "interview" in prompt_lower:
            actions.append({
                "id": "act_101",
                "action": "Set assignment reminder for 8:00 PM tonight",
                "trust_level": "LEVEL_1_AUTO" if not review_mode else "LEVEL_2_RECOMMEND",
                "reason": "Prevents deadline overlap with tomorrow's travel schedule.",
                "confidence": "95%",
                "status": "✓ Executed Automatically" if not review_mode else "Pending Review",
                "priority": "HIGH (16)",
                "explanation": "Priority: High (16). Risk: Low. Safe reversible action."
            })
            actions.append({
                "id": "act_102",
                "action": "Set departure alarm for 12:15 PM tomorrow",
                "trust_level": "LEVEL_1_AUTO" if not review_mode else "LEVEL_2_RECOMMEND",
                "reason": "Factored 90-min rain travel delay + 15-min buffer.",
                "confidence": "91%",
                "status": "✓ Executed Automatically" if not review_mode else "Pending Review",
                "priority": "CRITICAL (22)",
                "explanation": "Priority: Critical (22). Risk: Rain delay (2.0x travel multiplier)."
            })

            base_score = 72
            mem_boost = 0
            if protect_pref:
                mem_boost = int(protect_pref["confidence"] * 0.2) # Dynamic score boost based on confidence
                applied_memory.append(f"Applied Preference: '{protect_pref['description']}' (Confidence: {protect_pref['confidence']}%, Score adjustment: +{mem_boost})")

            actions.append({
                "id": "act_103",
                "action": "Reschedule 12:00 PM Project Sync Meeting to 4:30 PM",
                "trust_level": "LEVEL_2_RECOMMEND",
                "reason": "Earliest feasible slot post-interview, resolving travel conflict.",
                "confidence": f"{min(98, 88 + (mem_boost // 2))}%",
                "status": "Pending Approval",
                "priority": "MEDIUM (11)",
                "rule_key": "protect_critical_over_meetings",
                "rule_desc": "Protect high-priority events (Interviews/Exams) over standard meetings.",
                "explanation": f"Base Score: {base_score} | Memory Boost: +{mem_boost} | Final Score: {base_score + mem_boost}. Resolves travel conflict for Critical Interview (22)."
            })

        # Scenario 2: Exam (Tests stateful memory from Bangalore scenario)
        elif "exam" in prompt_lower:
            actions.append({
                "id": "act_201",
                "action": "Block 2:00 PM - 5:00 PM for Exam Study Block",
                "trust_level": "LEVEL_1_AUTO" if not review_mode else "LEVEL_2_RECOMMEND",
                "reason": "Protects minimum 3-hour focus window required for exam preparation.",
                "confidence": "94%",
                "status": "✓ Executed Automatically" if not review_mode else "Pending Review",
                "priority": "CRITICAL (22)",
                "explanation": "Priority: Critical (22). 3-Hour required continuous study block."
            })

            base_score = 65
            mem_boost = 0
            if protect_pref:
                mem_boost = int(protect_pref["confidence"] * 0.25)
                applied_memory.append(f"Adaptive Memory Applied: User previously approved protecting critical events over meetings. (Confidence: {protect_pref['confidence']}%, Score adjustment: +{mem_boost})")

            actions.append({
                "id": "act_202",
                "action": "Decline non-essential Project Sync Meeting at 2:00 PM",
                "trust_level": "LEVEL_2_RECOMMEND",
                "reason": "Clears schedule conflict during critical study window.",
                "confidence": f"{min(96, 84 + (mem_boost // 2))}%",
                "status": "Pending Approval",
                "priority": "LOW (8)",
                "rule_key": "protect_critical_over_meetings",
                "rule_desc": "Protect high-priority events (Interviews/Exams) over standard meetings.",
                "explanation": f"Base Score: {base_score} | Memory Boost: +{mem_boost} | Final Score: {base_score + mem_boost}. Selected automatically based on learned user preference."
            })

        # Scenario 3: Meeting Conflict
        elif "meeting" in prompt_lower and "assignment" in prompt_lower:
            actions.append({
                "id": "act_301",
                "action": "Shift Project Sync Meeting from 2:00 PM to 11:00 AM",
                "trust_level": "LEVEL_2_RECOMMEND",
                "reason": "Opens 3-hour focus block before 5:00 PM assignment deadline.",
                "confidence": "90%",
                "status": "Pending Approval",
                "priority": "HIGH (13)",
                "rule_key": "protect_critical_over_meetings",
                "rule_desc": "Protect high-priority events over standard meetings.",
                "explanation": "Opens focus block for Critical Assignment (20)."
            })
        else:
            actions.append({
                "id": "act_401",
                "action": "Create Context Review Task",
                "trust_level": "LEVEL_1_AUTO",
                "reason": "Request requires additional parameters.",
                "confidence": "70%",
                "status": "✓ Executed Automatically",
                "priority": "LOW (5)",
                "explanation": "General clarification action."
            })

        return {"actions": actions, "applied_memory": applied_memory}

# =====================================================================
# API ROUTES
# =====================================================================
class UserPrompt(BaseModel):
    message: str
    review_mode: bool = False

class ActionDecision(BaseModel):
    action_id: str
    decision: str  # APPROVE, REJECT, CONFIRM, CANCEL
    action_text: str
    rule_key: Optional[str] = None
    rule_desc: Optional[str] = None

@app.get("/favicon.ico", include_in_schema=False)
async def favicon():
    return Response(status_code=204)

@app.post("/api/process")
async def process_orchestration(data: UserPrompt):
    raw_prompt = data.message.strip()
    if len(raw_prompt) < 10 or raw_prompt.lower() in ["handle tomorrow.", "help me"]:
        return {
            "vague": True,
            "user_intent": "Undefined",
            "trace": [{"layer": "1. Intent Engine", "detail": "Vague prompt detected.", "status": "WARNING"}],
            "recommended_actions": [],
            "message": "Please specify what events, tasks, or goals you need managed."
        }

    env = load_mock_environment()
    trace = []

    # 1. Intent Engine
    intent = IntentEngine.parse_intent(raw_prompt)
    trace.append({"layer": "1. Intent Engine", "detail": f"Intent: {intent['primary_intent']} | Entities: {', '.join(intent['entities'])}", "status": "COMPLETED"})

    # 2. Context & Priority Engine
    eval_data = ContextAndPriorityEngine.evaluate(intent, env)
    score_str = ", ".join([f"{k}: {v['score']} ({v['level']})" for k, v in eval_data["scores"].items()])
    trace.append({"layer": "2 & 3. Context, Priority & Conflict Engine", "detail": f"Scores: [{score_str}]. Conflicts: {' '.join(eval_data['conflicts'])}", "status": "COMPLETED"})

    # 4 & 5. Decision Engine with Stateful Memory Loading
    plan = DecisionEngine.resolve_and_plan(intent, eval_data, data.review_mode)
    
    if plan["applied_memory"]:
        for mem_log in plan["applied_memory"]:
            trace.append({"layer": "Adaptive Memory Layer", "detail": mem_log, "status": "MEMORY_APPLIED"})
    else:
        trace.append({"layer": "Adaptive Memory Layer", "detail": "No applicable prior preference found in memory.", "status": "NO_PREFERENCE"})

    trace.append({"layer": "4 & 5. Action & Trust Engine", "detail": f"Generated {len(plan['actions'])} actions with Trust Levels.", "status": "COMPLETED"})

    # Formatted Memory List for UI Display
    formatted_memory = []
    for k, pref in memory.preferences.items():
        if pref["active"]:
            formatted_memory.append({
                "rule_key": k,
                "text": f"{pref['description']}",
                "confidence": pref["confidence"],
                "approvals": pref["approved_count"]
            })

    return {
        "vague": False,
        "user_intent": intent["primary_intent"],
        "trace": trace,
        "recommended_actions": plan["actions"],
        "memory_applied": len(plan["applied_memory"]) > 0,
        "learned_preferences": formatted_memory
    }

@app.post("/api/action-decision")
async def record_action_decision(data: ActionDecision):
    was_approved = data.decision in ["APPROVE", "CONFIRM"]
    
    # Store decision in Adaptive Decision Memory
    if data.rule_key and data.rule_desc:
        memory.learn_preference(data.rule_key, data.rule_desc, was_approved)

    log_status = "Approved & Executed" if was_approved else f"{data.decision}ED"
    log_msg = f"Status: {log_status} | Action: '{data.action_text}'"

    formatted_memory = []
    for k, pref in memory.preferences.items():
        if pref["active"]:
            formatted_memory.append({
                "rule_key": k,
                "text": f"{pref['description']}",
                "confidence": pref["confidence"],
                "approvals": pref["approved_count"]
            })

    return {
        "status": "SUCCESS",
        "log_entry": log_msg,
        "updated_preferences": formatted_memory
    }

@app.post("/api/clear-memory")
async def clear_memory():
    memory.clear()
    return {"status": "SUCCESS", "message": "Learned decision memory reset completely."}

@app.get("/", response_class=HTMLResponse)
async def serve_ui():
    with open("templates/index.html", "r", encoding="utf-8") as f:
        return f.read()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)
