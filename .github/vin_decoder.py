# vin_decoder.py
"""
Модуль для работы с API NHTSA: расшифровка VIN-кодов и WMI.
Документация API: https://vpic.nhtsa.dot.gov/api/
"""

import requests
from typing import Dict, Any, Optional, List

NHTSA_BASE_URL = "https://vpic.nhtsa.dot.gov/api/vehicles"

def _call_nhtsa_api(endpoint: str, params: Optional[Dict] = None, timeout: int = 10) -> Dict[str, Any]:
    """
    Универсальная функция для вызова API NHTSA.
    Args:
        endpoint: Часть URL после /vehicles/ (например, 'DecodeVin/...')
        params: Параметры запроса (например, {'format': 'json'})
        timeout: Таймаут в секундах.
    Returns:
        JSON-ответ от API в виде словаря.
    Raises:
        requests.exceptions.RequestException: При ошибках сети или HTTP.
    """
    if params is None:
        params = {'format': 'json'}  
    else:
        params.setdefault('format', 'json')
    
    url = f"{NHTSA_BASE_URL}/{endpoint}"
    response = requests.get(url, params=params, timeout=timeout)
    response.raise_for_status()  
    return response.json()

def decode_standard(vin: str, model_year: Optional[str] = None) -> List[Dict]:
    """
    1. Расшифровка VIN (DecodeVin) - иерархический формат.
    Возвращает список переменных и их значений для указанного VIN.
    """
    endpoint = f"DecodeVin/{vin}"
    params = {}
    if model_year:
        params['modelyear'] = model_year
    data = _call_nhtsa_api(endpoint, params)
    return data.get('Results', [])

def decode_flat(vin: str, model_year: Optional[str] = None) -> Dict:
    """
    2. Расшифровка VIN в плоском формате (DecodeVinValues).
    Возвращает один словарь, где ключи - названия атрибутов (Make, Model и т.д.).
    """
    endpoint = f"DecodeVinValues/{vin}"
    params = {}
    if model_year:
        params['modelyear'] = model_year
    data = _call_nhtsa_api(endpoint, params)
    results = data.get('Results', [])
    return results[0] if results else {}

def decode_extended(vin: str, model_year: Optional[str] = None) -> List[Dict]:
    """
    3. Расширенная расшифровка VIN (DecodeVinExtended).
    Возвращает больше полей, чем стандартная (например, мощность, электрофикация).
    """
    endpoint = f"DecodeVinExtended/{vin}"
    params = {}
    if model_year:
        params['modelyear'] = model_year
    data = _call_nhtsa_api(endpoint, params)
    return data.get('Results', [])

def decode_extended_flat(vin: str, model_year: Optional[str] = None) -> Dict:
    """
    4. Расширенная расшифровка VIN в плоском формате (DecodeVinValuesExtended).
    Возвращает словарь с максимальным количеством полей (до 136 атрибутов).
    """
    endpoint = f"DecodeVinValuesExtended/{vin}"
    params = {}
    if model_year:
        params['modelyear'] = model_year
    data = _call_nhtsa_api(endpoint, params)
    results = data.get('Results', [])
    return results[0] if results else {}

def decode_wmi(wmi: str) -> List[Dict]:
    """
    5. Расшифровка WMI (World Manufacturer Identifier) - первые 3 символа VIN.
    Возвращает информацию о производителе (название, страна, тип ТС).
    """
    if len(wmi) < 3:
        wmi = wmi[:3].ljust(3, '?')  
    else:
        wmi = wmi[:3]
    
    endpoint = f"DecodeWMI/{wmi}"
    data = _call_nhtsa_api(endpoint)
    return data.get('Results', [])

def print_flat_result(car_data: Dict) -> None:
    """Красиво печатает плоский результат расшифровки VIN."""
    if not car_data:
        print("Нет данных для отображения.")
        return
    
    important_keys = ['Make', 'Model', 'ModelYear', 'BodyClass', 'FuelTypePrimary', 
                      'EngineCylinders', 'DriveType', 'PlantCountry']
    print("\n--- Результат расшифровки VIN ---")
    for key in important_keys:
        value = car_data.get(key)
        if value and value != 'Not Applicable':
            print(f"{key}: {value}")

def print_wmi_result(wmi_data: List[Dict]) -> None:
    """Красиво печатает результат расшифровки WMI."""
    if not wmi_data:
        print("WMI не найден.")
        return
    
    print("\n--- Информация о производителе (WMI) ---")
    for item in wmi_data:
        print(f"Производитель: {item.get('Make', 'N/A')}")
        print(f"Название компании: {item.get('ManufacturerName', 'N/A')}")
        print(f"Страна: {item.get('Country', 'N/A')}")
        print(f"Тип ТС: {item.get('VehicleType', 'N/A')}")
        break  