# bot.py
import asyncio
import logging
import os
from dotenv import load_dotenv

from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command, CommandStart
from aiogram.types import Message
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from quest_data import QUEST

load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")

logging.basicConfig(level=logging.INFO)

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()


class QuestState(StatesGroup):
    in_block = State()


def normalize(text: str) -> str:
    return text.strip().lower().replace("ё", "е").replace("  ", " ")


def block_progress(user_data: dict, block_num: int) -> int:
    return len(user_data.get(f"done_{block_num}", []))


def required_count(block_num: int) -> int:
    return QUEST[block_num].get("required", 3)


def next_task_index(user_data: dict, block_num: int):
    done = user_data.get(f"done_{block_num}", [])
    tasks = QUEST[block_num]["tasks"]
    for i, task in enumerate(tasks):
        if task["id"] not in done:
            return i
    return None


def block_completed(user_data: dict, block_num: int) -> bool:
    return block_progress(user_data, block_num) >= required_count(block_num)


def build_block_intro(block_num: int) -> str:
    b = QUEST[block_num]
    if block_num == 5:
        rule = ("Финальный сектор. Здесь нужно выполнить ВСЕ 5 заданий — "
                "иначе не получишь последнюю награду.")
    else:
        rule = "В блоке 5 заданий. Выполни минимум 3 — и получишь награду."
    return (
        f"🟩 {b['name']}\n"
        f"📍 Локация: {b['location']}\n\n"
        f"{rule}\n"
        f"За каждую подсказку — минус 1 очко воли.\n\n"
        f"Напиши /task чтобы получить первое задание."
    )


def build_final_message() -> str:
    return (
        "💚 Финальное послание Батареи Силы\n\n"
        "Женечка, ты прошёл все пять секторов. Клятва произнесена, "
        "воля проверена, страх побеждён, конструкты построены, "
        "спектр эмоций освоен.\n\n"
        "Но помни: кольцо Зелёного Фонаря питается не силой мышц, "
        "а силой воли. Не страхом. Не яростью. Не отчаянием. "
        "А верой в то, что можно изменить мир — если по-настоящему захотеть.\n\n"
        "Ты прошёл этот путь не потому, что умнее всех. "
        "А потому, что не сдался.\n\n"
        "Корпус Зелёных Фонарей признаёт тебя полноправным членом.\n\n"
        "💍 С днём рождения, моя любимка.\n\n"
        "Знаешь, иногда я смотрю на тебя и не могу поверить, "
        "что мне так повезло. Ты — лучшее, что случалось со мной. "
        "Я люблю тебя не за что-то, а просто потому, что ты — это ты. "
        "За твой взгляд, за твои руки, за то, как ты умеешь сделать "
        "даже обычный день волшебным.\n\n"
        "Я хочу, чтобы ты знал: я твоя навсегда. "
        "Пусть этот год принесёт тебе всё, о чём ты мечтаешь. "
        "А я буду рядом, чтобы разделить с тобой каждую минуту.\n\n"
        "💚 Да озарит твой путь свет воли."
    )


def check_answer(task: dict, user_text: str) -> bool:
    ua = normalize(user_text)
    if task.get("any"):
        return True
    if "all_words" in task:
        for w in task["all_words"]:
            if normalize(w) not in ua:
                return False
        return True
    for ans in task.get("answers", []):
        na = normalize(ans)
        if na in ua or ua in na:
            return True
    return False


@dp.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext):
    await state.clear()
    await state.update_data(
        block=1,
        done_1=[], done_2=[], done_3=[], done_4=[], done_5=[],
        hints_used=0,
        score=0,
    )
    await message.answer(
        "💚 Добро пожаловать в Корпус Зелёных Фонарей!\n\n"
        "Кольцо силы выбрало тебя. Внутри — твоё первое задание.\n"
        "Пройди пять секторов — и докажешь, что достоин носить зелёный цвет.\n"
        "За каждое испытание — награда.\n\n"
        "Правила:\n"
        "• Кольцо на руке всё время\n"
        "• В каждом блоке 5 заданий, нужно выполнить минимум 3\n"
        "• Подсказка — минус 1 очко воли\n\n"
        "Напиши /go чтобы начать Сектор 1 «Оа».",
    )


