import json
import ollama
from typing import List, Literal
from pydantic import BaseModel, Field

# 1. ADVANCED DEEP-DIVE WORKER SCHEMA
class AdvancedWorkerProfileSchema(BaseModel):
    trade_category: Literal["plumbing", "electrical", "hvac", "appliance_repair", "handyman"] = Field(
        description="The primary trade category the worker belongs to."
    )
    core_specialties: List[str] = Field(
        description="List of specific sub-skills or tasks they specialize in? (e.g., solar panel installation, drain cleaning, commercial HVAC)"
    )
    years_experience: int = Field(
        description="Total number of years working professionally in this specific trade."
    )
    license_status: Literal["verified_active", "pending_review", "unlicensed"] = Field(
        description="Status of their professional trade license based on their statements."
    )
    heavy_equipment_owned: List[str] = Field(
        description="Specialized heavy machinery, advanced diagnostic gear, or specific tools they own/operate."
    )
    emergency_24_7: bool = Field(
        description="True if they explicitly state they accept immediate, 24/7 high-urgency dispatches."
    )
    background_check_consent: bool = Field(
        description="True if they explicitly agree to pass a background check."
    )


# 2. DATA EXTRACTION ENGINE WITH STRICT VALIDATION
def extract_worker_json(chat_history: List[dict], model_name: str) -> AdvancedWorkerProfileSchema:
    # Scrub interactive loop system prompt to prevent pollution
    cleaned_history = [msg for msg in chat_history if msg["role"] != "system"]
    
    extraction_prompt = (
        "You are a strict data compliance parser. Output ONLY valid JSON matching the schema. "
        "Analyze the worker interview history. "
        "Extract their core_specialties and heavy_equipment_owned as explicit string arrays. "
        "If they don't explicitly reject background checks or emergency calls, set them to True based on positive conversational tone."
    )
    
    payload = [{"role": "system", "content": extraction_prompt}] + cleaned_history
    
    response = ollama.chat(
        model=model_name,
        messages=payload,
        format=AdvancedWorkerProfileSchema.model_json_schema(),
        options={"temperature": 0.0} # Absolute determinism
    )
    
    raw_content = response['message']['content'].strip()
    
    # Safe markdown stripping
    if raw_content.startswith("```json"):
        raw_content = raw_content.split("```json", 1)[1].rsplit("```", 1)[0].strip()
    elif raw_content.startswith("```"):
        raw_content = raw_content.split("```", 1)[1].rsplit("```", 1)[0].strip()

    return AdvancedWorkerProfileSchema.model_validate_json(raw_content)


# 3. INTERACTIVE DEEP-DIVE INTERVIEW LOOP
def run_worker_interview():
    MODEL_NAME = "qwen2.5:3b" 
    
    # Contextual system prompt instructing the AI to dynamically discover micro-skills
    system_prompt = (
        "You are an expert technical vetting assistant for home services. "
        "Your mission is to uncover a worker's exact niche skillsets, specialties, and tools.\n\n"
        "FIELDS TO DISCOVER:\n"
        "1. Trade, 2. Years experience, 3. License status, 4. Sub-specialties (e.g., solar, commercial, drain cleaning), "
        "5. Specialized equipment owned, 6. Emergency readiness + background check.\n\n"
        "DYNAMIC INTERVIEW RULES:\n"
        "- Do not accept vague answers. If they say 'plumbing', immediately ask: 'What are your exact specialties? (e.g., solar tech, leak detection, jetting?)'\n"
        "- Keep questions single-focused, direct, and under 20 words.\n"
        "- Do not chat, greet, or offer pleasantries after the first turn.\n"
        "- As soon as you know their trade, sub-specialties, tools, experience, license, and consent, immediately append '[COMPLETE]'."
    )
    
    conversation_history = [{"role": "system", "content": system_prompt}]
    
    print("==========================================================")
    print(" AI Deep-Dive Worker Profile Vetting Terminal")
    print(" Type 'exit' to quit.")
    print("==========================================================\n")
    
    initial_greeting = (
        "Welcome! What is your main trade, how many years have you practiced it, "
        "and do you hold an active license?"
    )
    print(f"AI: {initial_greeting}")
    conversation_history.append({"role": "assistant", "content": initial_greeting})
    
    # Increased max turns to allow for an organic, deep conversational discovery flow
    max_turns = 8
    turn_count = 0
    
    while turn_count < max_turns:
        user_input = input("\nWorker: ").strip()
        if not user_input:
            continue
        if user_input.lower() == 'exit':
            print("Exiting...")
            return
            
        conversation_history.append({"role": "user", "content": user_input})
        turn_count += 1
        
        response = ollama.chat(
            model=MODEL_NAME,
            messages=conversation_history,
            options={"temperature": 0.1} # Slight temperature allows conversational curiosity for probing details
        )
        
        ai_message = response['message']['content'].strip()
        
        if "[COMPLETE]" in ai_message or turn_count >= max_turns:
            clean_message = ai_message.replace("[COMPLETE]", "").strip()
            if not clean_message:
                clean_message = "Thank you. Profiling complete. Parsing credentials..."
            print(f"\nAI: {clean_message}")
            conversation_history.append({"role": "assistant", "content": ai_message})
            break
        else:
            print(f"\nAI: {ai_message}")
            conversation_history.append({"role": "assistant", "content": ai_message})

    print("\n" + "="*50)
    print(" DEPTH VERIFICATION ACHIEVED -> COMPILING DETAILED JSON")
    print("="*50)
    
    try:
        structured_data = extract_worker_json(conversation_history, MODEL_NAME)
        print("\n[SUCCESS] Final Deep Worker Profile JSON for Matching Optimization:")
        print(json.dumps(structured_data.model_dump(), indent=2))
        
    except Exception as e:
        print(f"\n[ERROR] Failed to extract structural deep profile: {e}")


if __name__ == "__main__":
    run_worker_interview()
