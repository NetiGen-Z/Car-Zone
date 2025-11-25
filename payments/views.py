import json
import requests
from django.conf import settings
from django.shortcuts import render, redirect
from django.views.decorators.csrf import csrf_exempt
from django.utils import timezone
from cars.models import Car

def initiate_payment(request, car_id):
    try:
        car = Car.objects.get(id=car_id)
    except Car.DoesNotExist:
        return render(request, 'payments/payment_failed.html', {'error': 'Car not found'}, status=404)

    if request.method == 'POST':
        try:
            amount = int(float(request.POST.get('amount'))) * 10
        except (ValueError, TypeError):
            return render(request, 'payments/payment_failed.html', {'error': 'Invalid amount'}, status=400)

        purchase_order_id = request.POST.get('purchase_order_id')
        purchase_order_name = request.POST.get('purchase_order_name')

        # Safely handle user data
        if request.user.is_authenticated:
            name = request.user.get_full_name() or request.user.username or "Guest User"
            email = request.user.email or "guest@example.com"
        else:
            name = "Guest User"
            email = "guest@example.com"

        payload = {
            "return_url": settings.KHALTI_RETURN_URL,
            "website_url": settings.KHALTI_WEBSITE_URL,
            "amount": amount,
            "purchase_order_id": purchase_order_id,
            "purchase_order_name": purchase_order_name,
            "customer_info": {
                "name": name,
                "email": email,
                "phone": ""
            }
        }

        headers = {
            'Authorization': f'Key {settings.KHALTI_SECRET_KEY}',
            'Content-Type': 'application/json',
        }

        response = requests.post(
            "https://a.khalti.com/api/v2/epayment/initiate/",
            headers=headers,
            data=json.dumps(payload)
        )

        try:
            data = response.json()
        except json.JSONDecodeError:
            return render(request, 'payments/payment_failed.html', {'error': 'Invalid response from Khalti'}, status=502)

        if response.status_code == 200 and 'payment_url' in data:
            return redirect(data['payment_url'])
        else:
            return render(request, 'payments/payment_failed.html', {
                'error': data.get('detail', 'Failed to initiate payment')
            }, status=response.status_code)
    else:
        context = {
            'car': car,
            'amount': car.price,
            'purchase_order_id': f"ORDER_{car_id}_{timezone.now().strftime('%Y%m%d%H%M%S')}",
            'purchase_order_name': f"Payment for {car.car_title}"
        }
        return render(request, 'payments/payment_form.html', context)


@csrf_exempt
def verify_payment(request, car_id=None):
    pidx = request.GET.get('pidx')
    if not pidx:
        return render(request, 'payments/payment_failed.html', {'error': 'Missing payment ID'})

    headers = {
        'Authorization': f'Key {settings.KHALTI_SECRET_KEY}',
        'Content-Type': 'application/json',
    }

    lookup_url = "https://a.khalti.com/api/v2/epayment/lookup/"
    payload = {
        "pidx": pidx
    }

    print("LOOKUP URL:", lookup_url)
    print("Payload:", payload)

    try:
        response = requests.post(lookup_url, headers=headers, json=payload)

        print("Status Code:", response.status_code)
        print("Raw Response:", response.text)
        
    except requests.exceptions.RequestException as e:
        return render(request, 'payments/payment_failed.html', {
            'error': f"Network error during verification: {str(e)}"
        })

    try:
        data = response.json()
    except json.JSONDecodeError:
        return render(request, 'payments/payment_failed.html', {
            'error': f"Invalid response from Khalti. Could not parse JSON.",
        }, status=502)

    if response.status_code == 200 and data.get('status') == 'Completed':
        return render(request, 'payments/payment_success.html', {'transaction': data})
    else:
        error_message = data.get('detail', 'Payment not completed')
        return render(request, 'payments/payment_failed.html', {'error': error_message}, status=400)

