    # --- режим удаления замеров ---
    if getattr(message.bot, "expecting_measurement_delete", False):
        index = number - 1
        if 0 <= index < len(message.bot.user_measurements):
            entry = message.bot.user_measurements[index]

            session = SessionLocal()
            m = session.query(Measurement).filter_by(
                user_id=user_id,
                date=entry.date
            ).first()

            if m:
                session.delete(m)
                session.commit()
                session.close()
                message.bot.user_measurements.pop(index)
                await message.answer(f"✅ Удалил замеры от {entry.date.strftime('%d.%m.%Y')}")
            else:
                session.close()
                await message.answer("❌ Не нашёл такие замеры в базе.")

        else:
            await message.answer("⚠️ Нет такой записи.")
        message.bot.expecting_measurement_delete = False
        return
