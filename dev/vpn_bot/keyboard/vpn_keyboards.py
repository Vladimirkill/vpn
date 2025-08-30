from telegram import InlineKeyboardButton, InlineKeyboardMarkup

def get_vpn_keyboard(client_name: str, has_existing_key: bool = False, existing_key_info: str = None):
    """
    Создает клавиатуру для управления VPN ключами
    
    Args:
        client_name: Имя клиента
        has_existing_key: Есть ли у пользователя существующий ключ
        existing_key_info: Информация о существующем ключе
    """
    
    if has_existing_key:
        # Клавиатура для пользователя с существующим ключом
        keyboard = [
            [
                InlineKeyboardButton("🔄 Обновить ключ", callback_data=f"update_key_{client_name}")
            ],
            [
                InlineKeyboardButton("🌍 Смена IP", callback_data="ip_refresh"),
                InlineKeyboardButton("🏢 Аренда IP", callback_data="rental_menu")
            ],
            [
                InlineKeyboardButton("⚙️ Настройки", callback_data=f"settings_{client_name}")
            ],
            [
                InlineKeyboardButton("🔙 Назад", callback_data="back_to_main")
            ]
        ]
    else:
        # Клавиатура для нового пользователя
        keyboard = [
            [
                InlineKeyboardButton("🔑 Создать VPN ключ", callback_data=f"create_key_{client_name}")
            ],
            [
                InlineKeyboardButton("🔙 Назад", callback_data="back_to_main")
            ]
        ]
    
    return InlineKeyboardMarkup(keyboard)

def get_key_management_keyboard(client_name: str, key_uuid: str = None):
    """
    Создает клавиатуру для управления конкретным ключом
    """
    keyboard = [
        [
            InlineKeyboardButton("🔄 Обновить ключ", callback_data=f"update_key_{client_name}")
        ],
        [
            InlineKeyboardButton("⚙️ Настройки лимитов", callback_data=f"limits_{client_name}")
        ],
        [
            InlineKeyboardButton("🔙 Назад в главное меню", callback_data="back_to_main")
        ]
    ]
    
    return InlineKeyboardMarkup(keyboard)

def get_confirmation_keyboard(action: str, client_name: str):
    """
    Создает клавиатуру подтверждения для критических действий
    """
    keyboard = [
        [
            InlineKeyboardButton("✅ Да, подтверждаю", callback_data=f"confirm_{action}_{client_name}"),
            InlineKeyboardButton("❌ Отмена", callback_data=f"cancel_{action}_{client_name}")
        ]
    ]
    
    return InlineKeyboardMarkup(keyboard)

def get_main_menu_keyboard(is_admin=False):
    """
    Создает основное меню бота
    """
    keyboard = [
        [
            InlineKeyboardButton("🔑 Мои VPN ключи", callback_data="my_keys"),
            InlineKeyboardButton("🚀 Создать новый ключ", callback_data="create_new_key")
        ],
        [
            InlineKeyboardButton("⚙️ Настройки", callback_data="settings"),
            InlineKeyboardButton("❓ Справка", callback_data="help")
        ]
    ]
    
    # Добавляем админскую кнопку для админов
    if is_admin:
        keyboard.insert(-1, [
            InlineKeyboardButton("🛡️ Админ панель", callback_data="admin_menu")
        ])
        keyboard.insert(-1, [
            InlineKeyboardButton("📊 Детальный статус", callback_data="status")
        ])
    
    return InlineKeyboardMarkup(keyboard) 

