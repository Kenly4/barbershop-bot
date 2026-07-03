from aiogram.fsm.state import State, StatesGroup


class BookingSG(StatesGroup):
    service = State()
    date = State()
    time = State()
    name = State()
    phone = State()
    confirm = State()


class RescheduleSG(StatesGroup):
    date = State()
    time = State()


class SettingsSG(StatesGroup):
    day_hours = State()      # data: weekday
    svc_add = State()
    svc_price = State()      # data: service_id
    svc_duration = State()   # data: service_id
    svc_name = State()       # data: service_id
