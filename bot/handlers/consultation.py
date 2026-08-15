"""Консультации: FAQ-дерево и связь с менеджером."""

from __future__ import annotations

import logging

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from bot.filters import ChatIsManagerGroup
from bot.keyboards.factories import ConsultationCallback
from bot.keyboards.inline import ask_manager_keyboard, consultation_keyboard, faq_keyboard
from bot.models import Consultation
from bot.services.catalog import get_faqs, get_or_create_user
from bot.services.notification import notify_manager_group
from bot.states import ConsultationState

logger = logging.getLogger(__name__)

router = Router(name="consultation")


async def show_consultation_menu(message: Message) -> None:
    text = (
        "💬 <b>Консультация</b>\n\n"
        "Наш beauty-консьерж поможет подобрать уход под вашу кожу, бюджет и задачи.\n\n"
        "Выберите вариант:"
    )
    await message.edit_text(text, reply_markup=consultation_keyboard(), parse_mode="HTML")


@router.message(F.text == "💬 Консультация")
async def consult_message(message: Message, state: FSMContext) -> None:
    await state.clear()
    await message.answer(
        "💬 <b>Консультация</b>\n\nНаш beauty-консьерж поможет подобрать уход. Выберите вариант:",
        reply_markup=consultation_keyboard(), parse_mode="HTML",
    )


@router.callback_query(ConsultationCallback.filter(F.action == "faq"))
async def faq_list(callback: CallbackQuery) -> None:
    await callback.message.edit_text("❓ <b>Частые вопросы</b>\n\nВыберите вопрос:", reply_markup=faq_keyboard(), parse_mode="HTML")
    await callback.answer()


@router.callback_query(ConsultationCallback.filter(F.action == "topic"))
async def faq_topic(callback: CallbackQuery, callback_data: ConsultationCallback) -> None:
    faqs = get_faqs()
    try:
        question, answer = faqs[int(callback_data.value)]
    except (ValueError, IndexError):
        await callback.answer("Вопрос не найден")
        return
    from aiogram.utils.keyboard import InlineKeyboardBuilder

    builder = InlineKeyboardBuilder()
    builder.button(text="💬 Задать свой вопрос", callback_data=ConsultationCallback(action="manager").pack())
    builder.button(text="🔙", callback_data=ConsultationCallback(action="faq").pack())
    builder.adjust(1)
    await callback.message.edit_text(
        f"❓ <b>{question}</b>\n\n{answer}",
        reply_markup=builder.as_markup(), parse_mode="HTML",
    )
    await callback.answer()


@router.callback_query(ConsultationCallback.filter(F.action == "faq_back"))
async def faq_back(callback: CallbackQuery) -> None:
    await show_consultation_menu(callback.message)
    await callback.answer()


@router.callback_query(ConsultationCallback.filter(F.action == "manager"))
async def ask_manager(callback: CallbackQuery, state: FSMContext) -> None:
    await start_consultation(callback.message, state)


@router.callback_query(ConsultationCallback.filter(F.action == "cancel"))
async def cancel_consult(callback: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    await callback.message.edit_text("Отменено.", reply_markup=consultation_keyboard())
    await callback.answer()


async def start_consultation(message: Message, state: FSMContext, topic: str | None = None) -> None:
    """Начинает консультацию: просит описать вопрос."""
    await state.set_state(ConsultationState.MESSAGE)
    await state.update_data(topic=topic)
    await message.answer(
        "✍️ <b>Опишите ваш вопрос</b>\n\n"
        "Расскажите, что хотите подобрать или узнать. Например: «ищу ночной уход для сухой кожи до 8 000 ₽».\n\n"
        "/отмена — отменить",
        reply_markup=ask_manager_keyboard(),
        parse_mode="HTML",
    )


@router.message(ConsultationState.MESSAGE)
async def consult_message_text(message: Message, state: FSMContext) -> None:
    if message.text and message.text.strip().lower() == "/отмена":
        await state.clear()
        await message.answer("Отменено. Чем ещё помочь?", reply_markup=consultation_keyboard())
        return
    text = (message.text or message.caption or "").strip()
    if not text:
        await message.answer("Пожалуйста, опишите вопрос текстом.")
        return
    data = await state.get_data()
    from bot.database import get_sessionmaker

    async with get_sessionmaker()() as session:
        user = await get_or_create_user(
            session, message.from_user.id, username=message.from_user.username,
            first_name=message.from_user.first_name, last_name=message.from_user.last_name,
        )
        consult = Consultation(user_id=user.id, topic=data.get("topic"), message=text)
        session.add(consult)
        await session.commit()
        consult_id = consult.id

    await state.clear()
    await message.answer(
        "✅ <b>Заявка отправлена!</b>\n\nМенеджер ответит в ближайшее время (обычно до 10 минут). "
        "Не забывайте заглядывать в этот чат.",
        parse_mode="HTML",
    )
    await notify_manager_group(
        message.bot,
        f"💬 <b>Новое обращение</b> (#{consult_id})\n\n"
        f"👤 {message.from_user.full_name} (@{message.from_user.username or '-'})\n"
        f"ID клиента: {message.from_user.id}\n"
        f"Тема: {data.get('topic') or '—'}\n\n{text}\n\n"
        f"Ответьте прямо на это сообщение — оно уйдёт клиенту.",
    )


@router.message(ChatIsManagerGroup())
async def manager_reply_forward(message: Message) -> None:
    """Пересылает ответ менеджера клиенту.

    Срабатывает на реплику в группе менеджеров на наше уведомление.
    Из текста исходного сообщения извлекается ID клиента.
    """
    if not message.reply_to_message:
        return
    if not message.text:
        return
    original = message.reply_to_message.text or ""
    tg_id_line = next((line for line in original.splitlines() if line.startswith("ID клиента: ")), None)
    if tg_id_line is None:
        return
    try:
        client_id = int(tg_id_line.replace("ID клиента: ", "").strip())
    except ValueError:
        return
    await message.bot.send_message(
        client_id,
        f"💬 <b>Ответ менеджера:</b>\n\n{message.text}",
        parse_mode="HTML",
    )
    await message.answer("✅ Ответ отправлен клиенту.")
