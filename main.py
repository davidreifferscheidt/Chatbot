import json
import os
from datetime import datetime, timedelta

import google.generativeai as genai
import requests

# Configure Gemini
genai.configure(api_key=os.environ["GEMINI_API_KEY"])
model = genai.GenerativeModel("gemini-pro")

# Meteoblue pictocode meanings
PICTOCODE_MEANINGS = {
    1: "Clear, cloudless sky",
    2: "Clear, few cirrus",
    3: "Clear with cirrus",
    4: "Clear with few low clouds",
    5: "Clear with few low clouds and few cirrus",
    6: "Clear with few low clouds and cirrus",
    7: "Partly cloudy",
    8: "Partly cloudy and few cirrus",
    9: "Partly cloudy and cirrus",
    10: "Mixed with some thunderstorm clouds possible",
    11: "Mixed with few cirrus with some thunderstorm clouds possible",
    12: "Mixed with cirrus and some thunderstorm clouds possible",
    13: "Clear but hazy",
    14: "Clear but hazy with few cirrus",
    15: "Clear but hazy with cirrus",
    16: "Fog/low stratus clouds",
    17: "Fog/low stratus clouds with few cirrus",
    18: "Fog/low stratus clouds with cirrus",
    19: "Mostly cloudy",
    20: "Mostly cloudy and few cirrus",
    21: "Mostly cloudy and cirrus",
    22: "Overcast",
    23: "Overcast with rain",
    24: "Overcast with snow",
    25: "Overcast with heavy rain",
    26: "Overcast with heavy snow",
    27: "Rain, thunderstorms likely",
    28: "Light rain, thunderstorms likely",
    29: "Storm with heavy snow",
    30: "Heavy rain, thunderstorms likely",
    31: "Mixed with showers",
    32: "Mixed with snow showers",
    33: "Overcast with light rain",
    34: "Overcast with light snow",
    35: "Overcast with mixture of snow and rain",
}


def geocode_location(location):
    url = f"https://api.opencagedata.com/geocode/v1/json?q={location}&key={os.environ['OPENCAGE_API_KEY']}"
    response = requests.get(url)
    data = response.json()
    if data["results"]:
        lat = data["results"][0]["geometry"]["lat"]
        lon = data["results"][0]["geometry"]["lng"]
        return lat, lon
    return None, None


def get_weather_data(lat, lon, date):
    url = f"https://my.meteoblue.com/packages/basic-day?apikey={os.environ['METEOBLUE_API_KEY']}&lat={lat}&lon={lon}&format=json"
    response = requests.get(url)
    data = response.json()

    # Find the index for the requested date
    target_date = datetime.strptime(date, "%Y-%m-%d").date()
    today = datetime.now().date()
    days_difference = (target_date - today).days

    if 0 <= days_difference < 7:  # Meteoblue provides 7 days forecast
        day_data = {
            key: data["data_day"][key][days_difference] for key in data["data_day"]
        }
        return {
            "date": day_data["time"],
            "temperature_max": day_data["temperature_max"],
            "temperature_min": day_data["temperature_min"],
            "temperature_mean": day_data["temperature_mean"],
            "felttemperature_max": day_data["felttemperature_max"],
            "felttemperature_min": day_data["felttemperature_min"],
            "precipitation": day_data["precipitation"],
            "precipitation_probability": day_data["precipitation_probability"],
            "windspeed_mean": day_data["windspeed_mean"],
            "winddirection": day_data["winddirection"],
            "pictocode": day_data["pictocode"],
            "uvindex": day_data["uvindex"],
            "relativehumidity_mean": day_data["relativehumidity_mean"],
        }
    else:
        return None


def process_user_query(query):
    prompt = f"""
    Extract the location and date from the following weather-related query. 
    If no specific date is mentioned, assume it's for today.
    Query: {query}
    Return the result like this:
    {{
        "location": "extracted location",
        "date": "extracted date in YYYY-MM-DD format"
    }}
    """

    response = model.generate_content(prompt)
    result = response.text

    extracted_info = json.loads(result)
    if extracted_info["date"] == "today":
        extracted_info["date"] = datetime.now().date().strftime("%Y-%m-%d")
    return extracted_info["location"], extracted_info["date"]


def generate_response(weather_data, location):
    weather_condition = PICTOCODE_MEANINGS.get(
        weather_data["pictocode"], "Unknown weather condition"
    )

    prompt = f"""
    Analyze the following weather data and generate a detailed, natural language response:
    
    Location: {location}
    Date: {weather_data['date']}
    Weather Condition: {weather_condition}
    Temperature:
      - Max: {weather_data['temperature_max']}°C
      - Min: {weather_data['temperature_min']}°C
      - Mean: {weather_data['temperature_mean']}°C
    Felt Temperature:
      - Max: {weather_data['felttemperature_max']}°C
      - Min: {weather_data['felttemperature_min']}°C
    Precipitation: {weather_data['precipitation']} mm
    Precipitation Probability: {weather_data['precipitation_probability']}%
    Wind:
      - Speed: {weather_data['windspeed_mean']} m/s
      - Direction: {weather_data['winddirection']}°
    UV Index: {weather_data['uvindex']}
    Relative Humidity: {weather_data['relativehumidity_mean']}%

    Provide a comprehensive weather report that includes:
    1. A summary of the overall weather condition
    2. Temperature analysis, including how it might feel
    3. Precipitation forecast and probability
    4. Wind conditions and what they mean for the day
    5. UV index interpretation and sun protection advice if needed
    6. Any notable weather patterns or changes

    The response should be friendly, informative, and easy to understand for the general public.
    """

    response = model.generate_content(prompt)
    return response.text


if __name__ == "__main__":
    print("Welcome to the Enhanced Weather Chatbot!")
    print("You can ask questions like: 'What's the weather in Munich on 2024-09-30?'")
    print("Type 'exit' to quit.")

    while True:
        user_input = input("You: ")
        if user_input.lower() == "exit":
            print("Goodbye!")
            break

        try:
            location, date = process_user_query(user_input)
            if location and date:
                lat, lon = geocode_location(location)
                if lat and lon:
                    weather_data = get_weather_data(lat, lon, date)
                    if weather_data:
                        response = generate_response(weather_data, location)
                        print(f"Chatbot: {response}")
                    else:
                        print(
                            f"Chatbot: I'm sorry, I couldn't get weather data for {location} on {date}. The date might be out of range."
                        )
                else:
                    print(
                        f"Chatbot: I'm sorry, I couldn't find the coordinates for {location}."
                    )
            else:
                print(
                    "Chatbot: I'm sorry, I couldn't understand the location or date in your query. Can you please rephrase?"
                )
        except Exception as e:
            print(f"Chatbot: I'm sorry, I encountered an error: {str(e)}")
