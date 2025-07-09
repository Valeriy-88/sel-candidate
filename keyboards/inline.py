from aiogram import types
from aiogram.types import InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from data import nicknames, quiz_data


def next_message() -> InlineKeyboardMarkup:
    """
    Создает клавиатуру с кнопкой "Далее" для перехода к следующему сообщению.

    Returns:
        InlineKeyboardMarkup: Клавиатура с одной кнопкой "Далее" (callback_data="next")
    """
    builder = InlineKeyboardBuilder()
    builder.add(types.InlineKeyboardButton(text="Далее", callback_data="next"))
    return builder.as_markup()


def start_test() -> InlineKeyboardMarkup:
    """
    Создает клавиатуру для начала теста с одной кнопкой "Начать тест".

    Returns:
        InlineKeyboardMarkup: Клавиатура с кнопкой старта теста (callback_data="start_test_user")
    """
    builder = InlineKeyboardBuilder()
    builder.add(
        types.InlineKeyboardButton(text="Начать тест", callback_data="start_test_user")
    )
    return builder.as_markup()


def build_quiz_keyboard(question_index: int) -> types.InlineKeyboardMarkup:
    """
    Создает клавиатуру с вариантами ответов для конкретного вопроса теста.

    Args:
        question_index (int): Индекс вопроса в quiz_data

    Returns:
        InlineKeyboardMarkup: Клавиатура с вариантами ответов (callback_data="answer_[question_index]_[option_index]")
    """
    builder = InlineKeyboardBuilder()
    question = quiz_data[question_index]

    for i, option in enumerate(question["options"]):
        builder.button(text=option, callback_data=f"answer_{question_index}_{i}")

    builder.adjust(1)
    return builder.as_markup()


def delete_manager() -> types.InlineKeyboardMarkup:
    """
    Создает клавиатуру для выбора менеджера из списка nicknames для удаления.

    Returns:
        InlineKeyboardMarkup: Клавиатура с кнопками менеджеров (callback_data="delete_[index]")
    """
    builder = InlineKeyboardBuilder()
    for i, option in enumerate(nicknames):
        builder.button(text=option, callback_data=f"delete_{i}")

    builder.adjust(1)
    return builder.as_markup()
