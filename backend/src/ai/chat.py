import json
import ollama
from src.core.schema import CustomerProblemSchema
from typing import List


def extract_final_json(chat_history: List[dict], model_name: str) -> CustomerProblemSchema:
    extraction_prompt = (
        "Based on the conversation above, extract the final problem details into the JSON format. "
        "Infer the category and urgency if the user did not state them explicitly but provided enough context."
    )
    
    payload = chat_history + [{"role": "user", "content": extraction_prompt}]
    
    response = ollama.chat(
        model=model_name,
        messages=payload,
        format=CustomerProblemSchema.model_json_schema(),
        options={"temperature": 0.0} 
    )
    
    return CustomerProblemSchema.model_validate_json(response['message']['content'])

# ==========================================================
# 3. Fast-Track Interactive Loop
# ==========================================================
def run_interactive_interview():
    MODEL_NAME = "qwen2.5:3b" 
    
    # ---------------------------------------------------------
    # NEW SYSTEM PROMPT: Optimized for speed and minimal turns
    # ---------------------------------------------------------
    system_prompt = (
        "You are an ultra-fast dispatch assistant for home repairs. "
        "You need exactly 3 pieces of data: 1. Category (plumbing/electrical/etc.), 2. Details of the problem, 3. Urgency (low/medium/high). "
        "\nRULES FOR SPEED: "
        "\n- Evaluate the user's message instantly. If you can confidently guess all 3 pieces of data from their message (e.g., 'massive water leak' = plumbing + high urgency), DO NOT ask any more questions. Say 'Got it, finding a worker now.' and append '[COMPLETE]'."
        "\n- If data is missing, ask ONE extremely short sentence asking ONLY for the missing information (e.g., 'Is this a low, medium, or high urgency?')."
        "\n- Never offer advice. Keep responses under 15 words if possible."
        "\n- The moment you have enough context for all 3 fields, you MUST end your response with '[COMPLETE]'."
    )
    
    conversation_history = [{"role": "system", "content": system_prompt}]
    
    print("==================================================")
    print(" Fast-Track AI Dispatch Terminal Started")
    print(" Type 'exit' to quit.")
    print("==================================================\n")
    
    # ---------------------------------------------------------
    # NEW INITIAL GREETING: Guide the user to answer in one go
    # ---------------------------------------------------------
    initial_greeting = (
        "Hello! To get a worker to you immediately, please describe the issue in one sentence. "
        "(Tip: Mention what's broken, what's happening, and if it's urgent)."
    )
    print(f"AI: {initial_greeting}")
    conversation_history.append({"role": "assistant", "content": initial_greeting})
    
    while True:
        user_input = input("\nYou: ").strip()
        if not user_input:
            continue
        if user_input.lower() == 'exit':
            print("Exiting...")
            return
            
        conversation_history.append({"role": "user", "content": user_input})
        
        print("AI is evaluating...")
        response = ollama.chat(
            model=MODEL_NAME,
            messages=conversation_history,
            options={"temperature": 0.1} # Lowered temperature for strictly logical evaluation
        )
        
        ai_message = response['message']['content']
        
        if "[COMPLETE]" in ai_message:
            clean_message = ai_message.replace("[COMPLETE]", "").strip()
            print(f"\nAI: {clean_message}")
            conversation_history.append({"role": "assistant", "content": ai_message})
            break
        else:
            print(f"\nAI: {ai_message}")
            conversation_history.append({"role": "assistant", "content": ai_message})

    # ==========================================================
    # 4. Phase 2: Run Extraction Pipeline
    # ==========================================================
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