import os
import google.generativeai as genai
import re
from datetime import datetime
from google.cloud import translate_v2 as translate
from google.auth.exceptions import RefreshError


def setup_gemini():
    """Configure Gemini API with the provided key for Gemini 1.5 Flash"""
    genai.configure(api_key="AIzaSyCEcF63Q7SpN7PJBJxPLKRZSGPhTq0Bbz8")
    generation_config = {
        "temperature": 0.7,
        "top_p": 0.95,
        "top_k": 40,
        "max_output_tokens": 2048,
    }

    return genai.GenerativeModel(
        model_name="gemini-1.5-flash",
        generation_config=generation_config,
    )


def setup_translation_client():
    """Set up Google Translate API client"""
    return translate.Client.from_service_account_json("gen-lang-client-0182388257-566babb95209.json")


def clean_response(response_text):
    """Clean the response to remove unnecessary text"""
    cleaned = re.sub(r'\[.*?\]', '', response_text)  # Remove square bracket content
    cleaned = cleaned.split("Suggested responses")[0] if "Suggested responses" in cleaned else cleaned
    cleaned = re.sub(r'Shopkeeper:?', '', cleaned)  # Remove 'Shopkeeper:' text
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


def translate_text(client, text, target_language):
    """Translate the given text to the target language"""
    result = client.translate(text, target_language=target_language)
    return result["translatedText"]


def handle_clarification(user_input):
    """Provide clarifications for unclear input."""
    clarifications = [
        "I didn’t quite catch that. Are you asking about a specific item or price?",
        "Could you rephrase or provide more details?",
        "I’m here to help! Can you let me know what you’re looking for?"
    ]
    return clarifications[hash(user_input) % len(clarifications)]


def run_grocery_conversation():
    try:
        model = setup_gemini()
        translation_client = setup_translation_client()

        # Define the context for the conversation
        context = """You are a friendly and knowledgeable grocery store shopkeeper. 
        Help customers with their queries, suggest related items, and ensure they have a pleasant experience. 
        Here's your inventory with prices:
        
        - Fresh Tomatoes ($2.99/lb)
        - Lettuce ($2.49/head)
        - Carrots ($1.99/lb)
        - Cucumbers ($1.49 each)
        - Apples ($1.99/lb)
        - Bananas ($0.59/lb)
        - Oranges ($2.49/lb)
        - Fresh Herbs ($1.99/bunch)

        Suggest related items when appropriate. Keep your tone friendly and conversational."""

        # Start chat and initialize with context
        chat = model.start_chat(history=[])
        chat.send_message(context)

        preferred_language = input("Please enter your preferred language (e.g., fr for French, es for Spanish): ").strip()

        print(f"\nShopkeeper: {get_greeting()} Welcome to our neighborhood grocery store. How can I help you today?")

        while True:
            user_input = input("\nYou: ").strip()

            if not user_input:
                print("\nShopkeeper: I didn't quite catch that. Could you please repeat?")
                continue

            if user_input.lower() in ['goodbye', 'exit', 'quit']:
                print("\nShopkeeper: Thank you for visiting! Have a wonderful day!")
                break

            try:
                # Translate user input to English if necessary
                user_input_translated = translate_text(translation_client, user_input, 'en')

                # Translate user message back to their preferred language for confirmation
                user_input_confirmed = translate_text(translation_client, user_input_translated, preferred_language)
                print(f"\nTranslated user Text: {user_input_confirmed}")

                # Get response from Gemini model
                response = chat.send_message(f"Customer: {user_input_translated}\nRespond naturally without showing instructions or context.")
                if response and hasattr(response, 'text'):
                    cleaned_response = clean_response(response.text)

                    if not cleaned_response or "I didn't quite understand" in cleaned_response:
                        clarification = handle_clarification(user_input)
                        translated_clarification = translate_text(translation_client, clarification, preferred_language)
                        print(f"\nShopkeeper: {translated_clarification} \n (English: {clarification})")
                    else:
                        translated_response = translate_text(translation_client, cleaned_response, preferred_language)
                        print(f"\nShopkeeper: {translated_response}  \n (English: {cleaned_response})")
                else:
                    clarification = handle_clarification(user_input)
                    translated_clarification = translate_text(translation_client, clarification, preferred_language)
                    print(f"\nShopkeeper: {translated_clarification} \n (English: {clarification})")

            except RefreshError as e:
                print(f"Authentication Error: {str(e)}")
                print("Please verify your API key and service account credentials.")
                break
            except Exception as e:
                print(f"An error occurred: {str(e)}")
                break

    except Exception as e:
        print(f"System Error: {str(e)}")
        print("Ensure the `google-generativeai` and `google-cloud-translate` packages are installed and valid API keys are configured.")


if __name__ == "__main__":
    run_grocery_conversation()