@dp.message(Command("go"))
async def cmd_go(message: Message, state: FSMContext):
    data = await state.get_data()
    block = data.get("block", 1)
    await state.set_state(QuestState.in_block)
    await message.answer(build_block_intro(block))


@dp.message(Command("task"))
async def cmd_task(message: Message, state: FSMContext):
    data = await state.get_data()
    block = data.get("block", 1)
    idx = next_task_index(data, block)

    if idx is None:
        await message.answer("Все задания блока выполнены. Напиши /next")
        return

    task = QUEST[block]["tasks"][idx]
    await message.answer(task["text"])


@dp.message(Command("next"))
async def cmd_next(message: Message, state: FSMContext):
    data = await state.get_data()
    block = data.get("block", 1)

    if not block_completed(data, block):
        done = block_progress(data, block)
        req = required_count(block)
        await message.answer(
            f"⚠️ Ты выполнил только {done} из {req} нужных заданий "
            f"в блоке {block}.\nНапиши /task чтобы продолжить."
        )
        return

    if block == 5:
        await message.answer(build_final_message())
        await state.clear()
        return

    location_hint = QUEST[block]["location_hint"]
    await message.answer(
        f"✅ Блок {block} пройден!\n\n"
        f"{location_hint}\n\n"
        f"Когда будешь готов — напиши /go для следующего сектора."
    )
    await state.update_data(block=block + 1)


@dp.message(Command("hint"))
async def cmd_hint(message: Message, state: FSMContext):
    data = await state.get_data()
    block = data.get("block", 1)
    idx = next_task_index(data, block)
    if idx is None:
        await message.answer("Нет активного задания.")
        return
    task = QUEST[block]["tasks"][idx]
    await state.update_data(
        hints_used=data.get("hints_used", 0) + 1,
        score=data.get("score", 0) - 1,
    )
    await message.answer(f"💡 Подсказка: {task['hint']}\n\n(-1 очко воли)")


@dp.message(Command("status"))
async def cmd_status(message: Message, state: FSMContext):
    data = await state.get_data()
    block = data.get("block", 1)
    lines = [f"🟢 Статус квеста\nТекущий блок: {block}\n"]
    for b in range(1, 6):
        done = block_progress(data, b)
        req = required_count(b)
        mark = "✅" if done >= req else "⏳"
        lines.append(f"{mark} Блок {b}: {done}/5 (нужно {req})")
    lines.append(f"\n💚 Очки воли: {data.get('score', 0)}")
    await message.answer("\n".join(lines))


@dp.message(Command("final"))
async def cmd_final(message: Message):
    await message.answer(build_final_message())


@dp.message(QuestState.in_block, F.text)
async def handle_answer(message: Message, state: FSMContext):
    data = await state.get_data()
    block = data.get("block", 1)
    idx = next_task_index(data, block)

    if idx is None:
        await message.answer("Все задания блока выполнены. Напиши /next")
        return

    task = QUEST[block]["tasks"][idx]

    if not check_answer(task, message.text):
        await message.answer(
            "❌ Неверно. Попробуй ещё раз или напиши /hint для подсказки."
        )
        return

    done_key = f"done_{block}"
    done = data.get(done_key, [])
    if task["id"] not in done:
        done.append(task["id"])
    await state.update_data(
        **{done_key: done, "score": data.get("score", 0) + 1}
    )

    req = required_count(block)
    await message.answer(
        f"✅ Верно! {task['id']} засчитано.\n\n"
        f"Прогресс блока: {len(done)}/5 (нужно {req}).\n"
        f"Напиши /task для следующего задания или /next если уже набрал {req}."
    )


async def main():
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
