import os
import json
import uuid
from flask import Flask, request, jsonify
from google.oauth2 import service_account
from google.auth.transport.requests import Request
import requests
import jwt
from dotenv import load_dotenv
from datetime import datetime

load_dotenv()

app = Flask(__name__)

ISSUER_ID = '3388000000022968451'
RECEIPT_CLASS_ID = f"{ISSUER_ID}.receipt_class_1"
SHOPPING_LIST_CLASS_ID = f"{ISSUER_ID}.shopping_list_class_4"
BASE_URL = 'https://walletobjects.googleapis.com/walletobjects/v1'
GOOGLE_APPLICATION_CREDENTIALS = os.environ.get('GOOGLE_APPLICATION_CREDENTIALS')
ORIGINS = ['http://localhost:5000']

credentials = service_account.Credentials.from_service_account_file(
    GOOGLE_APPLICATION_CREDENTIALS,
    scopes=['https://www.googleapis.com/auth/wallet_object.issuer']
)

with open(GOOGLE_APPLICATION_CREDENTIALS, 'r') as f:
    cred_json = json.load(f)

session = requests.Session()

# ---- Helper to get Bearer Token ----
def get_bearer_token():
    if not credentials.valid or credentials.expired:
        credentials.refresh(Request())
    return credentials.token

# ---- Create Receipt Class (existing) ----
def create_pass_class(max_items):
    card_rows = []
    for idx in range(max_items):
        row = {
            "threeItems": {
                "startItem": {
                    "firstValue": {
                        "fields": [{"fieldPath": f"object.textModulesData['item_{idx}']"}]
                    }
                },
                "middleItem": {
                    "firstValue": {
                        "fields": [{"fieldPath": f"object.textModulesData['qnty_{idx}']"}]
                    }
                },
                "endItem": {
                    "firstValue": {
                        "fields": [{"fieldPath": f"object.textModulesData['price_{idx}']"}]
                    }
                }
            }
        }
        card_rows.append(row)

    generic_class = {
        'id': RECEIPT_CLASS_ID,
        'classTemplateInfo': {
            'cardTemplateOverride': {
                'cardRowTemplateInfos': card_rows
            }
        }
    }

    headers = {
        'Authorization': f'Bearer {get_bearer_token()}',
        'Content-Type': 'application/json'
    }
    resp = session.get(f'{BASE_URL}/genericClass/{RECEIPT_CLASS_ID}', headers=headers)
    if resp.status_code == 200:
        print('Receipt class already exists')
        return
    elif resp.status_code == 404:
        resp = session.post(f'{BASE_URL}/genericClass', headers=headers, data=json.dumps(generic_class))
        if resp.status_code in (200, 409):
            print('Receipt class created')
        else:
            print('Error creating receipt class:', resp.text)
            raise Exception('Receipt class creation failed')
    else:
        print('Unexpected status getting receipt class:', resp.status_code, resp.text)
        raise Exception('Error checking receipt class existence')

# ---- Create Shopping List Class ----
def create_shopping_list_class(max_items):
    card_rows = []
    for idx in range(max_items):
        row = {
            "threeItems": {
                "startItem": {
                    "firstValue": {
                        "fields": [{"fieldPath": f"object.textModulesData['item_{idx}']"}]
                    }
                },
                "middleItem": {
                    "firstValue": {
                        "fields": [{"fieldPath": f"object.textModulesData['quantity_{idx}']"}]
                    }
                },
                "endItem": {
                    "firstValue": {
                        "fields": [{"fieldPath": f"object.textModulesData['cost_{idx}']"}]
                    }
                }
            }
        }
        card_rows.append(row)

    generic_class = {
        'id': SHOPPING_LIST_CLASS_ID,
        'classTemplateInfo': {
            'cardTemplateOverride': {
                'cardRowTemplateInfos': card_rows
            }
        }
    }

    headers = {
        'Authorization': f'Bearer {get_bearer_token()}',
        'Content-Type': 'application/json'
    }
    resp = session.get(f'{BASE_URL}/genericClass/{SHOPPING_LIST_CLASS_ID}', headers=headers)
    if resp.status_code == 200:
        print('Shopping list class already exists')
        return
    elif resp.status_code == 404:
        resp = session.post(f'{BASE_URL}/genericClass', headers=headers, data=json.dumps(generic_class))
        if resp.status_code in (200, 409):
            print('Shopping list class created')
        else:
            print('Error creating shopping list class:', resp.text)
            raise Exception('Shopping list class creation failed')
    else:
        print('Unexpected status getting shopping list class:', resp.status_code, resp.text)
        raise Exception('Error checking shopping list class existence')