def get_limits_keyboard(client_name: str, max_connections: int, max_devices: int, locked: bool = False):
    """
    Клавиатура для экрана настройки лимитов.
    Включает кнопки увеличения/уменьшения и кнопку Назад.
    """
    if locked:
        keyboard = [
            [
                InlineKeyboardButton("🔒 Изменение недоступно", callback_data="noop")
            ],
            [
                InlineKeyboardButton("🔙 К списку ключей", callback_data=f"back_to_keys_{client_name}")
            ]
        ]
    else:
        keyboard = [
            [
                InlineKeyboardButton("➖ Соединения", callback_data=f"limits_dec_conn_{client_name}"),
                InlineKeyboardButton(f"{max_connections}", callback_data="noop"),
                InlineKeyboardButton("➕ Соединения", callback_data=f"limits_inc_conn_{client_name}")
            ],
            [
                InlineKeyboardButton("➖ Устройства", callback_data=f"limits_dec_dev_{client_name}"),
                InlineKeyboardButton(f"{max_devices}", callback_data="noop"),
                InlineKeyboardButton("➕ Устройства", callback_data=f"limits_inc_dev_{client_name}")
            ],
            [
                InlineKeyboardButton("🔙 К списку ключей", callback_data=f"back_to_keys_{client_name}")
            ]
        ]
    return InlineKeyboardMarkup(keyboard)

def get_admin_keyboard():
    """
    Создает админскую клавиатуру
    """
    keyboard = [
        [
            InlineKeyboardButton("👥 Управление пользователями", callback_data="admin_users")
        ],
        [
            InlineKeyboardButton("📊 Статистика системы", callback_data="admin_stats")
        ],
        [
            InlineKeyboardButton("🛡️ Применить лимиты", callback_data="admin_enforce_limits")
        ],
        [
            InlineKeyboardButton("🔧 Управление Xray", callback_data="admin_xray_menu")
        ],
        [
            InlineKeyboardButton("🔐 OpenVPN", callback_data="vpn_openvpn"),
            InlineKeyboardButton("⚡ WireGuard", callback_data="vpn_wireguard")
        ],
        [
            InlineKeyboardButton("🔙 Главное меню", callback_data="back_to_main")
        ]
    ]
    return InlineKeyboardMarkup(keyboard)

def get_admin_users_keyboard(page=0, users_per_page=5):
    """
    Создает клавиатуру для управления пользователями
    """
    keyboard = [
        [
            InlineKeyboardButton("🔍 Поиск пользователя", callback_data="admin_search_user")
        ],
        [
            InlineKeyboardButton("📋 Все пользователи", callback_data=f"admin_list_users_{page}")
        ],
        [
            InlineKeyboardButton("🔙 Админ меню", callback_data="admin_menu")
        ]
    ]
    return InlineKeyboardMarkup(keyboard)

def get_user_admin_keyboard(client_name: str):
    """
    Создает клавиатуру для управления конкретным пользователем
    """
    keyboard = [
        [
            InlineKeyboardButton("⚙️ Управление лимитами", callback_data=f"admin_manage_limits_{client_name}")
        ],
        [
            InlineKeyboardButton("🔄 Сбросить лимиты", callback_data=f"admin_reset_limits_{client_name}")
        ],
        [
            InlineKeyboardButton("🗑️ Удалить все ключи", callback_data=f"admin_remove_all_keys_{client_name}")
        ],
        [
            InlineKeyboardButton("🔑 Создать ключ", callback_data=f"admin_create_key_{client_name}")
        ],
        [
            InlineKeyboardButton("📊 Статистика", callback_data=f"admin_user_stats_{client_name}")
        ],
        [
            InlineKeyboardButton("🔙 К пользователям", callback_data="admin_users")
        ]
    ]
    return InlineKeyboardMarkup(keyboard)

def get_admin_xray_keyboard():
    """
    Создает клавиатуру для управления Xray
    """
    keyboard = [
        [
            InlineKeyboardButton("📊 Статус Xray", callback_data="admin_xray_status")
        ],
        [
            InlineKeyboardButton("🔄 Перезапустить Xray", callback_data="admin_xray_restart")
        ],
        [
            InlineKeyboardButton("🔧 Перезагрузить конфигурацию", callback_data="admin_xray_reload")
        ],
        [
            InlineKeyboardButton("📋 Логи Xray", callback_data="admin_xray_logs")
        ],
        [
            InlineKeyboardButton("🧹 Очистить просроченные ключи", callback_data="admin_cleanup_expired")
        ],
        [
            InlineKeyboardButton("🔙 Админ меню", callback_data="admin_menu")
        ]
    ]
    return InlineKeyboardMarkup(keyboard)