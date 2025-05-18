import os
import google.generativeai as genai
import re
from datetime import datetime
from google.cloud import translate_v2 as translate
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

def setup_gemini():
    """Configure Gemini API with the provided key"""
    # Get API key from environment variable
    api_key = os.getenv('GEMINI_API_KEY')
    
    if not api_key:
        raise ValueError("GEMINI_API_KEY environment variable is not set. Please set your Gemini API key.")
    
    genai.configure(api_key=api_key)

    generation_config = {
        "temperature": 0.7,
        "top_p": 0.95,
        "top_k": 40,
        "max_output_tokens": 2048,
    }

    return genai.GenerativeModel(
        model_name="gemini-1.5-pro",
        generation_config=generation_config,
    )

def setup_translation_client():
    """Set up Google Translate API client"""
    # Get credentials file path from environment variable
    credentials_path = os.getenv('GOOGLE_APPLICATION_CREDENTIALS')
    
    if not credentials_path:
        raise ValueError("GOOGLE_APPLICATION_CREDENTIALS environment variable is not set. Please set the path to your credentials file.")
    
    return translate.Client()

def clean_response(response_text):
    """Clean the response to remove unnecessary text"""
    cleaned = re.sub(r'\[.*?\]', '', response_text)  # Remove square bracket content
    cleaned = cleaned.split("Suggested responses")[0] if "Suggested responses" in cleaned else cleaned
    return " ".join(cleaned.split()).strip()  # Clean up whitespace

def get_greeting():
    """Generate a greeting based on the time of day."""
    hour = datetime.now().hour
    if hour < 12:
        return "Good morning!"
    elif 12 <= hour < 18:
        return "Good afternoon!"
    else:
        return "Good evening!"

def translate_text(client, text, target_language='en'):
    """Translate the given text to the target language"""
    if target_language.lower() == 'en':
        return text
    try:
        result = client.translate(text, target_language=target_language)
        return result["translatedText"]
    except Exception as e:
        print(f"Translation error: {str(e)}")
        return text

def handle_clarification(user_input):
    """Provide clarifications for unclear input."""
    clarifications = [
        "I didn't quite catch that. Are you asking about a specific route or schedule?",
        "Could you rephrase or provide more details?",
        "I'm here to help! Are you looking for ticket prices or directions?"
    ]
    return clarifications[hash(user_input) % len(clarifications)]

def validate_language_code(code):
    """Validate if the language code is in the correct format"""
    return bool(re.match(r'^[a-z]{2}(-[A-Z]{2})?$', code))

def run_transportation_conversation():
    """Main function to run the transportation guide conversation"""
    try:
        print("Initializing transportation guide...")
        model = setup_gemini()
        translation_client = setup_translation_client()

        # Define the context for the conversation
        context = """You are a helpful and friendly public transportation guide. 
        Assist the customer in understanding directions, routes, ticket types, and schedules. 
        Provide clear and simple responses to their questions about public transport. 
        Here is some example data you can use in your responses:

        - Routes:
            1. Bus 101: Downtown to Central Park (Every 15 minutes)
            2. Train A: Airport to City Center (Every 30 minutes)
            3. Bus 202: University to Shopping Mall (Every 20 minutes)

        - Ticket Prices:
            - Single Ride: $2.50
            - Day Pass: $7.00
            - Weekly Pass: $25.00

        Include helpful suggestions about nearby landmarks when giving directions."""

        # Start chat and initialize with context
        chat = model.start_chat(history=[])
        chat.send_message(context)

        while True:
            preferred_language = input("\nPlease enter your preferred language code (e.g., fr for French, es for Spanish, en for English): ").strip().lower()
            
            if preferred_language == 'en' or validate_language_code(preferred_language):
                break
            print("Invalid language code. Please use format like 'en', 'fr', 'es', etc.")

        print(f"\nGuide: {get_greeting()} How can I assist you with public transportation today?")

        while True:
            user_input = input("\nYou: ").strip()

            if not user_input:
                print("\nGuide: I didn't quite catch that. Could you please repeat?")
                continue

            if user_input.lower() in ['goodbye', 'exit', 'quit', 'bye']:
                farewell = "Thank you for using our transportation guide! Have a safe journey!"
                translated_farewell = translate_text(translation_client, farewell, preferred_language)
                print(f"\nGuide: {translated_farewell}")
                break

            try:
                # Translate user input to English if necessary
                user_input_translated = translate_text(translation_client, user_input, 'en')

                # Get response from Gemini model
                response = chat.send_message(f"Customer: {user_input_translated}\nRespond naturally without showing instructions or context.")
                
                if response and hasattr(response, 'text'):
                    cleaned_response = clean_response(response.text)

                    if not cleaned_response or "I didn't quite understand" in cleaned_response:
                        clarification = handle_clarification(user_input)
                        translated_clarification = translate_text(translation_client, clarification, preferred_language)
                        print(f"\nGuide: {translated_clarification}")
                    else:
                        translated_response = translate_text(translation_client, cleaned_response, preferred_language)
                        if preferred_language != 'en':
                            print(f"\nGuide: {translated_response}")
                            print(f"(English: {cleaned_response})")
                        else:
                            print(f"\nGuide: {cleaned_response}")
                else:
                    clarification = handle_clarification(user_input)
                    translated_clarification = translate_text(translation_client, clarification, preferred_language)
                    print(f"\nGuide: {translated_clarification}")

            except Exception as e:
                print(f"\nGuide: I apologize for the technical difficulty. Error: {str(e)}")
                print("How else can I help you today?")

    except Exception as e:
        print(f"\nSystem Error: {str(e)}")
        print("\nPlease ensure you have:")
        print("1. Installed required packages: pip install google-generativeai google-cloud-translate python-dotenv")
        print("2. Set up your .env file with GEMINI_API_KEY and GOOGLE_APPLICATION_CREDENTIALS")
        print("3. Valid API keys and credentials for both services")

if __name__ == "__main__":
    run_transportation_conversation()