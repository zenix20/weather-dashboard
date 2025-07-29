from flask import Flask, render_template, request, jsonify
import requests
import os
from dotenv import load_dotenv
from datetime import datetime, timedelta

load_dotenv()   #so we can access API key from .env

#because the index.html is in root folder
app = Flask(__name__, template_folder='.')

#URLs where we will get data
API_KEY = os.getenv('OPENWEATHER_API_KEY')
BASE_URL = "https://api.openweathermap.org/data/2.5/weather"
FORECAST_URL = "https://api.openweathermap.org/data/2.5/forecast"

def fetch_default_weather():
    #get info for Islamabad by default when we open it the first time
    try:
        current_params = {'q': 'Islamabad,Pakistan', 'appid': API_KEY, 'units': 'metric'}
        current_response = requests.get(BASE_URL, params=current_params)
        current_data = current_response.json()
        
        if current_response.status_code != 200:
            raise Exception(current_data.get('message', 'API error'))
            
        weather = {
            'city': current_data['name'],
            'country': current_data['sys']['country'],
            'temp': round(current_data['main']['temp']),
            'feels_like': round(current_data['main']['feels_like']),
            'description': current_data['weather'][0]['description'].title(),
            'humidity': current_data['main']['humidity'],
            'wind_speed': round(current_data['wind']['speed'] * 3.6),
            'pressure': current_data['main']['pressure'],
            'icon': get_icon(current_data['weather'][0]['main'])
        }
        
        forecast_params = {'q': 'Islamabad,Pakistan', 'appid': API_KEY, 'units': 'metric', 'cnt': 24}
        forecast_response = requests.get(FORECAST_URL, params=forecast_params)
        forecast_data = forecast_response.json()
        
        if forecast_response.status_code == 200:
            weather['forecast'] = process_forecast(forecast_data['list'], forecast_data['city']['timezone'])
        else:
            weather['forecast'] = get_fallback_forecast()
            
        return weather
    
    #if there is problem with API, this returns already written fake values for Islamabad
    except Exception as e:
        print(f"Error: {str(e)}")
        return get_fallback_data()

def get_fallback_data():
    return {
        'city': 'Islamabad',
        'country': 'PK',
        'temp': 25,
        'feels_like': 28,
        'description': 'Clear Sky',
        'humidity': 65,
        'wind_speed': 12,
        'pressure': 1013,
        'forecast': get_fallback_forecast()
    }

def get_fallback_forecast():
    return [
        {'day': 'Tomorrow', 'icon': 'sun', 'max_temp': 28, 'min_temp': 18},
        {'day': 'Day 2', 'icon': 'cloud', 'max_temp': 24, 'min_temp': 16},
        {'day': 'Day 3', 'icon': 'cloud-rain', 'max_temp': 22, 'min_temp': 14}
    ]

#when we visit homepage, it loads the index.html with Islamabad's weather data
@app.route('/')
def index():
    default_data = fetch_default_weather()
    return render_template('index.html', weather=default_data)

#when user enters a city, it handles that
@app.route('/search', methods=['POST'])
def search():
    city = request.form.get('city')   #get city name from user input
    if not city:
        return jsonify({'error': 'City name required'}), 400
    
    try:         #call API for the city that user entered
        current_params = {'q': city, 'appid': API_KEY, 'units': 'metric'}
        current_response = requests.get(BASE_URL, params=current_params)
        current_data = current_response.json()
        
        #display error message 
        if current_response.status_code != 200:
            return jsonify({'error': current_data.get('message', 'Weather data error')}), 400

        #pulls weather data for the city    
        weather = {
            'city': current_data['name'],
            'country': current_data['sys']['country'],
            'temp': round(current_data['main']['temp']),
            'feels_like': round(current_data['main']['feels_like']),
            'description': current_data['weather'][0]['description'].title(),
            'humidity': current_data['main']['humidity'],
            'wind_speed': round(current_data['wind']['speed'] * 3.6),
            'pressure': current_data['main']['pressure'],
            'icon': get_icon(current_data['weather'][0]['main'])
        }
        
        #parameter i am sending to API
        forecast_params = {'q': city, 'appid': API_KEY, 'units': 'metric', 'cnt': 24}
        #stores response
        forecast_response = requests.get(FORECAST_URL, params=forecast_params)
        
        #if successful convert response to JSON and store in dictionary or else get fake fallback data
        if forecast_response.status_code == 200:
            weather['forecast'] = process_forecast(forecast_response.json()['list'], current_data['timezone'])
        else:
            weather['forecast'] = get_fallback_forecast()
            
        #return response to frontend
        return jsonify(weather)
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

#to display the forecast information
def process_forecast(forecast_list, timezone_offset):
    daily_forecasts = {}    #group forecasts by date
    for forecast in forecast_list:
        date = datetime.fromtimestamp(forecast['dt'] + timezone_offset).date()
        daily_forecasts.setdefault(date, []).append(forecast)
    
    #display forecast based on today's date
    next_days = [datetime.now().date() + timedelta(days=i) for i in range(1, 4)]  
    
    result = []
    for i, day in enumerate(next_days):
        if day not in daily_forecasts:
            continue
            
        day_forecasts = daily_forecasts[day]
        temps = [f['main']['temp'] for f in day_forecasts]
        conditions = [f['weather'][0]['main'] for f in day_forecasts]
        
        result.append({
            'day': ['Tomorrow', 'Day 2', 'Day 3'][i],
            'icon': get_icon(max(set(conditions), key=conditions.count)),
            'max_temp': round(max(temps)),
            'min_temp': round(min(temps))
        })
    
    return result

#match weather icons to names
def get_icon(weather_condition):
    icons = {
        'Clear': 'sun', 'Clouds': 'cloud', 'Rain': 'cloud-rain',
        'Thunderstorm': 'bolt', 'Snow': 'snowflake', 'Mist': 'smog',
        'Smoke': 'smog', 'Haze': 'smog', 'Dust': 'smog', 'Fog': 'smog'
    }
    return icons.get(weather_condition, 'cloud')

if __name__ == '__main__':
    app.run(debug=True)