# ---- Create Receipt Object (existing) ----
def create_pass_object(receipt_data, grouping_id, sort_index):
    object_suffix = str(uuid.uuid4())
    object_id = f"{ISSUER_ID}.receipt_{object_suffix}"

    category = receipt_data.get('category', 'Receipt')
    date = receipt_data.get('date', '')
    items = receipt_data.get('items', [])
    vendor_name = receipt_data.get('vendorName', '') or 'Receipt Management'
 
    text_modules = []
    for idx, item in enumerate(items):
        text_modules.append({
            'id': f'item_{idx}',
            'header': '',
            'body': item.get('item', '')
        })
        text_modules.append({
            'id': f'qnty_{idx}',
            'header': '',
            'body': item.get('qnty', '')
        })
        text_modules.append({
            'id': f'price_{idx}',
            'header': '',
            'body': item.get('price', '')
        })

    generic_object = {
        'id': object_id,
        'classId': RECEIPT_CLASS_ID,
        'genericType': 'GENERIC_TYPE_UNSPECIFIED',
        'hexBackgroundColor': '#34A853',
        'logo': {
            'sourceUri': {'uri': 'https://storage.googleapis.com/wallet-lab-tools-codelab-artifacts-public/pass_google_logo.jpg'}
        },
        'cardTitle': {'defaultValue': {'language': 'en', 'value': vendor_name}},
        'subheader': {'defaultValue': {'language': 'en', 'value': date}},
        'header': {'defaultValue': {'language': 'en', 'value': category}},
          "barcode": { "type": "TEXT_ONLY","value": text_modules},
        'textModulesData': text_modules,
        'groupingInfo': {
            'groupingId': grouping_id,
            'sortIndex': sort_index
        }
    }

    headers = {
        'Authorization': f'Bearer {get_bearer_token()}',
        'Content-Type': 'application/json'
    }

    resp = session.post(f'{BASE_URL}/genericObject', headers=headers, data=json.dumps(generic_object))
    if resp.status_code not in (200, 409):
        print('Error creating receipt object:', resp.text)
        raise Exception('Receipt object creation failed')

    print('Receipt object created:', object_id)
    return object_id

# ---- Create Shopping List Object (Updated with Instructions Support) ----
def create_shopping_list_object(list_data, grouping_id, sort_index):
    object_suffix = str(uuid.uuid4())
    object_id = f"{ISSUER_ID}.shopping_{object_suffix}"

    task_name = list_data.get('taskName', 'Shopping List') 
    category = list_data.get('category', 'General') 
    date = list_data.get('date', datetime.now().strftime('%Y-%m-%d'))
    items = list_data.get('items', [])
    cooking_instructions = list_data.get('cookingInstructions', [])

    # Create text modules for shopping items (these will appear in the card template - front of pass)
    text_modules = []
    total_estimated_cost = 0
    
    for idx, item in enumerate(items):
        item_name = item.get('item', '')
        quantity = item.get('quantity', '1')
        approx_cost = item.get('approxCost', '₹0.00')
        
        text_modules.append({
            'id': f'item_{idx}',
            'header': '',
            'body': item_name
        })
        text_modules.append({
            'id': f'quantity_{idx}',
            'header': '',
            'body': quantity
        })
        text_modules.append({
            'id': f'cost_{idx}',
            'header': '',
            'body': approx_cost
        })
        
        # Calculate total cost (remove ₹ and convert to float)
        try:
            cost_value = float(approx_cost.replace('₹', '').replace(',', ''))
            total_estimated_cost += cost_value
        except ValueError:
            pass  # Skip if cost format is invalid

    # Add cooking instructions as additional text modules (these will appear in details section - back of pass)
    if cooking_instructions:
        # Add recipe info if available
        cooking_info = []
        if list_data.get('cookingTime'):
            cooking_info.append(f"⏱️ {list_data['cookingTime']}")
        if list_data.get('servings'):
            cooking_info.append(f"🍽️ Serves {list_data['servings']}")
        if list_data.get('difficulty'):
            cooking_info.append(f"📊 {list_data['difficulty']}")
        
        if cooking_info:
            text_modules.append({
                'id': 'recipe_info',
                'header': 'Recipe Info',
                'body': ' • '.join(cooking_info)
            })

        # Add instructions header
        text_modules.append({
            'id': 'instructions_header',
            'header': 'Cooking Instructions',
            'body': 'Follow these steps to prepare your recipe:'
        })
        
        # Add each cooking instruction step
        for idx, instruction in enumerate(cooking_instructions):
            text_modules.append({
                'id': f'instruction_{idx}',
                'header': f'Step {idx + 1}',
                'body': instruction.strip()
            })
        
        # Add cooking tips if provided
        if list_data.get('cookingTips'):
            tips = list_data['cookingTips']
            if isinstance(tips, list):
                tips_text = '\n'.join([f"• {tip}" for tip in tips])
            else:
                tips_text = tips
            
            text_modules.append({
                'id': 'cooking_tips',
                'header': '💡 Pro Tips',
                'body': tips_text
            })

    # Format total cost
    total_cost_str = f"Est. Total: ₹{total_estimated_cost:.2f}"

    generic_object = {
        'id': object_id,
        'classId': SHOPPING_LIST_CLASS_ID,
        'genericType': 'GENERIC_TYPE_UNSPECIFIED',
        'hexBackgroundColor': '#4285F4',
        'logo': {
            'sourceUri': {'uri': 'https://storage.googleapis.com/wallet-lab-tools-codelab-artifacts-public/pass_google_logo.jpg'}
        },
        'cardTitle': {'defaultValue': {'language': 'en', 'value': 'Shopping List'}},
        'subheader': {'defaultValue': {'language': 'en', 'value': f"{category} • {total_cost_str}"}},
        'header': {'defaultValue': {'language': 'en', 'value': task_name}},
        'textModulesData': text_modules,
        'groupingInfo': {
            'groupingId': grouping_id,
            'sortIndex': sort_index
        }
    }

    headers = {
        'Authorization': f'Bearer {get_bearer_token()}',
        'Content-Type': 'application/json'
    }

    resp = session.post(f'{BASE_URL}/genericObject', headers=headers, data=json.dumps(generic_object))
    if resp.status_code not in (200, 409):
        print('Error creating shopping list object:', resp.text)
        raise Exception('Shopping list object creation failed')

    print('Shopping list object created:', object_id)
    return object_id

