from django.shortcuts import render
from django.shortcuts import render,redirect
from django.contrib.auth.models import User
from django.contrib import messages
from django.contrib.auth import login ,logout,authenticate
from django.shortcuts import get_object_or_404
import json
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_exempt
from .models import NutritionImage
# Create your views here.
def home(request):
    return render(request,'home.html')
def register(request):
    if request.method == 'POST':
        name = request.POST['name']
        email = request.POST['email']
        password = request.POST['password']
        confirmation_password = request.POST['confirm_password']
        if password == confirmation_password:
            if User.objects.filter(username=email).exists():
                messages.error(request, 'Username already exists, please choose a different one.')
                return redirect('register')
            else:
                if User.objects.filter(email=email).exists():
                    messages.error(request, 'Email already exists, please choose a different one.')
                    return redirect('register')
                else:
                    user = User.objects.create_user(
                        username=email,
                        password=password,
                        email=email,
                        first_name=name,
                    )
                    user.save()
                    return redirect('login')
        else:
            messages.error(request, 'Passwords do not match.')
        return render(request, 'signup.html')
    return render(request, 'signup.html')

def login_view(request):
    if request.method == "POST":
        username = request.POST.get('username')
        password = request.POST.get('password')
        if User.objects.filter(username=username).exists():
            user=User.objects.get(username=username)
            if user.check_password(password):
                user = authenticate(username=username,password=password)
                if user is not None:
                    login(request,user)
                    messages.success(request,'login successfull')
                    return redirect('/')
                else:
                   messages.error(request,'please check the Password Properly')
                   return redirect('login')
            else:
                messages.error(request,"please check the Password Properly")  
                return redirect('login') 
        else:
            messages.error(request,"Email doesn't exist")
            return redirect('login')
    return render(request,'login.html')
# Load and preprocess the dataset
def logout_view(request):
    logout(request)
    return redirect('login')


def dashboard(request):
    images = NutritionImage.objects.filter(user=request.user)
    return render(request, "dashboard.html", {"images": images})


import os
import requests
import base64
import re
def analyze_food_nutrition(image_path, api_key):
    try:
        if not os.path.exists(image_path):
            return json.dumps({"error": "File not found"})
        
        with open(image_path, "rb") as image_file:
            image_data = base64.b64encode(image_file.read()).decode("utf-8")

        if not api_key:
            return json.dumps({"error": "API key is missing"})

        url = f"https://generativelanguage.googleapis.com/v1/models/gemini-1.5-flash:generateContent?key={api_key}"
        payload = {
            "contents": [
                {
                    "role": "user",
                    "parts": [
                        {"inlineData": {"mimeType": "image/jpeg", "data": image_data}},
                        {"text": (
                            "Analyze the dish in the image and provide its name and nutritional breakdown per 100 grams in JSON format. "
                            "Ensure the output is strictly in JSON format with a list of dictionaries, each with keys: 'Nutrient', 'Value', and 'Unit'. "
                            "Add the dish name as the first element in the list, where Nutrient is 'Dish Name', value is the name itself and unit is null. "
                            "Return only the JSON response with no extra text."
                        )}
                    ]
                }
            ]
        }
        
        headers = {"Content-Type": "application/json"}
        response = requests.post(url, json=payload, headers=headers)
        response.raise_for_status()
        
        response_json = response.json()
        text_response = response_json.get("candidates", [{}])[0].get("content", {}).get("parts", [{}])[0].get("text", "")
        
        if not text_response:
            return json.dumps({"error": "No valid response from API"})
        
        # Extract JSON from text response more reliably
        json_matches = re.findall(r'\[.*?\]', text_response, re.DOTALL)
        if not json_matches:
            return json.dumps({"error": "Failed to extract JSON from API response"})
        
        try:
          raw_nutrition_data = json.loads(json_matches[0])
        except json.JSONDecodeError:
          return json.dumps({"error": "Invalid JSON format in API response"})

        # Validate that the response is a list of dictionaries with the correct keys
        if not isinstance(raw_nutrition_data, list) or not all(isinstance(item, dict) and "Nutrient" in item and "Value" in item and "Unit" in item for item in raw_nutrition_data):
            return json.dumps({"error": "Invalid JSON format: expected list of dictionaries with 'Nutrient', 'Value', and 'Unit' keys"})

        return json.dumps(raw_nutrition_data, indent=4)
    
    except requests.exceptions.RequestException as e:
        return json.dumps({"error": f"API request failed: {e}"})
    except json.JSONDecodeError:
        return json.dumps({"error": "Invalid JSON format in API response"})
import tempfile
import pandas as pd
def check_nutritions(request):
    apikey ='AIzaSyBpLetJX8VwYq3QHc_icj9po2DWiQRqMdY'
    if request.method == 'POST' and 'info' in request.FILES:
        image_file = request.FILES['info']
        with tempfile.NamedTemporaryFile(delete=False, suffix='.jpg') as temp_file:
            for chunk in image_file.chunks():
                temp_file.write(chunk)
            temp_file_path = temp_file.name
        nutrition_data = analyze_food_nutrition(temp_file_path, apikey)
        os.remove(temp_file_path)

        if isinstance(nutrition_data, dict) and "error" in nutrition_data:
            return render(request, 'output.html', {'Recipe': True, 'error': nutrition_data["error"]})
        nutrition_dict = json.loads(nutrition_data)
        df = pd.DataFrame(nutrition_dict) # Debugging output

        s = NutritionImage.objects.create(
            user=request.user,
            image=image_file,  
            result=nutrition_dict 
        )
        s.save()

        return render(request, 'output.html', {'output_data': df.to_html(), 'ingredients': True})

    return render(request, 'checknutritions.html')