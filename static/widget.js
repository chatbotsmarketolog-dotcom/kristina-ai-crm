@app.route('/api/send_with_files', methods=['POST'])
@token_required
def send_message_with_files():
    try:
        chat_id = request.form.get('chat_id')
        text = request.form.get('text', '')
        files = request.files.getlist('files')
        
        if not chat_id:
            return jsonify({"error": "chat_id обязателен"}), 400
        
        # Определяем отправителя
        user = request.current_user
        sender = 'admin' if user.is_admin else 'user'
        
        # Создаём сообщение
        msg = Message(chat_id=chat_id, sender=sender, text=text)
        db.session.add(msg)
        db.session.commit()
        
        # Сохраняем файлы
        if files:
            uploads_dir = os.path.join(app.static_folder, 'uploads', 'chat_files', str(chat_id))
            os.makedirs(uploads_dir, exist_ok=True)
            
            for file in files:
                if file.filename:
                    filename = f"{uuid.uuid4().hex}_{file.filename}"
                    filepath = os.path.join(uploads_dir, filename)
                    file.save(filepath)
                    
                    # Добавляем информацию о файле (можно создать отдельную таблицу)
                    # Для простоты сохраняем в text как JSON
                    file_info = {
                        "name": file.filename,
                        "url": f"/static/uploads/chat_files/{chat_id}/{filename}"
                    }
        
        # Отправляем уведомления
        chat = Chat.query.get(chat_id)
        if chat and chat.user_id:
            if sender == 'admin':
                user_recipient = User.query.get(chat.user_id)
                if user_recipient and user_recipient.telegram_chat_id:
                    send_telegram_notification(
                        user_recipient.telegram_chat_id,
                        f"💬 <b>Новое сообщение от админа!</b>\n\n{text[:100]}..." if len(text) > 100 else text
                    )
            else:
                admin = User.query.filter_by(is_admin=True).first()
                if admin and admin.telegram_chat_id:
                    user_recipient = User.query.get(chat.user_id)
                    send_telegram_notification(
                        admin.telegram_chat_id,
                        f"💬 <b>Ответ от {user_recipient.username if user_recipient else 'Пользователя'}</b>\n\n{text[:100]}..." if len(text) > 100 else text
                    )
        
        return jsonify({"ok": True})
    except Exception as e:
        print(f"Send with files error: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500
