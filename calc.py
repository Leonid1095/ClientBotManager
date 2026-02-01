# calc.py
# Модуль для калькулятора стоимости заказа

# Здесь будет реализована логика расчета стоимости по параметрам заказа



def calculate_price(type_bot: str, complexity: str, hosting: str, bonus: int = 0) -> int:
    base = 5000
    if type_bot == "магазин":
        base += 5000
    if complexity == "сложный":
        base += 7000
    if hosting == "мой сервер":
        base += 2000
    final_price = max(base - bonus, 0)
    return final_price
