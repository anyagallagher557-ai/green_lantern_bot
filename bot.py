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


def next_task_index(user_data: dict, block_num: int):
    done = user_data.get(f"done_{block_num}", [])
    tasks = QUEST[block_num]["tasks"]
    for i, task in enumerate(tasks):
        if task["id"] not in done:
            return i
    return None


def block_completed(user_data: dict, block_num: int) -> bool:
    return block_progress(user_data, block_num) >= 3


def build_block_intro(block_num: int) -> str:
    b = QUEST[block_num]
    return (
        f"🟩 *{b['name']}*\n"
        f"📍 Локация: {b['location']}\n\n"
        f"В блоке 5 заданий. Выполни *минимум 3* — и получишь награду.\n"
        f"За каждую подсказку — минус 1 очко воли.\n\n"
        f"Напиши /task чтобы получить первое задание."
    )


def build_task_message(block_num: int, task_idx: int) -> str:
    task = QUEST[block_num]["tasks"][task_idx]
    return f"📜 *Задание {task['id']}*\n\n{task['text']}"


def build_final_message() -> str:
    return (
        "💚 *Финальное послание Батареи Силы*\n\n"
        "Женечка, ты прошёл все пять секторов. Клятва произнесена, "
        "воля проверена, страх побеждён, конструкты построены, "
        "спектр эмоций освоен.\n\n"
        "Но помни: кольцо Зелёного Фонаря питается не силой мышц, "
        "а силой воли. Не страхом. Не яростью. Не отчаянием. "
        "А верой в то, что можно изменить мир — если по-настоящему захотеть.\n\n"
        "Ты прошёл этот путь не потому, что умнее всех. "
        "А потому, что не сдался.\n\n"
        "Корпус Зелёных Фонарей признаёт тебя полноправным членом.\n\n"
        "💍 *С днём рождения, моя любимка.*\n\n"
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
        "💚 *Добро пожаловать в Корпус Зелёных Фонарей!*\n\n"
        "Кольцо силы выбрало тебя. Внутри — твоё первое задание.\n"
        "Пройди пять секторов — и докажешь, что достоин носить зелёный цвет.\n"
        "За каждое испытание — награда.\n\n"
        "Правила:\n"
        "• Кольцо на руке всё время\n"
        "• В каждом блоке 5 заданий, нужно выполнить минимум 3\n"
        "• Подсказка — минус 1 очко воли\n\n"
        "Напиши /go чтобы начать Сектор 1 «Оа».",
        parse_mode="Markdown",
    )


@dp.message(Command("go"))
async def cmd_go(message: Message, state: FSMContext):
    data = await state.get_data()
    block = data.get("block", 1)
    await state.set_state(QuestState.in_block)
    await message.answer(build_block_intro(block), parse_mode="Markdown")


@dp.message(Command("task"))
async def cmd_task(message: Message, state: FSMContext):
    data = await state.get_data()
    block = data.get("block", 1)
    idx = next_task_index(data, block)

    if idx is None:
        await message.answer("Все задания блока выполнены. Напиши /next")
        return

    if block_completed(data, block):
        await message.answer(
            "Ты уже выполнил минимум 3 задания в этом блоке! 💪\n"
            "Можешь добить остальные (/task) или перейти дальше (/next)."
        )

    await message.answer(build_task_message(block, idx), parse_mode="Markdown")


@dp.message(Command("next"))
async def cmd_next(message: Message, state: FSMContext):
    data = await state.get_data()
    block = data.get("block", 1)

    if not block_completed(data, block):
        done = block_progress(data, block)
        await message.answer(
            f"⚠️ Ты выполнил только {done} из 3 нужных заданий в блоке {block}.\n"
            f"Напиши /task чтобы продолжить."
        )
        return

    reward_text = None
    for task in QUEST[block]["tasks"]:
        if task["reward"]:
            reward_text = task["reward"]
            break

    if block == 5:
        await message.answer(build_final_message(), parse_mode="Markdown")
        await state.clear()
        return

    await message.answer(
        f"✅ Блок {block} пройден!\n\n"
        f"{reward_text or ''}\n\n"
        f"{QUEST[block]['location_hint']}\n\n"
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
    await state.update_data(hints_used=data.get("hints_used", 0) + 1,
                            score=data.get("score", 0) - 1)
    await message.answer(f"💡 Подсказка: {task['hint']}\n\n(-1 очко воли)")


@dp.message(Command("status"))
async def cmd_status(message: Message, state: FSMContext):
    data = await state.get_data()
    block = data.get("block", 1)
    lines = [f"🟢 *Статус квеста*\nТекущий блок: {block}\n"]
    for b in range(1, 6):
        done = block_progress(data, b)
        mark = "✅" if done >= 3 else "⏳"
        lines.append(f"{mark} Блок {b}: {done}/5 (нужно 3)")
    lines.append(f"\n💚 Очки воли: {data.get('score', 0)}")
    await message.answer("\n".join(lines), parse_mode="Markdown")


@dp.message(Command("final"))
async def cmd_final(message: Message):
    await message.answer(build_final_message(), parse_mode="Markdown")


@dp.message(QuestState.in_block, F.text)
async def handle_answer(message: Message, state: FSMContext):
    data = await state.get_data()
    block = data.get("block", 1)
    idx = next_task_index(data, block)

    if idx is None:
        await message.answer("Все задания блока выполнены. Напиши /next")
        return

    task = QUEST[block]["tasks"][idx]
    user_answer = normalize(message.text)

    if task["answer"] is None:
        correct = True
    else:
        correct = normalize(task["answer"]) in user_answer or user_answer in normalize(task["answer"])

    if not correct:
        await message.answer(
            "❌ Неверно. Попробуй ещё раз или напиши /hint для подсказки."
        )
        return

    done_key = f"done_{block}"
    done = data.get(done_key, [])
    if task["id"] not in done:
        done.append(task["id"])
    await state.update_data(**{done_key: done, "score": data.get("score", 0) + 1})

    reward_line = f"\n\n{task['reward']}" if task.get("reward") else ""

    await message.answer(
        f"✅ Верно! {task['id']} засчитано.{reward_line}\n\n"
        f"Прогресс блока: {len(done)}/5 (нужно 3).\n"
        f"Напиши /task для следующего задания или /next если уже набрал 3."
    )


async def main():
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())