# ---- Generate Save-to-Wallet Link for Multiple Objects ----
def generate_save_link(object_ids):
    payload = {
        "iss": cred_json['client_email'],
        "aud": "google",
        "origins": ORIGINS,
        "typ": "savetowallet",
        "payload": {
            "genericObjects": [{"id": obj_id} for obj_id in object_ids]
        }
    }
    token = jwt.encode(payload, cred_json['private_key'], algorithm='RS256')
    if isinstance(token, bytes):
        token = token.decode('utf-8')
    return f"https://pay.google.com/gp/v/save/{token}"

# ---- API Route for Grouped Receipt Passes (existing) ----
@app.route("/create-grouped-passes", methods=["POST"])
def create_grouped_passes():
    """
    Expected JSON format:
    {
        "groupingId": "food_group_1",
        "passes": [
            {
                "category": "Food & Dining",
                "date": "2025-07-26",
                "items": [...]
            },
            {
                "category": "Food & Dining",
                "date": "2025-07-27",
                "items": [...]
            }
        ]
    }
    """
    data = request.get_json()
    if not data:
        return jsonify({'error': 'No JSON data provided'}), 400

    grouping_id = data.get('groupingId')
    passes = data.get('passes')

    if not grouping_id or not passes or not isinstance(passes, list):
        return jsonify({'error': 'groupingId and passes list are required'}), 400

    try:
        # Determine max items per pass for template
        max_items = max(len(p['items']) for p in passes)
        create_pass_class(max_items=max_items)

        # Prepare sorting by date (latest first) if sortIndex not provided
        passes_with_dates = []
        for p in passes:
            date_str = p.get('date', '')
            try:
                date_obj = datetime.strptime(date_str, '%Y-%m-%d')
            except ValueError:
                date_obj = datetime.min  # Invalid date goes last
            passes_with_dates.append((p, date_obj))

        # Sort descending by date
        passes_with_dates.sort(key=lambda x: x[1], reverse=True)

        object_ids = []
        for idx, (pass_data, _) in enumerate(passes_with_dates):
            # If sortIndex is provided, use it, else assign based on date order
            sort_index = pass_data.get('sortIndex') or (idx + 1)
            object_id = create_pass_object(pass_data, grouping_id, sort_index)
            object_ids.append(object_id)

        # Generate Save Link for all grouped passes
        save_link = generate_save_link(object_ids)

        return jsonify({
            'success': True,
            'object_ids': object_ids,
            'save_link': save_link
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# ---- API Route for Shopping List Passes (Updated with Instructions Support) ----
@app.route("/create-shopping-lists", methods=["POST"])
def create_shopping_lists():
    """
    Enhanced JSON format for shopping lists with cooking instructions:
    {
        "groupingId": "baking_group_1",
        "lists": [
            {
                "taskName": "Baking a Cake",
                "category": "Baking & Desserts", 
                "date": "2025-07-26",
                "cookingTime": "45 mins",
                "servings": "8 people",
                "difficulty": "Medium",
                "items": [
                    {"item": "All-purpose flour", "quantity": "2 cups", "approxCost": "₹35.00"},
                    {"item": "Sugar", "quantity": "1.5 cups", "approxCost": "₹22.50"}
                ],
                "cookingInstructions": [
                    "Preheat oven to 350°F (175°C)",
                    "In a large bowl, cream together butter and sugar until light and fluffy",
                    "Beat in eggs one at a time, then add vanilla",
                    "In a separate bowl, whisk together flour, baking powder, and salt",
                    "Gradually mix dry ingredients into wet ingredients",
                    "Pour batter into greased 9-inch round pans",
                    "Bake for 25-30 minutes or until toothpick comes out clean",
                    "Cool completely before frosting"
                ],
                "cookingTips": [
                    "Room temperature ingredients mix better",
                    "Don't overmix the batter to avoid tough cake",
                    "Test doneness with a toothpick in the center"
                ]
            }
        ]
    }
    """
    data = request.get_json()
    if not data:
        return jsonify({'error': 'No JSON data provided'}), 400

    grouping_id = data.get('groupingId')
    lists = data.get('lists')

    if not grouping_id or not lists or not isinstance(lists, list):
        return jsonify({'error': 'groupingId and lists are required'}), 400

    try:
        max_items = max(len(l['items']) for l in lists)
        create_shopping_list_class(max_items=max_items)

        object_ids = []
        for idx, list_data in enumerate(lists):
            sort_index = list_data.get('sortIndex') or (idx + 1)
            object_id = create_shopping_list_object(list_data, grouping_id, sort_index)
            object_ids.append(object_id)

        save_link = generate_save_link(object_ids)

        return jsonify({
            'success': True,
            'object_ids': object_ids,
            'save_link': save_link,
            'message': 'Shopping lists created with cooking instructions in details section'
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# ---- Health Check ----
@app.route("/health", methods=["GET"])
def health_check():
    return jsonify({'status': 'healthy', 'message': 'Google Wallet Pass API is running'})

# ---- API Documentation ----
@app.route("/", methods=["GET"])
def api_info():
    return jsonify({
        'message': 'Google Wallet Pass API (Receipts & Shopping Lists with Cooking Instructions)',
        'endpoints': {
            'POST /create-grouped-passes': 'Create grouped receipt wallet passes from JSON data',
            'POST /create-shopping-lists': 'Create shopping list wallet passes with cooking instructions',
            'GET /health': 'Health check endpoint',
            'GET /': 'API information'
        },
        'features': {
            'shopping_lists': [
                'Shopping items displayed in 3-column layout on front of pass',
                'Cooking instructions appear in details section (back of pass)',
                'Support for recipe info (cooking time, servings, difficulty)',
                'Pro tips section for additional cooking advice',
                'Estimated total cost calculation'
            ]
        },
        'examples': {
            'receipts': {
                'url': '/create-grouped-passes',
                'method': 'POST',
                'content_type': 'application/json',
                'body': {
                    'groupingId': 'food_group_1',
                    'passes': [
                        {
                            'category': 'Food & Dining',
                            'date': '2025-07-26',
                            'items': [
                                {'item': 'Pizza', 'qnty': '1', 'price': '₹150.00'},
                                {'item': 'Cola', 'qnty': '2', 'price': '₹40.00'}
                            ]
                        }
                    ]
                }
            },
            'shopping_lists': {
                'url': '/create-shopping-lists',
                'method': 'POST',
                'content_type': 'application/json',
                'body': {
                    'groupingId': 'baking_group_1',
                    'lists': [
                        {
                            'taskName': 'Chocolate Chip Cookies',
                            'category': 'Baking & Desserts',
                            'cookingTime': '25 mins',
                            'servings': '24 cookies',
                            'difficulty': 'Easy',
                            'items': [
                                {'item': 'All-purpose flour', 'quantity': '2 cups', 'approxCost': '₹35.00'},
                                {'item': 'Sugar', 'quantity': '1.5 cups', 'approxCost': '₹22.50'}
                            ],
                            'cookingInstructions': [
                                'Preheat oven to 375°F (190°C)',
                                'Mix dry ingredients in a bowl',
                                'Cream butter and sugar until fluffy',
                                'Combine wet and dry ingredients',
                                'Drop spoonfuls on baking sheet',
                                'Bake for 9-11 minutes until golden'
                            ],
                            'cookingTips': [
                                'Use room temperature butter for better mixing',
                                'Don\'t overbake - cookies will continue cooking on hot pan'
                            ]
                        }
                    ]
                }
            }
        }
    })

if __name__ == "__main__":
    app.run(debug=True)