import os
import google.generativeai as genai
import re
from datetime import datetime
from google.cloud import translate_v2 as translate

def setup_gemini():
    """Configure Gemini API with the provided key"""
    genai.configure(api_key="AIzaSyC7-YhQoMLVhx2J_S_U_bnp917sqoEZ-JI")

    generation_config = {
        "temperature": 0.5,  # Lower temperature for concise and focused responses
        "top_p": 0.8,       # Encourage higher confidence tokens
        "top_k": 20,        # Smaller range of token selection
        "max_output_tokens": 200,  # Adjust response length for meaningful sentences
    }

    return genai.GenerativeModel(
        model_name="gemini-1.0-pro",
        generation_config=generation_config,
    )

def setup_translation_client():
    """Set up Google Translate API client"""
    return translate.Client.from_service_account_json("gen-lang-client-0182388257-027b6c8204af.json")

def clean_response(response_text):
    """Clean the response to ensure brevity and relevance"""
    cleaned = re.sub(r'\[.*?\]', '', response_text)  # Remove square bracket content
    cleaned = cleaned.split("Suggested responses")[0] if "Suggested responses" in cleaned else cleaned
    cleaned = re.sub(r'Guide:?|Shopkeeper:?|\*+', '', cleaned)  # Remove roles and asterisks
    cleaned = " ".join(cleaned.split()).strip()  # Clean up whitespace
    return cleaned  # Allow full meaningful response

def get_greeting():
    """Generate a greeting based on the time of day."""
    hour = datetime.now().hour
    if hour < 12:
        return "Good morning!"
    elif 12 <= hour < 18:
        return "Good afternoon!"
    else:
        return "Good evening!"

def translate_text(client, text, target_language):
    """Translate the given text to the target language"""
    result = client.translate(text, target_language=target_language)
    return result["translatedText"]

def handle_clarification(user_input):
    """Provide clarifications for unclear input."""
    clarifications = [
        "Could you clarify your request?",
        "Can you rephrase that?",
        "Let me know more details!"
    ]
    return clarifications[hash(user_input) % len(clarifications)]

def run_transport_guide():
    try:
        model = setup_gemini()
        translation_client = setup_translation_client()

        # Define the context for the conversation with the role of Teacher
        context = """ You are a caring and insightful teacher.  
Assist the parent in understanding their child’s progress, behavior, and involvement in school activities.  
Provide clear, constructive feedback and helpful suggestions. Use the example below to guide your tone and style:

- Example Interaction:
    Parent: "How is my child doing in math?"
    Response: "Your child is improving steadily in math, especially in problem-solving. They could benefit from additional practice with fractions, which we’re focusing on this term."

- Key Topics:
    - Academic Subjects: Strengths, areas for improvement.
    - Behavior: Participation, discipline, social interactions.
    - School Activities: Events, extracurricular participation.
    - Feedback: Constructive and specific advice for improvement.

Respond in a calm, supportive tone, ensuring your feedback is clear and actionable """

        # Start chat and initialize with context
        chat = model.start_chat(history=[])
        chat.send_message(context)

        preferred_language = input("Please enter your preferred language (e.g., fr for French, es for Spanish): ").strip()

        print(f"\nTeacher: {get_greeting()} Welcome! How can I assist you today?")

        while True:
            user_input = input("\nYou: ").strip()

            if not user_input:
                print("\nTeacher: Could you repeat that?")
                continue

            if user_input.lower() in ['goodbye', 'exit', 'quit']:
                print("\nTeacher: Thanks for visiting! Have a great day!")
                break

            try:
                # Translate user input to English if necessary
                user_input_translated = translate_text(translation_client, user_input, 'en')

                # Get response from Gemini model
                response = chat.send_message(f"Customer: {user_input_translated}")

                if response and hasattr(response, 'text'):
                    cleaned_response = clean_response(response.text)

                    if not cleaned_response:
                        clarification = handle_clarification(user_input)
                        translated_clarification = translate_text(translation_client, clarification, preferred_language)
                        print(f"\nTeacher: {translated_clarification}")
                        print(f"(English: {clarification})")
                    else:
                        translated_response = translate_text(translation_client, cleaned_response, preferred_language)
                        user_input_translated_back = translate_text(translation_client, user_input, preferred_language)
                        print(f"\nYou (Translated): {user_input_translated_back}")
                        print(f"\nTeacher: {translated_response}")
                        print(f"(English: {cleaned_response})")
                else:
                    clarification = handle_clarification(user_input)
                    translated_clarification = translate_text(translation_client, clarification, preferred_language)
                    print(f"\nTeacher: {translated_clarification}")
                    print(f"(English: {clarification})")

            except Exception as e:
                print("\nTeacher: Sorry, something went wrong. How else can I help?")

    except Exception as e:
        print(f"System Error: {str(e)}")
        print("Please ensure the required packages and API keys are set up correctly.")

if __name__ == "__main__":
    run_transport_guide()
