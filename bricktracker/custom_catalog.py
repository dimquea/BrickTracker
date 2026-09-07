from typing import Any

from flask import current_app


# Ссылка на позицию в произвольном стороннем каталоге
#
# Пришла на смену жёстко зашитым ссылкам на Rebrickable. После перехода на
# каталог BrickLink идентификаторы у нас его, и ссылки на Rebrickable вели
# бы в никуда. Но место для второго каталога полезное: у каждого свой
# любимый справочник, и адрес позиции в нём складывается по шаблону.
#
# Выключено, пока не задано название: без него подписывать ссылку нечем.
# Пустой шаблон выключает ссылки только для своего типа позиций — можно
# завести каталог, знающий, скажем, только наборы.
def custom_catalog_url(pattern_name: str, /, **parameters: Any) -> str:
    if not current_app.config['CUSTOM_CATALOG_NAME']:
        return ''

    pattern = current_app.config[pattern_name]

    if not pattern:
        return ''

    try:
        return pattern.format(**parameters)

    # Шаблон задаёт пользователь, и опечатка в подстановке не должна
    # ронять страницу целиком
    except Exception:
        return ''
