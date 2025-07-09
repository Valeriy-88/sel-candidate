import asyncio
import random
from collections import defaultdict
from datetime import datetime, timedelta

from aiogram import Bot, F, Router, types
from aiogram.filters import BaseFilter
from aiogram.filters.command import Command

from config import ADMIN_ID
from data import array_text, nicknames, quiz_data, save_nicks
from keyboards.inline import (
    build_quiz_keyboard,
    delete_manager,
    next_message,
    start_test,
)

router = Router()
user_states: dict = {}
user_answers: dict = {}
user_scores: dict = {}
user_phase: dict = {}
user_last_action: dict = {}
reminder_tasks: dict = {}
nickname_stats = defaultdict(int)
if not nicknames:
    nicknames: list[str] = [""]
    save_nicks(nicknames)

nickname_queue = nicknames.copy()
random.shuffle(nickname_queue)

bot_instance = None


class IsAdmin(BaseFilter):
    """Фильтр для проверки прав администратора"""
    async def __call__(self, message: types.Message) -> bool:
        return message.from_user.id == ADMIN_ID


async def on_startup(bot: Bot) -> None:
    """Инициализация бота при запуске"""
    global bot_instance
    bot_instance = bot
    print("Бот инициализирован: %s", bot_instance is not None)


async def on_shutdown() -> None:
    """Очистка ресурсов при завершении работы"""
    for task in reminder_tasks.values():
        task.cancel()
    print("Бот завершает работу, задачи напоминаний отменены")


async def send_reminder(user_id: int) -> None:
    """
    Отправляет напоминание пользователю через 10 минут бездействия

    Args:
        user_id (int): ID пользователя для отправки напоминания
    """
    try:
        await asyncio.sleep(600)

        if user_id not in user_phase or user_id not in user_last_action:
            return

        if user_id in user_scores and user_scores[user_id] == len(quiz_data):
            return

        if datetime.now() - user_last_action[user_id] < timedelta(minutes=10):
            return

        try:
            if user_phase[user_id] == "text":
                await bot_instance.send_message(
                    user_id,
                    "⏰ Ты забыл про меня! "
                    "Давай продолжим чтение текстов. Нажми /start чтобы продолжить.",
                )
            elif user_phase[user_id] == "quiz":
                await bot_instance.send_message(
                    user_id,
                    "⏰ Ты забыл про тестирование! "
                    "Давай завершим его. Нажми /start чтобы продолжить.",
                )
        except Exception as e:
            print("Ошибка отправки напоминания пользователю %s: %s", user_id, e)

    except asyncio.CancelledError:
        print("Задача напоминания отменена")
    except Exception as e:
        print("Неожиданная ошибка в задаче напоминания: %s", e)


def update_last_action(user_id: int) -> None:
    """
    Обновляет время последнего действия пользователя и создает задачу напоминания

    Args:
        user_id (int): ID пользователя
    """
    user_last_action[user_id] = datetime.now()

    if user_id in reminder_tasks:
        try:
            reminder_tasks[user_id].cancel()
        except:
            pass

    if user_id not in user_scores or user_scores[user_id] < len(quiz_data):
        reminder_tasks[user_id] = asyncio.create_task(send_reminder(user_id))
        print("Создана задача напоминания для пользователя %s", user_id)


@router.message(Command("start"))
async def cmd_start(message: types.Message):
    """
    Обработчик команды /start
    Инициализирует состояние пользователя для начала работы с ботом
    """
    user_id: int = message.from_user.id

    if user_id in user_scores and user_scores[user_id] == len(quiz_data):
        await message.answer("Вы уже успешно завершили тестирование!")
        return

    user_states[user_id]: int = -1
    user_scores[user_id]: int = 0
    user_phase[user_id]: str = "text"
    update_last_action(user_id)

    await message.answer(
        "Приветствую! Этот бот поможет вам узнать подробнее "
        "о работе и пройти обучение.\nПосле обучения будет "
        "небольшой тест на проверку того, как вы усвоили материал, "
        "поэтому будьте внимательны во время изучения "
        "информации.\nНажмите кнопку ниже и поехали 🚀 ",
        reply_markup=next_message(),
    )


