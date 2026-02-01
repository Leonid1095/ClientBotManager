# states.py
# Модуль для описания состояний FSM (Finite State Machine) для форм и сценариев

# Здесь будут описаны состояния для:
# - Многошаговой формы заказа
# - Других сценариев, если потребуется


from aiogram.dispatcher.filters.state import State, StatesGroup


class OrderForm(StatesGroup):
	fio = State()
	contact = State()
	idea = State()
	type_bot = State()
	budget = State()
	deadline = State()
	options = State()
	settings = State()
	file = State()
	hosting = State()
	use_bonus = State()


class StatusForm(StatesGroup):
	order_id = State()


class CalcState(StatesGroup):
	type_bot = State()
	complexity = State()
	hosting = State()


class ReviewForm(StatesGroup):
	text = State()
