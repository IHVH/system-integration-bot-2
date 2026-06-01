# main.py
import vin_decoder  

def demonstrate_vin_decoding():
    """Пример использования всех функций расшифровки VIN."""
    
    test_vin = "4T1G11AK5MU123456"  
    
    print("\n=== 1. Стандартная расшифровка VIN (DecodeVin) ===")
    standard_results = vin_decoder.decode_standard(test_vin)
    for i, item in enumerate(standard_results[:5]):  
        print(f"{item.get('Variable')}: {item.get('Value')}")
    
    print("\n=== 2. Расшифровка VIN, плоский формат (DecodeVinValues) ===")
    flat_data = vin_decoder.decode_flat(test_vin)
    vin_decoder.print_flat_result(flat_data)
    
    print("\n=== 3. Расширенная расшифровка VIN (DecodeVinExtended) ===")
    extended_results = vin_decoder.decode_extended(test_vin)
    for i, item in enumerate(extended_results[:8]):
        print(f"{item.get('Variable')}: {item.get('Value')}")
    
    print("\n=== 4. Расширенная расшифровка VIN, плоский формат (DecodeVinValuesExtended) ===")
    ext_flat_data = vin_decoder.decode_extended_flat(test_vin)
    extra_fields = ['EnginePowerKW', 'ElectrificationLevel', 'TopSpeedMPH', 'WheelSizeFront']
    for field in extra_fields:
        value = ext_flat_data.get(field)
        if value and value != 'Not Applicable':
            print(f"{field}: {value}")
    
    print("\n=== 5. Расшифровка WMI (DecodeWMI) ===")
    wmi_data = vin_decoder.decode_wmi(test_vin[:3])
    vin_decoder.print_wmi_result(wmi_data)

if __name__ == "__main__":
    demonstrate_vin_decoding()