@router.callback_query(F.data == "next")
async def handle_next_callback(callback: types.CallbackQuery):
    """
    Обработчик нажатия кнопки "Далее"
    Переключает между текстами обучения или запускает тест
    """
    user_id: int = callback.from_user.id
    update_last_action(user_id)

    try:
        await callback.message.delete()
    except Exception as e:
        print("Ошибка при удалении сообщения: %s", e)

    if user_phase.get(user_id) == "text":
        current_index: int = user_states.get(user_id, -1) + 1
        user_states[user_id]: int = current_index

        if current_index >= len(array_text):
            await callback.message.answer(
                "Обучение пройдено! Давай приступим к тесту. Нажимай кнопку «начать тест»",
                reply_markup=start_test(),
            )
        else:
            text = array_text[current_index]
            await callback.message.answer(f"{text}", reply_markup=next_message())
    else:
        await callback.answer("Нажмите на вариант ответа")


@router.callback_query(F.data == "start_test_user")
async def handle_start_test(callback: types.CallbackQuery):
    """
    Обработчик начала тестирования
    Переводит пользователя в фазу тестирования и показывает первый вопрос
    """
    user_id: int = callback.from_user.id
    update_last_action(user_id)

    try:
        await callback.message.delete()
    except Exception as e:
        print("Ошибка при удалении сообщения: %s", e)

    user_phase[user_id]: str = "quiz"
    user_states[user_id]: int = 0
    question = quiz_data[0]["question"]
    await callback.message.answer(f"{question}", reply_markup=build_quiz_keyboard(0))


@router.callback_query(F.data.startswith("answer_"))
async def handle_answer(callback: types.CallbackQuery):
    """
    Обработчик ответов на вопросы теста
    Проверяет правильность ответа и переключает на следующий вопрос
    """
    user_id: int = callback.from_user.id
    update_last_action(user_id)

    if user_phase.get(user_id) != "quiz":
        await callback.answer("Сначала прочитайте все тексты")
        return

    parts: list[str] = callback.data.split("_")
    question_index: int = int(parts[1])
    answer_index: int = int(parts[2])

    selected_answer: str = quiz_data[question_index]["options"][answer_index]
    correct_answer: str | list[str] = quiz_data[question_index]["correct"]

    is_correct: bool = selected_answer == correct_answer

    if is_correct:
        user_scores[user_id]: int = user_scores.get(user_id, 0) + 1

    next_question_index: int = question_index + 1
    user_states[user_id]: int = next_question_index

    if next_question_index >= len(quiz_data):
        await show_results(callback)

        if user_id in reminder_tasks:
            reminder_tasks[user_id].cancel()
            del reminder_tasks[user_id]
    else:
        question: str | list[str] = quiz_data[next_question_index]["question"]
        await callback.message.edit_text(
            f"{question}", reply_markup=build_quiz_keyboard(next_question_index)
        )


def get_next_nickname():
    """
    Возвращает никнейм менеджера с равномерным распределением

    Returns:
        str: Следующий никнейм менеджера для контакта
    """
    global nickname_queue

    if not nickname_queue:
        min_count: int = min(nickname_stats.values()) if nickname_stats else 0
        candidates: list[str] = [
            nick for nick in nicknames if nickname_stats.get(nick, 0) == min_count
        ]
        if not candidates:
            candidates: list[str] = nicknames.copy()
        nickname_queue = random.sample(candidates, len(candidates))

    next_nick: str = nickname_queue.pop()
    nickname_stats[next_nick]: int = nickname_stats.get(next_nick, 0) + 1

    return next_nick


async def show_results(callback: types.CallbackQuery):
    """
    Показывает результаты тестирования и контакт менеджера

    Args:
        callback (CallbackQuery): Объект callback запроса
    """
    user_id: int = callback.from_user.id
    total_questions: int = len(quiz_data)
    correct_answers: int = user_scores.get(user_id, 0)

    try:
        selected_nick: str = get_next_nickname()
        success_message: str = (
            "Поздравляю! Вы успешно прошли обучение и тест! "
            f"Скорее пишите Вашему САМу для дальнейшего трудоустройства {selected_nick}.\n\n"
            "<b>Мы ждем вашего сообщения!</b>\n\n"
            "Можете выйти из обучающего бота, чтобы Вас не беспокоили уведомления!\n"
            "<i>Вас примут на работу в течение суток. "
            "Менеджер отвечает сотрудникам в порядке очереди. "
            "В субботу менеджеры не отвечают.</i>"
        )
    except Exception as e:
        print("Ошибка при выборе никнейма: %s", e)
        success_message: str = (
            "Поздравляю! Вы успешно прошли обучение и тест! "
            "Скорее свяжитесь с вашим руководителем "
            "для дальнейшего трудоустройства https://t.me/gridnyasha.\n\n"
            "<b>Мы ждем вашего сообщения!</b>\n"
            "<i>Вас примут на работу в течение суток. "
            "Менеджер отвечает сотрудникам в порядке очереди. "
            "В субботу менеджеры не отвечают.</i>"
        )

    if correct_answers >= total_questions:
        await callback.message.edit_text(success_message)
    else:
        await callback.message.edit_text(
            f"Вы ответили правильно на {correct_answers} "
            f"из {total_questions} вопросов.\n"
            "Попробуйте еще раз!",
            reply_markup=types.InlineKeyboardMarkup(
                inline_keyboard=[
                    [
                        types.InlineKeyboardButton(
                            text="Начать заново", callback_data="restart"
                        )
                    ]
                ]
            ),
        )


