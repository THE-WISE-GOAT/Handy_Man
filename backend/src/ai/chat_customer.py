import json
import ollama
from src.core.schema import CustomerProblemSchema
from typing import List


def extract_final_json(chat_history: List[dict], model_name: str) -> CustomerProblemSchema:
    # 1. REMOVE the interactive loop's system prompt so it doesn't pollute extraction logic
    cleaned_history = [msg for msg in chat_history if msg["role"] != "system"]
    
    extraction_prompt = (
        "You are a strict data-extraction engine. Output ONLY valid JSON matching the schema. "
        "Based on the conversation above, extract the final problem details. "
        "Infer the category and urgency if they are not stated explicitly but provided enough context."
    )
    
    # Construct an unpolluted payload specific to extraction task
    payload = [{"role": "system", "content": extraction_prompt}] + cleaned_history
    
    response = ollama.chat(
        model=model_name,
        messages=payload,
        format=CustomerProblemSchema.model_json_schema(),
        options={"temperature": 0.0}  # Hard deterministic zero out
    )
    
    raw_content = response['message']['content'].strip()
    
    # 2. STRIP potential LLM markdown artifacts safely before Pydantic parsing
    if raw_content.startswith("```json"):
        raw_content = raw_content.split("```json", 1)[1].rsplit("```", 1)[0].strip()
    elif raw_content.startswith("```"):
        raw_content = raw_content.split("```", 1)[1].rsplit("```", 1)[0].strip()

    return CustomerProblemSchema.model_validate_json(raw_content)


def run_interactive_interview():
    MODEL_NAME = "qwen2.5:3b" 
    
    system_prompt = (
        "You are an ultra-fast dispatch assistant for home repairs. "
        "You need exactly 3 pieces of data: 1. Category (plumbing/electrical/etc.), "
        "2. Details of the problem, 3. Urgency (low/medium/high).\n\n"
        "RULES FOR SPEED:\n"
        "- Evaluate the user's message instantly. If you can confidently guess all 3 pieces "
        "of data from their message (e.g., 'massive water leak' = plumbing + high urgency), "
        "DO NOT ask any more questions. Say 'Got it, finding a worker now.' and append '[COMPLETE]'.\n"
        "- If data is missing, ask ONE extremely short sentence asking ONLY for the missing information.\n"
        "- Never offer advice. Keep responses under 15 words.\n"
        "- The moment you have enough context for all 3 fields, you MUST end your response with '[COMPLETE]'."
    )
    
    conversation_history = [{"role": "system", "content": system_prompt}]
    
    print("==================================================")
    print(" Fast-Track AI Dispatch Terminal Started")
    print(" Type 'exit' to quit.")
    print("==================================================\n")
    
    initial_greeting = (
        "Hello! To get a worker to you immediately, please describe the issue in one sentence. "
        "(Tip: Mention what's broken, what's happening, and if it's urgent)."
    )
    print(f"AI: {initial_greeting}")
    conversation_history.append({"role": "assistant", "content": initial_greeting})
    
    # Define max safe conversation turns to prevent infinite loops on small models
    max_turns = 6
    turn_count = 0
    
    while turn_count < max_turns:
        user_input = input("\nYou: ").strip()
        if not user_input:
            continue
        if user_input.lower() == 'exit':
            print("Exiting...")
            return
            
        conversation_history.append({"role": "user", "content": user_input})
        turn_count += 1
        
        print("AI is evaluating...")
        response = ollama.chat(
            model=MODEL_NAME,
            messages=conversation_history,
            options={"temperature": 0.0} # Absolute zero temperature for strict instruction adherence
        )
        
        ai_message = response['message']['content'].strip()
        
        # 3. ROBUST MATCHING: Accommodate small models missing strict spacing formatting
        if "[COMPLETE]" in ai_message or turn_count >= max_turns:
            clean_message = ai_message.replace("[COMPLETE]", "").strip()
            if not clean_message:
                clean_message = "Got it, processing your request now."
            print(f"\nAI: {clean_message}")
            conversation_history.append({"role": "assistant", "content": ai_message})
            break
        else:
            print(f"\nAI: {ai_message}")
            conversation_history.append({"role": "assistant", "content": ai_message})

    print("\n" + "="*50)
    print(" SUFFICIENT DATA GATHERED -> EXTRACTING JSON")
    print("="*50)
    
    try:
        structured_data = extract_final_json(conversation_history, MODEL_NAME)
        print("\n[SUCCESS] Final Payload for Database & Matching Engine:")
        print(json.dumps(structured_data.model_dump(), indent=2))
        
    except Exception as e:
        print(f"\n[ERROR] Failed to extract structural data: {e}")


if __name__ == "__main__":
    run_interactive_interview()