@router.callback_query(F.data == "restart")
async def handle_restart(callback: types.CallbackQuery):
    """
    Обработчик перезапуска тестирования
    Сбрасывает прогресс пользователя и возвращает к началу обучения
    """
    user_id: int = callback.from_user.id
    user_states[user_id]: int = -1
    user_scores[user_id]: int = 0
    user_phase[user_id]: str = "text"
    update_last_action(user_id)

    try:
        await callback.message.delete()
    except Exception as e:
        print("Ошибка при удалении сообщения: %s", e)

    await callback.message.answer(
        "Нажмите «Далее» чтобы заново прочитать текст и пройти тестирование",
        reply_markup=next_message(),
    )


@router.message(Command("list"), IsAdmin())
async def cmd_list(message: types.Message):
    """
    Показывает список всех менеджеров (только для администратора)
    """
    array_nicknames = "\n".join(nicknames)
    await message.answer(
        "Твой список сотрудников:\n%s",
        array_nicknames,
    )


@router.message(Command("add"), IsAdmin())
async def cmd_add(message: types.Message):
    """
    Запускает процесс добавления нового менеджера (только для администратора)
    """
    await message.answer(
        "Напиши никнейм сотрудника которого хочешь добавить в свой список",
    )
    user_phase[message.from_user.id]: str = "adding_nickname"


@router.message(Command("del"), IsAdmin())
async def cmd_delete(message: types.Message):
    """
    Запускает процесс удаления менеджера (только для администратора)
    """
    await message.answer(
        "выбери менеджера которого хочешь удалить из списка",
        reply_markup=delete_manager(),
    )


@router.callback_query(F.data.startswith("delete_"))
async def handle_delete(callback: types.CallbackQuery):
    """
    Обработчик удаления менеджера из списка
    """
    index: int = int(callback.data.split("_")[1])
    deleted_nick: str = nicknames.pop(index)
    save_nicks(nicknames)

    if deleted_nick in nickname_queue:
        nickname_queue.remove(deleted_nick)
    if deleted_nick in nickname_stats:
        del nickname_stats[deleted_nick]

    await callback.message.edit_text(
        f"Никнейм {deleted_nick} успешно удален", reply_markup=None
    )


@router.message(Command("list", "add", "del"))
async def handle_non_admin_commands(message: types.Message):
    """
    Обработчик команд администратора для не-администраторов
    """
    await message.answer("⛔ Эта команда доступна только администратору")


@router.message(F.text)
async def add_manager_in_list(message: types.Message):
    """
    Обработчик добавления нового менеджера в список
    """
    if user_phase.get(message.from_user.id) != "adding_nickname":
        return

    if message.from_user.id != ADMIN_ID:
        return

    new_nick: str = message.text.strip()

    if not new_nick:
        await message.answer("Никнейм не может быть пустым")
        return

    if f"https://t.me/{new_nick}" in nicknames:
        await message.answer("Этот ник уже есть в списке!")
        return

    if new_nick.startswith(("http://", "https://", "@")):
        await message.answer("Вводите только логин (без @ и ссылок)")
        return

    full_nick: str = f"https://t.me/{new_nick}"

    nicknames.append(full_nick)
    save_nicks(nicknames)

    for nick in nicknames:
        nickname_stats[nick] = 0

    nickname_queue.clear()

    user_phase[message.from_user.id] = None
    await message.answer("Никнейм %s успешно добавлен", full_nick)
